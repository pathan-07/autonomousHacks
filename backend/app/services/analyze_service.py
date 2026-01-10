import json
import hashlib
import uuid

from app.core.schemas import AgentBreakdown, AnalyzeRequest, AnalyzeResponse
from app.core.decision import decide
from app.core.redaction import redact_analyze_payload
from app.db.sqlite import cleanup_old_interactions, get_cached_analysis, insert_interaction, upsert_cached_analysis
from app.services.orchestrator import run_agents


def _hash_request(redacted: AnalyzeRequest) -> str:
    # Use redacted content to avoid caching keyed on raw PII.
    stable = {
        "text": redacted.text or "",
        "links": redacted.links or [],
        "image_url": redacted.image_url or "",
        # base64 could be large; keep exact-match semantics but avoid dumping bytes into DB.
        "image_base64": (redacted.image_base64 or "")[:64],
        "metadata": (redacted.metadata.model_dump() if redacted.metadata else {}),
    }
    blob = json.dumps(stable, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def analyze_request(payload: AnalyzeRequest) -> AnalyzeResponse:
    cleanup_old_interactions()

    interaction_id = str(uuid.uuid4())
    redacted = redact_analyze_payload(payload)

    cache_key = _hash_request(redacted)
    cached = get_cached_analysis(input_hash=cache_key, max_age_seconds=None)
    if cached:
        try:
            response = AnalyzeResponse.model_validate(cached)
        except Exception:
            response = None
        if response is not None:
            insert_interaction(
                interaction_id=interaction_id,
                redacted_text=redacted.text,
                links_json=json.dumps(redacted.links),
                risk_score=response.risk_score,
                risk_level=response.risk_level,
                confidence=response.confidence,
            )
            return response

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

    # Store for exact-match cache.
    upsert_cached_analysis(input_hash=cache_key, response=response.model_dump())

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
