import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.agents.audio_agent import AudioAgent

from app.core.auth import require_api_key
from app.core.rate_limit import rate_limit
from app.core.schemas import AgentBreakdown, AnalyzeRequest, AnalyzeResponse
from app.services.analyze_service import analyze_request

router = APIRouter(prefix="", tags=["analyze"])


def _max_confidence(a: str, b: str) -> str:
    order = {"Low": 0, "Medium": 1, "High": 2}
    return a if order.get(a, 0) >= order.get(b, 0) else b


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: Request, _auth=Depends(require_api_key), _rl=Depends(rate_limit)) -> AnalyzeResponse:
    content_type = (request.headers.get("content-type") or "").lower()

    payload: AnalyzeRequest
    audio_bytes: bytes | None = None
    audio_mime: str | None = None

    if "multipart/form-data" in content_type:
        form = await request.form()

        text_val = form.get("text")
        image_url_val = form.get("image_url")

        text = text_val if isinstance(text_val, str) else None
        image_url = image_url_val if isinstance(image_url_val, str) else None

        links: list[str] = []
        links_val = form.get("links")
        if isinstance(links_val, str) and links_val.strip():
            # Support either JSON array or newline-separated.
            try:
                parsed = json.loads(links_val)
                if isinstance(parsed, list):
                    links = [str(x) for x in parsed if str(x).strip()]
            except Exception:
                links = [ln.strip() for ln in links_val.splitlines() if ln.strip()]

        audio_file = form.get("audio_file")
        if audio_file is not None:
            # Starlette UploadFile
            try:
                audio_mime = getattr(audio_file, "content_type", None)
                audio_bytes = await audio_file.read()
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid audio_file")

        payload = AnalyzeRequest(text=text, image_url=image_url, links=links)
    else:
        try:
            raw = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")

        try:
            payload = AnalyzeRequest.model_validate(raw)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid request body")

    # Run existing multi-agent analysis (text/link/image).
    response = analyze_request(payload)

    # Optional: run audio analysis and merge into the verdict.
    if audio_bytes:
        agent = AudioAgent()
        try:
            audio_analysis = await agent.analyze(audio_bytes=audio_bytes, mime_type=audio_mime or "audio/mpeg")
            response.audio_analysis = audio_analysis

            audio_score = int(audio_analysis.get("risk_score", 0) or 0)
            audio_score = max(0, min(100, audio_score))
            category = str(audio_analysis.get("category", "")).strip()
            reasoning = str(audio_analysis.get("reasoning", "")).strip()
            snippet = str(audio_analysis.get("transcript_snippet", "")).strip()

            audio_reasons: list[str] = []
            if category or reasoning:
                audio_reasons.append((f"Audio ({category}): {reasoning}" if category else f"Audio: {reasoning}").strip())
            if snippet:
                audio_reasons.append(f"Transcript snippet: {snippet}")

            audio_reasons = [r for r in audio_reasons if r.strip()][:6]

            if response.agent_results is None:
                response.agent_results = []
            response.agent_results.append(
                AgentBreakdown(
                    agent="AudioAgent",
                    score=audio_score,
                    confidence="High" if audio_score >= 70 else "Medium" if audio_score >= 35 else "Low",
                    reasons=audio_reasons,
                    ok=True,
                )
            )

            # Merge: let audio raise the overall risk score if it's higher.
            if audio_score > int(response.risk_score or 0):
                response.risk_score = audio_score
                if audio_score < 30:
                    response.risk_level = "Safe"
                elif audio_score <= 60:
                    response.risk_level = "Caution"
                else:
                    response.risk_level = "High"

            # Merge some audio reasons into top-level reasons.
            if audio_reasons:
                response.reasons = list(response.reasons or []) + audio_reasons
                response.reasons = [r for r in response.reasons if isinstance(r, str) and r.strip()][:12]

            # Confidence: take the max.
            response.confidence = _max_confidence(
                response.confidence,
                "High" if audio_score >= 70 else "Medium" if audio_score >= 35 else "Low",
            )
        except Exception as e:
            response.audio_analysis = {"error": "Failed to analyze audio", "details": type(e).__name__}

    return response
