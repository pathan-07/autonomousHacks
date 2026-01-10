from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.settings import settings
from app.db.sqlite import init_db

app = FastAPI(title="ScamShield API")


@app.on_event("startup")
def _startup() -> None:
    init_db()


# --- CRITICAL FIX FOR CLOUD RUN ---
# Allow your Frontend to talk to this Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows ALL origins (Safe for Hackathons)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your analysis routes
app.include_router(api_router)


@app.get("/")
def health_check():
    """Simple check to see if Backend is running"""
    return {"status": "online", "service": "ScamShield Agent Core"}
