import ast
import json
import re
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_fixed

from app.core.settings import settings
from app.services.json_utils import extract_first_json_object


class GeminiError(RuntimeError):
    pass


def _is_retryable_error(exc: BaseException) -> bool:
    # Network/transient conditions.
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    if isinstance(exc, GeminiError):
        msg = str(exc).lower()
        # Retry on transient API errors and format glitches.
        if "api error 429" in msg:
            return True
        if "api error 5" in msg:
            return True
        if "empty candidate text" in msg:
            return True
        if "did not return valid json" in msg:
            return True
    return False


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

    # 1) Strict JSON parse.
    try:
        data = json.loads(txt)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # 2) Best-effort: pull the first JSON object from surrounding text.
    try:
        data = extract_first_json_object(txt)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 3) Fallback: some models return Python-like dicts with single quotes.
    #    ast.literal_eval is safe (no code execution) and works for dict/list/str/int.
    s = (txt or "").strip()
    try:
        val = ast.literal_eval(s)
        if isinstance(val, dict):
            return val
    except Exception:
        pass

    # 4) Last resort: attempt to extract the outermost {...} and literal-eval it.
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        chunk = s[start : end + 1]
        try:
            val = ast.literal_eval(chunk)
            if isinstance(val, dict):
                return val
        except Exception:
            pass

    raise GeminiError("Model did not return valid JSON")


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

    # Delimiters: keep instruction and data separate to reduce irrelevant answers.
    input_payload = {
        "text": text or "",
        "links": links or [],
        "metadata": metadata or {},
    }
    input_text = json.dumps(input_payload, ensure_ascii=False, indent=2)

    # If the system prompt includes a template placeholder, inject the input there.
    if "{input_text}" in resolved_system_prompt:
        resolved_system_prompt = resolved_system_prompt.replace("{input_text}", input_text)

    user_prompt = "Analyze the content in <input_data>. Return strict JSON only."

    # JSON mode + schema: strongly reduces format drift.
    response_schema: dict[str, Any] = {
        "type": "object",
        "required": [
            "risk_score",
            "risk_level",
            "category",
            "reasoning",
            "advice",
            "advice_hindi",
            "scam_type_local",
        ],
        "properties": {
            "risk_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "risk_level": {
                "type": "string",
                "enum": ["High", "Medium", "Low", "Safe", "Caution", "Critical"],
            },
            "category": {"type": "string"},
            "reasoning": {"type": "string"},
            "advice": {"type": "string"},
            "advice_hindi": {"type": "string"},
            "scam_type_local": {"type": "string"},
        },
    }

    # For image models, Gemini works best when the image is first in the context.
    parts: list[dict[str, Any]] = []
    if image_base64_list:
        for b64 in image_base64_list:
            parts.append(_image_part_from_base64(b64))
    parts.append({"text": user_prompt})

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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception(_is_retryable_error),
        reraise=True,
    )
    def _call_once() -> dict[str, Any]:
        with httpx.Client(timeout=60.0) as client:
            r = client.post(url, params={"key": settings.gemini_api_key}, json=payload)

        if r.status_code >= 400:
            raise GeminiError(f"Gemini API error {r.status_code}: {r.text[:500]}")

        return _extract_json_from_response(r.json())

    return _call_once()
