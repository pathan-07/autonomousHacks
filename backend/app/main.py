from fastapi import FastAPI

from app.api.routes import router
from app.core.settings import settings
from app.db.sqlite import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="AI Scam Detection API", version="0.1.0")

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    app.include_router(router)
    return app


app = create_app()
