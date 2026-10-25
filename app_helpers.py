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
