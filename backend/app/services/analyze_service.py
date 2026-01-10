import json
import uuid

from app.core.schemas import AnalyzeRequest, AnalyzeResponse
from app.core.decision import decide
from app.core.redaction import redact_analyze_payload
from app.core.settings import settings
from app.db.sqlite import cleanup_old_interactions, insert_interaction
from app.services.orchestrator import run_agents
from app.services.gemini_client import GeminiError, generate_scam_verdict_json


def analyze_request(payload: AnalyzeRequest) -> AnalyzeResponse:
    cleanup_old_interactions()

    interaction_id = str(uuid.uuid4())
    redacted = redact_analyze_payload(payload)

    # Prefer Gemini structured output when configured; fall back to local agents.
    if settings.gemini_api_key:
        try:
            verdict = generate_scam_verdict_json(
                text=redacted.text or "",
                links=redacted.links or [],
                metadata=(redacted.metadata.model_dump() if redacted.metadata else None),
            )

            response = AnalyzeResponse(
                risk_score=int(verdict.get("risk_score", 0)),
                risk_level=str(verdict.get("risk_level", "Safe")),
                confidence=str(verdict.get("confidence", "Low")),
                reasons=list(verdict.get("reasons", [])),
                recommended_action=str(verdict.get("recommended_action", "")),
            )
        except GeminiError as e:
            agent_results = run_agents(redacted)
            decision = decide(agent_results)
            response = AnalyzeResponse(
                risk_score=decision.risk_score,
                risk_level=decision.risk_level,
                confidence=decision.confidence,
                reasons=(decision.reasons + [f"Gemini fallback: {str(e)[:120]}"])[0:12],
                recommended_action=decision.recommended_action,
            )
    else:
        agent_results = run_agents(redacted)
        decision = decide(agent_results)
        response = AnalyzeResponse(
            risk_score=decision.risk_score,
            risk_level=decision.risk_level,
            confidence=decision.confidence,
            reasons=decision.reasons,
            recommended_action=decision.recommended_action,
        )

    insert_interaction(
        interaction_id=interaction_id,
        redacted_text=redacted.text,
        links_json=json.dumps(redacted.links),
        risk_score=response.risk_score,
        risk_level=response.risk_level,
        confidence=response.confidence,
    )

    # Normalize score/level consistency just in case.
    response.risk_score = max(0, min(100, int(response.risk_score)))
    if response.risk_score < 30:
        response.risk_level = "Safe"
    elif response.risk_score <= 60:
        response.risk_level = "Caution"
    else:
        response.risk_level = "High"

    if response.confidence not in {"Low", "Medium", "High"}:
        response.confidence = "Low"

    return response
