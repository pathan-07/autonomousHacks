from fastapi import APIRouter, Depends

from app.core.auth import require_api_key
from app.core.rate_limit import rate_limit
from app.core.schemas import FeedbackRequest, FeedbackResponse
from app.services.feedback_service import store_feedback

router = APIRouter(prefix="", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
def feedback(payload: FeedbackRequest, _auth=Depends(require_api_key), _rl=Depends(rate_limit)) -> FeedbackResponse:
    return store_feedback(payload)
