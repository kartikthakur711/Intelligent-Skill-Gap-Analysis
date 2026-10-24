"""Read the aggregate skill-demand file without loading source job text."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

REQUIRED_COLUMNS = {
    "category",
    "skill",
    "distinct_job_count",
    "window_start_utc",
    "generated_at_utc",
}


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
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not REQUIRED_COLUMNS.issubset(reader.fieldnames or []):
                return None, None
            rows = []
            for row in reader:
                skill = normalize_skill(row.get("skill", ""))
                try:
                    count = max(0, int(float(row.get("distinct_job_count", "0"))))
                except (TypeError, ValueError):
                    continue
                if skill and row.get("category"):
                    rows.append({
                        "category": row["category"],
                        "skill_normalized": skill,
                        "distinct_job_count": str(count),
                    })
            loaded = {str(k): str(v) for k, v in metadata.items()}
            try:
                watermark = datetime.fromisoformat(str(metadata.get("snapshot_watermark", "")).replace("Z", "+00:00"))
                window_start = datetime.fromisoformat(str(metadata["window_start_utc"]).replace("Z", "+00:00"))
                loaded["snapshot_before_window"] = str(watermark.astimezone(timezone.utc) < window_start.astimezone(timezone.utc))
            except (TypeError, ValueError):
                loaded["snapshot_before_window"] = "False"
            return rows, loaded
    except (OSError, csv.Error, UnicodeError, json.JSONDecodeError):
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
