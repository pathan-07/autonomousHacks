from __future__ import annotations

from typing import Any

import httpx

from app.core.settings import settings


class SafeBrowsingError(RuntimeError):
    pass


def find_threats(*, urls: list[str]) -> dict[str, list[str]]:
    """Return a map: url -> list of threatType strings."""
    if not settings.safe_browsing_api_key:
        raise SafeBrowsingError("SAFE_BROWSING_API_KEY not configured")

    clean_urls = [u.strip() for u in (urls or []) if isinstance(u, str) and u.strip()]
    if not clean_urls:
        return {}

    payload: dict[str, Any] = {
        "client": {"clientId": "autonomousHacks", "clientVersion": "0.1"},
        "threatInfo": {
            "threatTypes": [
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION",
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": u} for u in clean_urls],
        },
    }

    url = "https://safebrowsing.googleapis.com/v4/threatMatches:find"

    with httpx.Client(timeout=15.0) as client:
        r = client.post(url, params={"key": settings.safe_browsing_api_key}, json=payload)

    if r.status_code >= 400:
        raise SafeBrowsingError(f"Safe Browsing API error {r.status_code}: {r.text[:300]}")

    data = r.json()
    matches = data.get("matches") or []

    out: dict[str, list[str]] = {}
    for m in matches:
        try:
            threat = str(m.get("threatType") or "").strip()
            threat_url = str(((m.get("threat") or {}).get("url")) or "").strip()
        except Exception:
            continue
        if threat and threat_url:
            out.setdefault(threat_url, []).append(threat)

    return out
