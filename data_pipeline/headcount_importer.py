#!/usr/bin/env python3
"""Build aggregate skill demand from a bounded Headcount Labs India query.

Posting text is processed in memory and never written to disk. The output only
contains categories and skill counts derived from the existing project catalog.
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE = "https://api.headcountlabs.com"
FIELDS = "job_id,title,description"
APP_COLUMNS = ("job_id", "category", "job_title", "job_description", "job_skill_set")
OUTPUT_COLUMNS = ("category", "skill", "distinct_job_count")


def normalize(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower().replace(".", "").replace("-", " ")


def parse_skills(value: str) -> list[str]:
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, (list, tuple, set)):
            return sorted({normalize(item) for item in parsed if normalize(item)})
    except (ValueError, SyntaxError):
        pass
    return sorted({normalize(item) for item in re.split(r"[,;|]", value) if normalize(item)})


def field_value(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("value") or "") if value.get("state") == "known" else ""
    return str(value or "")


def load_taxonomy(catalog_path: Path) -> dict[str, set[str]]:
    taxonomy: dict[str, set[str]] = defaultdict(set)
    with catalog_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(APP_COLUMNS).difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Catalog is missing required columns: {sorted(missing)}")
        for row in reader:
            category = str(row.get("category") or "").strip()
            if category:
                taxonomy[category].update(parse_skills(row.get("job_skill_set") or ""))
    if not taxonomy:
        raise ValueError("Catalog taxonomy is empty")
    return dict(taxonomy)


def request_page(params: dict[str, str], api_key: str, timeout: int = 30) -> dict:
    query = urlencode(params)
    request = Request(
        f"{API_BASE}/v1/jobs?{query}",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        # Never include response text or request headers: either could contain secrets.
        raise RuntimeError(f"Headcount API returned HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Headcount API request failed ({type(exc).__name__})") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("Headcount API returned an unexpected response shape")
    return payload


def extract_skills(description: str, title: str, taxonomy: dict[str, set[str]]) -> dict[str, list[str]]:
    text = normalize(f"{title} {description}")
    found: dict[str, list[str]] = {}
    for category, skills in taxonomy.items():
        matches = [skill for skill in skills if skill and re.search(rf"(?<![\w]){re.escape(skill)}(?![\w])", text)]
        if matches:
            found[category] = matches
    return found


def run(
    catalog_path: Path,
    output_path: Path,
    *,
    api_key: str,
    updated_since: str,
    max_records: int = 250,
    page_size: int = 100,
    sleep_seconds: float = 0.2,
) -> dict[str, int | str]:
    if not api_key:
        raise ValueError("HEADCOUNT_API_KEY is required")
    if not 1 <= max_records <= 1000:
        raise ValueError("max_records must be between 1 and 1000")
    if not 1 <= page_size <= 250:
        raise ValueError("page_size must be between 1 and 250")
    taxonomy = load_taxonomy(catalog_path)
    params = {
        "country": "IN",
        "currentness": "current",
        "stale": "false",
        "updated_since": updated_since,
        "sort": "updated",
        "fields": FIELDS,
        "limit": str(min(page_size, max_records)),
    }
    jobs: dict[str, tuple[str, str]] = {}
    cursor: str | None = None
    watermark: str | None = None
    while True:
        page_params = dict(params)
        if cursor:
            page_params["cursor"] = cursor
        payload = request_page(page_params, api_key)
        if watermark is None:
            watermark = str(payload.get("snapshot_watermark") or "")
        elif payload.get("snapshot_watermark") != watermark:
            raise RuntimeError("Headcount catalog watermark changed during pagination; rerun the import")
        for job in payload["data"]:
            job_id = str(job.get("job_id") or "").strip()
            title = field_value(job.get("title"))
            description = field_value(job.get("description"))
            if not job_id or not title or not description:
                continue
            jobs[job_id] = (title, description)
            if len(jobs) > max_records:
                raise RuntimeError(f"Import exceeded the safety cap of {max_records} unique jobs")
        cursor = payload.get("next_cursor")
        if not cursor:
            break
        if len(jobs) >= max_records:
            raise RuntimeError(f"Import exceeded the safety cap of {max_records} unique jobs")
        time.sleep(sleep_seconds)

    counts: Counter[tuple[str, str]] = Counter()
    for title, description in jobs.values():
        for category, skills in extract_skills(description, title, taxonomy).items():
            counts.update((category, skill) for skill in skills)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for (category, skill), count in sorted(counts.items()):
            writer.writerow({"category": category, "skill": skill, "distinct_job_count": count})
    temporary_path.replace(output_path)
    return {"unique_jobs": len(jobs), "category_skill_pairs": len(counts), "snapshot_watermark": watermark or ""}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("job_catalog.csv"))
    parser.add_argument("--output", type=Path, default=Path("build/headcount_skill_demand.csv"))
    parser.add_argument("--updated-since", help="RFC 3339 timestamp; defaults to 48 hours ago")
    parser.add_argument("--max-records", type=int, default=250)
    args = parser.parse_args()
    since = args.updated_since or (datetime.now(timezone.utc) - timedelta(hours=48)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    try:
        report = run(args.catalog, args.output, api_key=os.environ.get("HEADCOUNT_API_KEY", ""), updated_since=since, max_records=args.max_records)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
