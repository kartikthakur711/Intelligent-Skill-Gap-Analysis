"""Pure analysis and roadmap helpers shared by the API and model workflows."""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone


def clean_html(text: object) -> str:
    """Strip markup, decode entities, and normalize whitespace for text matching."""
    value = "" if text is None else str(text)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def build_learning_roadmap(
    missing_skills,
    dependencies,
    known_skills,
    normalize_skill,
):
    """Return prerequisite-ordered learning steps, excluding known skills."""
    known = {normalize_skill(skill) for skill in (known_skills or [])}
    result = []
    seen = set()
    visiting = set()

    def add(skill):
        key = normalize_skill(skill)
        if not key or key in known or key in seen or key in visiting:
            return
        visiting.add(key)
        for prerequisite in dependencies.get(key, []):
            add(prerequisite)
        visiting.remove(key)
        seen.add(key)
        result.append(skill)

    for skill in missing_skills:
        add(skill)
    return result


def build_skill_recommendations(priority_rows, resources, normalize_skill):
    """Join demand-ranked missing skills to catalog resources and explain rank."""
    resource_map = {}
    for resource in resources or []:
        key = normalize_skill(resource.get("skill", ""))
        if key:
            resource_map.setdefault(key, []).append(resource)

    rows = []
    for row in priority_rows or []:
        skill = str(row.get("Skill", "")).strip()
        if not skill:
            continue
        count = int(row.get("Job Demand", 0) or 0)
        recent = int(row.get("Recent India Listings (48h)", 0) or 0)
        catalog_score = float(row.get("Demand Score", 0) or 0)
        # Catalog frequency is the stable baseline; recent listings break ties
        # and provide a modest boost without letting a small sample dominate.
        score = catalog_score + (min(recent, 10) / 100.0)
        if count or recent:
            reason = f"Appears in {count} job-catalog skill entries"
            if recent:
                reason += f" and {recent} recent India listing(s)"
            reason += "; higher observed demand puts it earlier in your plan."
        else:
            reason = "No demand was recorded in the available sources; ordered after skills with observed demand."
        rows.append({
            "Skill": skill,
            "Demand Score": score,
            "Explanation": reason,
            "Resources": resource_map.get(normalize_skill(skill), []),
        })

    rows.sort(key=lambda item: (-item["Demand Score"], normalize_skill(item["Skill"])))
    for rank, row in enumerate(rows, 1):
        row["Rank"] = rank
    return rows


def build_learning_plan(roadmap, normalize_skill):
    """Create a deterministic 30/60/90-day plan from prerequisite order."""
    steps = [skill for skill in roadmap if normalize_skill(skill)]
    phases = [
        {"Day": 30, "Phase": "First 30 days", "Skills": []},
        {"Day": 60, "Phase": "Days 31–60", "Skills": []},
        {"Day": 90, "Phase": "Days 61–90", "Skills": []},
    ]
    total = max(1, len(steps))
    for index, skill in enumerate(steps):
        phase_index = min(2, (index * 3) // total)
        phases[phase_index]["Skills"].append(skill)
    return phases


def build_dashboard_skill_demand(catalog_skill_rows, recent_counts, normalize_skill, limit=5):
    """Summarize observed catalog skill mentions and an optional recent snapshot."""
    counts = {}
    labels = {}
    for skills in catalog_skill_rows or []:
        for skill in skills or []:
            label = str(skill).strip()
            key = normalize_skill(label)
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
            labels.setdefault(key, label)

    rows = []
    for key, count in counts.items():
        row = {"Skill": labels[key], "Catalog mentions": count}
        if recent_counts is not None:
            row["Recent India listings"] = int(recent_counts.get(key, 0))
        rows.append(row)
    rows.sort(key=lambda row: (-row["Catalog mentions"], normalize_skill(row["Skill"])))
    return rows[:max(0, int(limit))]


def summarize_recent_snapshot(rows, metadata, now=None, stale_after_hours=36):
    """Explain whether an aggregate snapshot is current, empty, or unavailable."""
    if rows is None or metadata is None:
        return {
            "state": "unavailable",
            "message": "Recent India listing data is unavailable (missing or invalid snapshot files). Catalog mentions remain available.",
            "age_hours": None,
        }

    try:
        generated = datetime.fromisoformat(str(metadata["generated_at_utc"]).replace("Z", "+00:00"))
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=timezone.utc)
        generated = generated.astimezone(timezone.utc)
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        age_hours = max(0.0, (current.astimezone(timezone.utc) - generated).total_seconds() / 3600)
        api_records = int(metadata["api_records"])
        processed_jobs = int(metadata["processed_jobs"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return {
            "state": "unavailable",
            "message": "Recent India listing data has invalid freshness or coverage metadata. Catalog mentions remain available.",
            "age_hours": None,
        }

    if metadata.get("stale") is True:
        state = "stale"
        source_time = metadata.get("source_snapshot_generated_at_utc", metadata.get("generated_at_utc"))
        message = f"The refresh failed; showing the last validated snapshot from {source_time}. Its counts are historical context."
    elif age_hours >= stale_after_hours:
        state = "stale"
        message = f"Snapshot is {age_hours:.0f} hours old, beyond the {stale_after_hours}-hour freshness window. Its recorded counts are shown as historical context."
    elif api_records == 0:
        state = "no_listings"
        message = "The latest snapshot found no India listings in its 48-hour posting window. This is a valid empty result, not a missing-data error."
    elif not rows:
        state = "no_skill_matches"
        message = f"The snapshot checked {api_records} API records ({processed_jobs} usable descriptions) but found no matches for catalog skills. This is a valid empty result, not a missing-data error."
    else:
        state = "available"
        message = f"The snapshot checked {api_records} API records ({processed_jobs} usable descriptions) and matched {len(rows)} category/skill pairs. A zero for a skill means it was not matched in this limited sample."
    return {"state": state, "message": message, "age_hours": age_hours}

