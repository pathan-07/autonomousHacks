from __future__ import annotations

from app.agents.base import AgentResult, BaseAgent
from app.core.schemas import AnalyzeRequest
from app.services.gemini_client import GeminiError, generate_scam_verdict_json


class GeminiAgent(BaseAgent):
    def __init__(self, *, model: str, name: str | None = None) -> None:
        self.model = model
        self.name = name or f"GeminiAgent[{model}]"

    def run(self, payload: AnalyzeRequest) -> AgentResult:
        try:
            verdict = generate_scam_verdict_json(
                text=(payload.text or ""),
                links=(payload.links or []),
                metadata=(payload.metadata.model_dump() if payload.metadata else None),
                model=self.model,
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
        advice_hi = str(verdict.get("advice_hindi", "")).strip()
        local_scam = str(verdict.get("scam_type_local", "")).strip()

        reasons: list[str] = []
        if reasoning:
            reasons.append(reasoning)
        if local_scam:
            reasons.append(f"Type: {local_scam}")
        if advice_hi:
            reasons.append(f"🇮🇳 Hindi Advice: {advice_hi}")

        return AgentResult(
            agent=self.name,
            score=max(0, min(100, score)),
            confidence=str(verdict.get("confidence", "Medium")),
            reasons=reasons[:8],
            ok=True,
        )
