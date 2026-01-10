import json
import uuid

from app.core.schemas import AgentBreakdown, AnalyzeRequest, AnalyzeResponse
from app.core.decision import decide
from app.core.redaction import redact_analyze_payload
from app.db.sqlite import cleanup_old_interactions, insert_interaction
from app.services.orchestrator import run_agents


def analyze_request(payload: AnalyzeRequest) -> AnalyzeResponse:
    cleanup_old_interactions()

    interaction_id = str(uuid.uuid4())
    redacted = redact_analyze_payload(payload)

    agent_results = run_agents(redacted)
    decision = decide(agent_results)
    response = AnalyzeResponse(
        risk_score=decision.risk_score,
        risk_level=decision.risk_level,
        confidence=decision.confidence,
        reasons=decision.reasons,
        recommended_action=decision.recommended_action,
        agent_results=[
            AgentBreakdown(
                agent=r.agent,
                score=int(r.score),
                confidence=str(r.confidence),
                reasons=list(r.reasons),
                ok=bool(getattr(r, "ok", True)),
            )
            for r in agent_results
        ],
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
