from __future__ import annotations

import base64

import httpx

from app.agents.base import AgentResult, BaseAgent
from app.core.schemas import AnalyzeRequest
from app.services.gemini_client import GeminiError, generate_scam_verdict_json


class GeminiImageAgent(BaseAgent):
    def __init__(self, *, model: str, name: str | None = None) -> None:
        self.model = model
        self.name = name or f"GeminiImageAgent[{model}]"

    def _fetch_image_as_data_url(self, url: str) -> str:
        # Fetch image bytes and convert to data URL so gemini_client can handle it.
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            r = client.get(url)
        r.raise_for_status()

        content_type = (r.headers.get("content-type") or "image/jpeg").split(";")[0].strip()
        data_b64 = base64.b64encode(r.content).decode("ascii")
        return f"data:{content_type};base64,{data_b64}"

    def run(self, payload: AnalyzeRequest) -> AgentResult:
        images: list[str] = []

        if payload.image_base64:
            images.append(payload.image_base64)

        if payload.image_url and not images:
            # Only fetch if base64 isn't provided (avoid duplicating work).
            try:
                images.append(self._fetch_image_as_data_url(payload.image_url))
            except Exception as e:
                return AgentResult(
                    agent=self.name,
                    score=0,
                    confidence="Low",
                    reasons=[f"Image fetch failed: {type(e).__name__}"],
                    ok=False,
                )

        if not images:
            return AgentResult(agent=self.name, score=0, confidence="Low", reasons=[], ok=True)

        try:
            verdict = generate_scam_verdict_json(
                text=(payload.text or ""),
                links=(payload.links or []),
                metadata=(payload.metadata.model_dump() if payload.metadata else None),
                model=self.model,
                image_base64_list=images,
            )
        except Exception as e:
            return AgentResult(
                agent=self.name,
                score=0,
                confidence="Low",
                reasons=[f"Gemini failed: {str(e)[:100]}"],
                ok=False,
            )

        score = int(verdict.get("risk_score", 0))
        reasoning = str(verdict.get("reasoning", "")).strip()
        advice_en = str(verdict.get("advice", "")).strip()
        advice_hi = str(verdict.get("advice_hindi", "")).strip()
        local_scam = str(verdict.get("scam_type_local", "")).strip()
        category = str(verdict.get("category", "")).strip()

        reasons: list[str] = []
        if reasoning:
            reasons.append(reasoning)
        if category and category != "Legitimate":
            reasons.append(f"Category: {category}")
        if local_scam:
            reasons.append(f"Scam Type: {local_scam}")
        if advice_en:
            reasons.append(f"Advice: {advice_en}")
        if advice_hi:
            reasons.append(f"🇮🇳 Hindi Advice: {advice_hi}")

        confidence = "High" if score >= 70 else "Medium" if score >= 35 else "Low"

        return AgentResult(
            agent=self.name,
            score=max(0, min(100, score)),
            confidence=confidence,
            reasons=reasons[:10],
            ok=True,
        )
