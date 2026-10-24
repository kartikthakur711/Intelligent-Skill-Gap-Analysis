#!/usr/bin/env python3
"""Validate and deduplicate a job catalog without modifying the source file.

Usage:
  python data_pipeline/build_catalog.py --input job_catalog.csv --output build/job_catalog_unique.csv

The script is source-agnostic. It does not fetch jobs or assume an API provider.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

REQUIRED = {"job_id", "category", "job_title", "job_description", "job_skill_set"}
APP_COLUMNS = ["job_id", "category", "job_title", "job_description", "job_skill_set"]


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def parse_skills(value: str) -> list[str]:
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, (list, tuple, set)):
            return sorted({clean(item) for item in parsed if clean(item)})
    except (ValueError, SyntaxError):
        pass
    return sorted({clean(item) for item in re.split(r"[,;|]", value) if clean(item)})


def fingerprint(row: dict[str, str]) -> str:
    # Do not use the catalog's row number/job_id as proof of uniqueness.
    payload = {
        "title": clean(row.get("job_title")),
        "description": clean(row.get("job_description")),
        "skills": parse_skills(row.get("job_skill_set", "")),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def dedup_key(row: dict[str, str]) -> str:
    external_id = clean(row.get("source_job_id"))
    url = clean(row.get("job_url") or row.get("canonical_url"))
    if external_id:
        return "id:" + external_id
    if url:
        return "url:" + url.rstrip("/")
    return "content:" + fingerprint(row)


def run(input_path: Path, output_path: Path, report_path: Path) -> int:
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        missing = REQUIRED.difference(columns)
        if missing:
            raise ValueError(f"Input is missing required app columns: {sorted(missing)}")
        rows = list(reader)

    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    duplicate_count = 0
    skills = Counter()
    for row in rows:
        key = dedup_key(row)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        unique.append(row)
        skills.update(parse_skills(row.get("job_skill_set", "")))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=APP_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(unique)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "input_rows": len(rows),
        "unique_rows": len(unique),
        "duplicate_rows_removed": duplicate_count,
        "unique_skill_count": len(skills),
        "top_skills_by_distinct_posting": skills.most_common(30),
        "deduplication_note": "Uses source_job_id, then job_url/canonical_url, then normalized title+description+skills fingerprint.",
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("build/job_catalog_unique.csv"))
    parser.add_argument("--report", type=Path, default=Path("build/catalog_quality_report.json"))
    args = parser.parse_args()
    try:
        return run(args.input, args.output, args.report)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
