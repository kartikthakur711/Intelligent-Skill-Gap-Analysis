"""Small pure helpers used by the Streamlit app."""
from __future__ import annotations

import html
import re


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

    def add(skill):
        key = normalize_skill(skill)
        if not key or key in known or key in seen:
            return
        for prerequisite in dependencies.get(key, []):
            add(prerequisite)
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
