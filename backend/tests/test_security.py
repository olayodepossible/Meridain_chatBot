"""Tests for frontend-auth user context extraction."""

import pytest
from fastapi import HTTPException, Request

from app.security import get_current_user


@pytest.mark.asyncio
async def test_get_current_user_missing_header() -> None:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "client": ("127.0.0.1", 1234),
    }
    request = Request(scope)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(request)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_with_headers() -> None:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [
            (b"x-user-id", b"user_abc"),
            (b"x-user-email", b"e@example.com"),
            (b"x-org-id", b"org_xyz"),
            (b"x-user-roles", b"admin, viewer"),
        ],
        "client": ("127.0.0.1", 1234),
    }
    request = Request(scope)
    ctx = await get_current_user(request)
    assert ctx.user_id == "user_abc"
    assert ctx.email == "e@example.com"
    assert ctx.org_id == "org_xyz"
    assert ctx.roles == ["admin", "viewer"]
    assert getattr(request.state, "user_context", None) is ctx
