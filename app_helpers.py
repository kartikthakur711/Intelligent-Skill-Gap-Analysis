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
