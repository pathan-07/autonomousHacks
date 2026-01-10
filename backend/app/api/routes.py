from fastapi import APIRouter

from app.api.routes_analyze import router as analyze_router
from app.api.routes_feedback import router as feedback_router

router = APIRouter()
router.include_router(analyze_router)
router.include_router(feedback_router)
