import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.config import Settings, get_settings
from app.schemas import UserContext
from app.security import get_current_user


class InMemoryRateLimiter:
    """Small per-process sliding-window limiter for the API gateway."""

    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        window_start = now - window_seconds
        bucket = self._requests[key]

        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded.",
            )

        bucket.append(now)


rate_limiter = InMemoryRateLimiter()


async def enforce_rate_limit(
    request: Request,
    user: Annotated[UserContext, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserContext:
    client_host = request.client.host if request.client else "unknown"
    key = f"{user.user_id}:{client_host}"
    rate_limiter.check(key, settings.rate_limit_requests, settings.rate_limit_window_seconds)
    return user
