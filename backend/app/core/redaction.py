import re

from app.core.schemas import AnalyzeRequest

_PHONE_RE = re.compile(r"\b(?:\+?91[\-\s]?)?[6-9]\d{9}\b")
_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
_UPI_RE = re.compile(r"\b[a-zA-Z0-9._-]{2,}@[a-zA-Z]{2,}\b")


def redact_text(text: str) -> str:
    t = text
    t = _PHONE_RE.sub("[PHONE]", t)
    t = _EMAIL_RE.sub("[EMAIL]", t)
    # UPI IDs often look like name@bank; this is a heuristic and may over-match.
    t = _UPI_RE.sub("[UPI_ID]", t)
    return t


def redact_analyze_payload(payload: AnalyzeRequest) -> AnalyzeRequest:
    redacted_text = redact_text(payload.text) if payload.text else None

    # Do not modify binary fields; only redact text + links.
    redacted_links = [redact_text(x) for x in (payload.links or [])]

    return AnalyzeRequest(
        text=redacted_text,
        image_base64=payload.image_base64,
        image_url=payload.image_url,
        audio_base64=payload.audio_base64,
        audio_url=payload.audio_url,
        links=redacted_links,
        metadata=payload.metadata,
    )
