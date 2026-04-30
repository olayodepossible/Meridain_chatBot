"""Tests for in-memory rate limiting."""

import time

import pytest
from fastapi import HTTPException

from app.rate_limit import InMemoryRateLimiter


def test_rate_limiter_allows_within_limit() -> None:
    limiter = InMemoryRateLimiter()
    limiter.check("k1", limit=3, window_seconds=60)
    limiter.check("k1", limit=3, window_seconds=60)
    limiter.check("k1", limit=3, window_seconds=60)


def test_rate_limiter_blocks_over_limit() -> None:
    limiter = InMemoryRateLimiter()
    limiter.check("k2", limit=2, window_seconds=60)
    limiter.check("k2", limit=2, window_seconds=60)
    with pytest.raises(HTTPException) as exc:
        limiter.check("k2", limit=2, window_seconds=60)
    assert exc.value.status_code == 429


def test_rate_limiter_sliding_window_expires() -> None:
    limiter = InMemoryRateLimiter()
    limiter.check("k3", limit=1, window_seconds=1)
    time.sleep(1.05)
    limiter.check("k3", limit=1, window_seconds=1)


def test_rate_limiter_independent_keys() -> None:
    limiter = InMemoryRateLimiter()
    limiter.check("a", limit=1, window_seconds=60)
    limiter.check("b", limit=1, window_seconds=60)
