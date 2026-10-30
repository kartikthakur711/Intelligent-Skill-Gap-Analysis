"""Read the aggregate skill-demand file without loading source job text."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import re
from typing import Callable
from datetime import datetime

REQUIRED_COLUMNS = {
    "category",
    "skill",
    "distinct_job_count",
    "window_start_utc",
    "generated_at_utc",
}
TITLE_COLUMNS = {"job_title", "distinct_job_count", "window_start_utc", "generated_at_utc"}


def load_headcount_demand(
    path: Path, normalize_skill: Callable[[str], str], metadata_path: Path | None = None
) -> tuple[list[dict[str, str]] | None, dict[str, str] | None]:
    """Return aggregate rows and generation metadata, or (None, None) if unavailable."""
    metadata_path = metadata_path or path.with_suffix(".metadata.json")
    if not path.exists() or not metadata_path.exists():
        return None, None
    try:
        with metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)
        required_metadata = {"generated_at_utc", "window_start_utc", "api_records", "processed_jobs", "category_skill_pairs"}
        if not isinstance(metadata, dict) or not required_metadata.issubset(metadata):
            return None, None
        for name in ("generated_at_utc", "window_start_utc"):
            value = str(metadata[name]).replace("Z", "+00:00")
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                return None, None
        if metadata.get("stale") is True:
            for name in ("fallback_at_utc", "source_snapshot_generated_at_utc"):
                value = str(metadata.get(name, "")).replace("Z", "+00:00")
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    return None, None
        elif metadata.get("fallback") is True:
            return None, None
        for name in ("api_records", "processed_jobs", "category_skill_pairs"):
            if int(metadata[name]) < 0:
                return None, None
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not REQUIRED_COLUMNS.issubset(reader.fieldnames or []):
                return None, None
            rows = []
            for row in reader:
                skill = normalize_skill(row.get("skill", ""))
                try:
                    raw_count = row.get("distinct_job_count", "")
                    count = int(raw_count)
                except (TypeError, ValueError):
                    return None, None
                category = str(row.get("category", "")).strip()
                if count < 0 or not skill or not category:
                    return None, None
                rows.append({
                    "category": category,
                    "skill_normalized": skill,
                    "distinct_job_count": str(count),
                })
            if len(rows) != int(metadata["category_skill_pairs"]):
                return None, None
            return rows, {str(k): str(v) for k, v in metadata.items()}
    except (OSError, csv.Error, UnicodeError, json.JSONDecodeError, TypeError, ValueError, OverflowError):
        return None, None


def recent_skill_counts(rows: list[dict[str, str]] | None) -> dict[str, int] | None:
    """Use the maximum category count to avoid double counting cross-category jobs."""
    if rows is None:
        return None
    counts: dict[str, int] = {}
    for row in rows:
        key = row["skill_normalized"]
        counts[key] = max(counts.get(key, 0), int(row["distinct_job_count"]))
    return counts


def load_headcount_titles(
    path: Path, metadata_path: Path | None = None
) -> tuple[list[dict[str, str]] | None, dict[str, str] | None]:
    """Load bounded, distinct-title aggregates and their snapshot provenance."""
    metadata_path = metadata_path or path.with_name("headcount_skill_demand.metadata.json")
    if not path.exists() or not metadata_path.exists():
        return None, None
    try:
        with metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)
        required_metadata = {
            "generated_at_utc", "window_start_utc", "api_records", "processed_jobs", "distinct_title_count"
        }
        if not isinstance(metadata, dict) or not required_metadata.issubset(metadata):
            return None, None
        for name in ("generated_at_utc", "window_start_utc"):
            value = str(metadata[name]).replace("Z", "+00:00")
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                return None, None
        if metadata.get("stale") is True:
            for name in ("fallback_at_utc", "source_snapshot_generated_at_utc"):
                value = str(metadata.get(name, "")).replace("Z", "+00:00")
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    return None, None
        elif metadata.get("fallback") is True:
            return None, None
        for name in ("api_records", "processed_jobs", "distinct_title_count"):
            if int(metadata[name]) < 0:
                return None, None
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not TITLE_COLUMNS.issubset(reader.fieldnames or []):
                return None, None
            rows = []
            seen: set[str] = set()
            for row in reader:
                title = re.sub(r"\s+", " ", str(row.get("job_title") or "")).strip()
                key = title.casefold()
                count = int(row.get("distinct_job_count", ""))
                if not title or count < 1 or key in seen:
                    return None, None
                seen.add(key)
                rows.append({"job_title": title, "distinct_job_count": str(count)})
            if len(rows) != int(metadata["distinct_title_count"]):
                return None, None
            return rows, {str(k): str(v) for k, v in metadata.items()}
    except (OSError, csv.Error, UnicodeError, json.JSONDecodeError, TypeError, ValueError, OverflowError):
        return None, None
