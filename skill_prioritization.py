"""Rank missing skills by loaded-catalog frequency, not distinct vacancies."""
from __future__ import annotations

import pandas as pd


def normalize_skill(skill):
    skill = str(skill).lower().strip().replace(".", "").replace("-", " ")
    skill = " ".join(skill.split())
    aliases = {
        "scikit learn": "scikit learn",
        "auto cad": "autocad",
        "tensorflow keras": "tensorflow",
        "mysql database": "mysql",
        "r or java": "r or java",
    }
    return aliases.get(skill, skill)


def priority_from_demand(missing_skills, catalog):
    """Rank gaps by observed catalog posting frequency, with explicit unknowns."""
    if not missing_skills:
        return pd.DataFrame(columns=["Skill", "Catalog Rows", "Catalog Frequency Score", "Priority", "Reason"])

    counter = {}
    if catalog is not None and "skills_list" in catalog.columns:
        for skills in catalog["skills_list"].dropna():
            if not isinstance(skills, (list, tuple, set)):
                continue
            for skill in skills:
                key = normalize_skill(skill)
                if key:
                    counter[key] = counter.get(key, 0) + 1

    max_demand = max(counter.values(), default=0)
    rows = []
    for skill in missing_skills:
        count = counter.get(normalize_skill(skill), 0)
        if max_demand == 0:
            score, priority = 0.0, "Unknown"
            reason = "Demand data is unavailable; priority is not estimated."
        elif count == 0:
            score, priority = 0.0, "Low"
            reason = "No matching skill occurrences were found in the loaded catalog."
        else:
            score = count / max_demand
            priority = "High" if score >= 0.50 else "Medium" if score >= 0.20 else "Low"
            reason = f"Found in {count} loaded catalog rows; relative to the most frequent skill. Rows may include repeated/template records."
        rows.append({
            "Skill": skill,
            "Catalog Rows": count,
            "Catalog Frequency Score": round(score, 3),
            "Priority": priority,
            "Reason": reason,
        })
    return pd.DataFrame(rows).sort_values(
        ["Catalog Frequency Score", "Skill"], ascending=[False, True], kind="stable"
    ).reset_index(drop=True)
