"""Lightweight visit context helpers for consented studio events."""
from __future__ import annotations

import ipaddress
import json
import re
import urllib.error
import urllib.request
from typing import Any

from django.core.cache import cache


_MOBILE = re.compile(r"Mobile|Android.*Mobile|iPhone|iPod|webOS|BlackBerry|IEMobile", re.I)
_TABLET = re.compile(r"iPad|Android(?!.*Mobile)|Tablet", re.I)

# Rough place from IP (city/country). Not GPS. Cached so repeat visits stay fast.
_GEO_CACHE_SECONDS = 60 * 60 * 24 * 7


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


def _is_public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address((value or "").strip())
    except ValueError:
        return False
    return not (
        address.is_private
        or address.is_loopback
        or address.is_reserved
        or address.is_multicast
        or address.is_link_local
        or address.is_unspecified
    )


def format_location_label(*, city: str = "", region: str = "", country: str = "", country_code: str = "") -> str:
    """Short label for Desk, e.g. Accra, Ghana."""
    city = (city or "").strip()
    region = (region or "").strip()
    country = (country or "").strip()
    code = (country_code or "").strip().upper()
    if city and country:
        return f"{city}, {country}"
    if city and code:
        return f"{city}, {code}"
    if region and country:
        return f"{region}, {country}"
    if country:
        return country
    if code:
        return code
    return ""


def lookup_ip_location(ip: str) -> dict[str, str]:
    """
    Map a public IP to an approximate place.
    Uses a free HTTPS lookup and remembers the answer for a week.
    Returns empty fields when the IP is local or the lookup fails.
    """
    raw = (ip or "").strip()
    empty = {"country_code": "", "country": "", "city": "", "region": ""}
    if not _is_public_ip(raw):
        return empty

    cache_key = f"studio-geoip:{raw}"
    cached = cache.get(cache_key)
    if isinstance(cached, dict):
        return {
            "country_code": str(cached.get("country_code") or "")[:2],
            "country": str(cached.get("country") or "")[:80],
            "city": str(cached.get("city") or "")[:80],
            "region": str(cached.get("region") or "")[:80],
        }

    result = dict(empty)
    try:
        request = urllib.request.Request(
            f"https://ipwho.is/{raw}",
            headers={"User-Agent": "TheCreativeBranders-Desk/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=1.5) as response:
            payload: Any = json.loads(response.read().decode("utf-8", errors="replace"))
        if isinstance(payload, dict) and payload.get("success") is True:
            result = {
                "country_code": str(payload.get("country_code") or "").strip().upper()[:2],
                "country": str(payload.get("country") or "").strip()[:80],
                "city": str(payload.get("city") or "").strip()[:80],
                "region": str(payload.get("region") or "").strip()[:80],
            }
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError):
        result = dict(empty)

    cache.set(cache_key, result, _GEO_CACHE_SECONDS)
    return result
