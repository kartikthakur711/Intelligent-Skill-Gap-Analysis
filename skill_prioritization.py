"""Skill gap ranking based on observed loaded-catalog posting counts."""
from __future__ import annotations

import re
import pandas as pd


def normalize_skill(skill):
    skill = str(skill).lower().strip().replace(".", "").replace("-", " ")
    return " ".join(skill.split())


def priority_from_demand(missing_skills, catalog):
    """Rank gaps by observed catalog posting frequency, with explicit unknowns."""
    if not missing_skills:
        return pd.DataFrame(columns=["Skill", "Job Demand", "Demand Score", "Priority", "Reason"])

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
            reason = f"Appears in {count} loaded job postings; normalized to the most frequent skill."
        rows.append({
            "Skill": skill,
            "Job Demand": count,
            "Demand Score": round(score, 3),
            "Priority": priority,
            "Reason": reason,
        })
    return pd.DataFrame(rows).sort_values(
        ["Demand Score", "Skill"], ascending=[False, True], kind="stable"
    ).reset_index(drop=True)
