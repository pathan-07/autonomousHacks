from fastapi import APIRouter, Depends

from app.core.auth import require_api_key
from app.core.rate_limit import rate_limit
from app.core.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.analyze_service import analyze_request

router = APIRouter(prefix="", tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest, _auth=Depends(require_api_key), _rl=Depends(rate_limit)) -> AnalyzeResponse:
    return analyze_request(payload)
