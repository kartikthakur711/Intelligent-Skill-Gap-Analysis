"""Read the aggregate skill-demand file without loading source job text."""
from __future__ import annotations

import csv
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
    path: Path, normalize_skill: Callable[[str], str]
) -> tuple[list[dict[str, str]] | None, dict[str, str] | None]:
    """Return aggregate rows and generation metadata, or (None, None) if unavailable."""
    if not path.exists():
        return None, None
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not REQUIRED_COLUMNS.issubset(reader.fieldnames or []):
                return None, None
            rows = []
            metadata = None
            for row in reader:
                if metadata is None:
                    metadata = {
                        "generated_at_utc": str(row.get("generated_at_utc") or ""),
                        "window_start_utc": str(row.get("window_start_utc") or ""),
                    }
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
            return rows, metadata if rows else None
    except (OSError, csv.Error, UnicodeError):
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

