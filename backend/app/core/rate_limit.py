import time
from collections import defaultdict, deque

from fastapi import Header, Request, HTTPException

from app.core.settings import settings


_requests: dict[str, deque[float]] = defaultdict(deque)


def _client_id(request: Request, x_api_key: str | None) -> str:
    if x_api_key:
        return f"key:{x_api_key}"
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


def rate_limit(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    rpm = settings.rate_limit_rpm
    if rpm <= 0:
        return

    now = time.time()
    window_seconds = 60.0
    cid = _client_id(request, x_api_key)
    q = _requests[cid]

    while q and (now - q[0]) > window_seconds:
        q.popleft()

    if len(q) >= rpm:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    q.append(now)
