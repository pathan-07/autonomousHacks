from __future__ import annotations

import json
import base64
from typing import Any

import httpx

from app.core.settings import settings
from app.services.json_utils import extract_first_json_object


class AudioAgent:
    """Analyze an uploaded audio clip for vishing / impersonation scams via Gemini."""

    def __init__(self, *, model: str | None = None) -> None:
        self.model = (model or settings.gemini_audio_model or "").strip() or "gemini-1.5-flash"

    async def analyze(self, *, audio_bytes: bytes, mime_type: str) -> dict[str, Any]:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")

        prompt = (
            "You are a Scam Detection Expert. Listen to this audio recording carefully.\n"
            "Analyze for threats, urgency, and 'Digital Arrest' keywords.\n\n"
            "Return strict JSON:\n"
            "{\n"
            '  "risk_score": <0-100>,\n'
            '  "risk_level": "High/Medium/Low",\n'
            '  "category": "Vishing / Sextortion / Impersonation",\n'
            '  "reasoning": "Explain why this is suspicious",\n'
            '  "advice_hindi": "Safety advice in Hindi (Devanagari)",\n'
            '  "transcript_snippet": "Suspicious sentence transcript"\n'
            "}"
        )

        # Gemini expects base64 for inlineData.
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        resolved_mime = (mime_type or "audio/mpeg").split(";")[0].strip() or "audio/mpeg"

        response_schema: dict[str, Any] = {
            "type": "object",
            "required": ["risk_score", "risk_level", "category", "reasoning", "advice_hindi"],
            "properties": {
                "risk_score": {"type": "integer", "minimum": 0, "maximum": 100},
                "risk_level": {"type": "string"},
                "category": {"type": "string"},
                "reasoning": {"type": "string"},
                "advice_hindi": {"type": "string"},
                "transcript_snippet": {"type": "string"},
            },
        }

        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"inlineData": {"mimeType": resolved_mime, "data": audio_b64}},
                        {"text": prompt},
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.9,
                "maxOutputTokens": 900,
                "responseMimeType": "application/json",
                "responseSchema": response_schema,
            },
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

        async with httpx.AsyncClient(timeout=90.0) as client:
            r = await client.post(url, params={"key": settings.gemini_api_key}, json=payload)

        if r.status_code >= 400:
            raise RuntimeError(f"Gemini API error {r.status_code}: {r.text[:500]}")

        resp_json = r.json()
        candidates = resp_json.get("candidates") or []
        if not candidates:
            raise RuntimeError("No candidates returned")

        content = (candidates[0] or {}).get("content") or {}
        parts = content.get("parts") or []
        text_out = "".join([(p.get("text") or "") for p in parts if isinstance(p, dict)]).strip()
        if not text_out:
            raise RuntimeError("Empty response text")

        try:
            parsed = json.loads(text_out)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # Fallback: extract first JSON object from any surrounding text.
        return extract_first_json_object(text_out)
