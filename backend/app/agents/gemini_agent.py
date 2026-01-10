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
        except GeminiError as e:
            return AgentResult(
                agent=self.name,
                score=0,
                confidence="Low",
                reasons=[f"{self.name} failed: {str(e)[:140]}"],
                ok=False,
            )
        except Exception as e:  # safety net
            return AgentResult(
                agent=self.name,
                score=0,
                confidence="Low",
                reasons=[f"{self.name} failed: {type(e).__name__}"],
                ok=False,
            )

        score = int(verdict.get("risk_score", 0))
        category = str(verdict.get("category", "")).strip()
        reasoning = str(verdict.get("reasoning", "")).strip()
        advice = str(verdict.get("advice", "")).strip()

        reasons: list[str] = []
        if category or reasoning:
            combined = (f"{category}: {reasoning}" if category else reasoning).strip()
            if combined:
                reasons.append(combined)
        if advice:
            reasons.append(f"Advice: {advice}")

        # Keep reasons tight so this agent doesn't dominate the combined output.
        reasons = [r for r in reasons if isinstance(r, str) and r.strip()][0:8]

        confidence = "High" if score >= 70 else "Medium" if score >= 35 else "Low"

        return AgentResult(
            agent=self.name,
            score=max(0, min(100, score)),
            confidence=confidence if confidence in {"Low", "Medium", "High"} else "Low",
            reasons=reasons,
            ok=True,
        )
