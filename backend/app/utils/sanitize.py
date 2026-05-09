"""Tiny sanitisers for user-supplied strings."""
from __future__ import annotations

import html
import re

_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def sanitize_text(value: str, *, max_len: int = 8000) -> str:
    if not value:
        return ""
    cleaned = _CONTROL.sub("", value)
    cleaned = html.escape(cleaned, quote=False)
    return cleaned[:max_len]
