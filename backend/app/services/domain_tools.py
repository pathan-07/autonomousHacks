from __future__ import annotations

import logging
from datetime import datetime, date, timezone
from functools import lru_cache

import tldextract
import whois

logger = logging.getLogger(__name__)


def extract_registered_domain(url: str) -> str:
    """Extracts the registrable domain (eTLD+1), e.g. https://a.b.co.uk/x -> b.co.uk."""
    ext = tldextract.extract(url or "")
    if not ext.domain or not ext.suffix:
        return ""
    return f"{ext.domain}.{ext.suffix}".lower()


def _to_datetime_utc(value: object) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    if isinstance(value, date):
        # Date without time; assume midnight UTC.
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)

    # Some WHOIS libraries may return strings; keep this tool conservative.
    return None


@lru_cache(maxsize=1024)
def get_domain_age_days(url: str) -> int | None:
    """Returns domain age in days.

    - Returns an integer >= 0 when known
    - Returns None when age cannot be determined (WHOIS blocked/unavailable/no creation date)

    Note: cached in-process to reduce repeated WHOIS calls.
    """
    registered = extract_registered_domain(url)
    if not registered:
        return None

    try:
        info = whois.whois(registered)
        creation_date = getattr(info, "creation_date", None)

        if isinstance(creation_date, list):
            creation_date = creation_date[0] if creation_date else None

        created_dt = _to_datetime_utc(creation_date)
        if not created_dt:
            return None

        age_days = (datetime.now(timezone.utc) - created_dt).days
        return max(0, int(age_days))
    except Exception as e:
        # WHOIS is notoriously noisy; keep failures out of agent code.
        logger.info("WHOIS lookup failed for %s (%s): %s", registered, url, type(e).__name__)
        return None


def get_domain_age_fact(url: str) -> str:
    """Returns a human-readable fact string suitable for an LLM prompt."""
    days = get_domain_age_days(url)
    if days is None:
        return "Domain Age: Unknown (Privacy protected or lookup failed)"

    if days < 30:
        return f"CRITICAL FACT: This domain is extremely new ({days} days old). High risk of phishing."
    if days < 365:
        return f"FACT: This domain is {days} days old."
    return f"FACT: This domain is established ({days} days old)."
