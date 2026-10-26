"""Utilities for honest discovery of roles present in the bundled catalog."""

from __future__ import annotations

import re


def normalize_title(title: object) -> str:
    """Normalize presentation variants without merging distinct role names."""
    value = re.sub(r"[^a-z0-9+# ]", " ", str(title or "").casefold())
    value = " ".join(value.split())
    aliases = {
        "ml engineer": "machine learning engineer",
        "ml developer": "machine learning developer",
        "ai engineer": "artificial intelligence engineer",
        "software developer": "software engineer",
        "application developer": "software engineer",
    }
    return aliases.get(value, value)


def catalog_roles(frame):
    """Return unique real title strings present in source rows, with provenance."""
    required = {"job_title"}
    if not required.issubset(frame.columns):
        raise ValueError("Job catalog is missing job_title")
    groups = {}
    for _, row in frame.iterrows():
        raw_title = row.get("job_title")
        title = "" if raw_title is None else str(raw_title).strip()
        if title.casefold() in {"nan", "none", "<na>"}:
            title = ""
        key = normalize_title(title)
        if not key:
            continue
        entry = groups.setdefault(key, {"Job title": title, "Catalog rows": 0, "Categories": set()})
        entry["Catalog rows"] += 1
        raw_category = row.get("category")
        category = "" if raw_category is None else str(raw_category).strip()
        if category.casefold() in {"nan", "none", "<na>"}:
            category = ""
        if category:
            entry["Categories"].add(category)
    result = []
    for entry in groups.values():
        result.append({
            "Job title": entry["Job title"],
            "Catalog rows": entry["Catalog rows"],
            "Categories": ", ".join(sorted(entry["Categories"])),
        })
    return sorted(result, key=lambda role: role["Job title"].casefold())

