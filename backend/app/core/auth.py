from fastapi import Header, HTTPException

from app.core.settings import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not settings.backend_api_key:
        return
    if x_api_key != settings.backend_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
