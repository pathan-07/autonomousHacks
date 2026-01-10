import json
import re
from typing import Any

import httpx

from app.core.settings import settings


class GeminiError(RuntimeError):
    pass


_DATA_URL_RE = re.compile(r"^data:(?P<mime>[-\w.+/]+);base64,(?P<data>[A-Za-z0-9+/=\s]+)$", re.IGNORECASE)


def _image_part_from_base64(image_base64: str) -> dict[str, Any]:
    s = (image_base64 or "").strip()
    if not s:
        raise GeminiError("Empty image_base64")

    mime = "image/jpeg"
    data = s

    m = _DATA_URL_RE.match(s)
    if m:
        mime = (m.group("mime") or "image/jpeg").strip()
        data = (m.group("data") or "").strip()

    # Remove any whitespace/newlines in base64
    data = "".join(data.split())
    if not data:
        raise GeminiError("Empty image data")

    return {"inlineData": {"mimeType": mime, "data": data}}


def _extract_text_from_response(resp_json: dict[str, Any]) -> str:
    candidates = resp_json.get("candidates") or []
    if not candidates:
        raise GeminiError("No candidates returned")

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []

    texts: list[str] = []
    for p in parts:
        t = p.get("text")
        if isinstance(t, str):
            texts.append(t)

    out = "".join(texts).strip()
    if not out:
        raise GeminiError("Empty candidate text")
    return out


def _extract_json_from_response(resp_json: dict[str, Any]) -> dict[str, Any]:
    """Gemini may return JSON in different shapes depending on settings."""
    # When responseMimeType is application/json, the text part typically contains JSON.
    txt = _extract_text_from_response(resp_json)
    try:
        data = json.loads(txt)
    except json.JSONDecodeError as e:
        raise GeminiError(f"Model did not return valid JSON: {e}")
    if not isinstance(data, dict):
        raise GeminiError("Model JSON is not an object")
    return data


def generate_scam_verdict_json(
    *,
    text: str,
    links: list[str],
    metadata: dict[str, Any] | None,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    max_output_tokens: int | None = None,
    image_base64_list: list[str] | None = None,
) -> dict[str, Any]:
    if not settings.gemini_api_key:
        raise GeminiError("GEMINI_API_KEY not configured")

    resolved_system_prompt = (system_prompt or "").strip() or settings.get_gemini_system_prompt()
    if not resolved_system_prompt:
        raise GeminiError("Gemini system prompt is empty/missing")

    resolved_model = (model or "").strip() or settings.gemini_model

    user_prompt = (
        "Analyze scam risk for the following content. Return strict JSON only.\n\n"
        "text: " + json.dumps(text or "") + "\n"
        "links: " + json.dumps(links or []) + "\n"
        "metadata: " + json.dumps(metadata or {}, ensure_ascii=False) + "\n"
    )

    # JSON mode + schema: strongly reduces format drift.
    response_schema: dict[str, Any] = {
        "type": "object",
        "required": ["risk_score", "risk_level", "confidence", "reasons", "recommended_action"],
        "properties": {
            "risk_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "risk_level": {"type": "string", "enum": ["Safe", "Caution", "High"]},
            "confidence": {"type": "string", "enum": ["Low", "Medium", "High"]},
            "reasons": {"type": "array", "minItems": 0, "maxItems": 12, "items": {"type": "string"}},
            "recommended_action": {"type": "string"},
        },
    }

    parts: list[dict[str, Any]] = [{"text": user_prompt}]

    if image_base64_list:
        for b64 in image_base64_list:
            parts.append(_image_part_from_base64(b64))

    payload: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": resolved_system_prompt}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": settings.gemini_temperature if temperature is None else float(temperature),
            "topP": settings.gemini_top_p if top_p is None else float(top_p),
            "maxOutputTokens": settings.gemini_max_output_tokens if max_output_tokens is None else int(max_output_tokens),
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        },
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{resolved_model}:generateContent"

    with httpx.Client(timeout=60.0) as client:
        r = client.post(url, params={"key": settings.gemini_api_key}, json=payload)

    if r.status_code >= 400:
        raise GeminiError(f"Gemini API error {r.status_code}: {r.text[:500]}")

    return _extract_json_from_response(r.json())
