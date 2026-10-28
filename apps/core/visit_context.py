"""Lightweight visit context helpers for consented studio events."""
from __future__ import annotations

import re


_MOBILE = re.compile(r"Mobile|Android.*Mobile|iPhone|iPod|webOS|BlackBerry|IEMobile", re.I)
_TABLET = re.compile(r"iPad|Android(?!.*Mobile)|Tablet", re.I)


def device_from_user_agent(user_agent: str, hint: str = "") -> str:
    """Return mobile, tablet, desktop, or unknown."""
    hint = (hint or "").strip().lower()
    if hint in {"mobile", "tablet", "desktop"}:
        return hint
    ua = user_agent or ""
    if not ua:
        return "unknown"
    if _TABLET.search(ua):
        return "tablet"
    if _MOBILE.search(ua):
        return "mobile"
    return "desktop"
