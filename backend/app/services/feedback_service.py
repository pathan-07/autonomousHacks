from app.core.schemas import FeedbackRequest, FeedbackResponse
from app.db.sqlite import insert_feedback


def store_feedback(payload: FeedbackRequest) -> FeedbackResponse:
    verdict = payload.user_verdict.strip().lower()
    if verdict not in {"scam", "safe"}:
        return FeedbackResponse(ok=False)

    insert_feedback(interaction_id=payload.interaction_id, user_verdict=verdict, notes=payload.notes)
    return FeedbackResponse(ok=True)
