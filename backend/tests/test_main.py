"""Tests for FastAPI app routes and helpers."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

import app.main as main_module
from app.main import _sse, app, create_app
from app.schemas import MCPToolDefinition, UserContext


@pytest.fixture(autouse=True)
def clear_main_caches() -> None:
    main_module.get_mcp_client.cache_clear()
    main_module.get_orchestrator.cache_clear()
    yield
    main_module.get_mcp_client.cache_clear()
    main_module.get_orchestrator.cache_clear()


@pytest.mark.asyncio
async def test_health() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_api_tools_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/tools")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_api_tools_returns_tools(monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    mock_client = MagicMock()
    mock_client.list_tools = AsyncMock(
        return_value=[
            MCPToolDefinition(name="t1", description="d1", input_schema={"type": "object"}),
        ]
    )
    monkeypatch.setattr(main_module, "get_mcp_client", lambda: mock_client)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/tools", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == "user_test_123"
    assert len(body["tools"]) == 1
    assert body["tools"][0]["name"] == "t1"


@pytest.mark.asyncio
async def test_api_chat_sse(monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]) -> None:
    class MockOrch:
        async def stream_response(
            self,
            message: str,
            user: UserContext,
            conversation_id: str | None = None,
        ):
            yield {"type": "status", "message": "started"}
            yield {"type": "message.delta", "content": "hello"}
            yield {"type": "message.done"}

    monkeypatch.setattr(main_module, "get_orchestrator", lambda: MockOrch())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/chat",
            headers={**auth_headers, "accept": "text/event-stream"},
            json={"message": "ping"},
        )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    text = r.text
    assert "event: status" in text
    assert "event: message.delta" in text
    assert "event: message.done" in text


@pytest.mark.asyncio
async def test_api_chat_missing_openai_key_returns_500(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    def boom() -> None:
        raise ValueError("OPENAI_API_KEY must be configured.")

    monkeypatch.setattr(main_module, "get_orchestrator", boom)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/chat", headers=auth_headers, json={"message": "x"})
    assert r.status_code == 500


def test_sse_format_and_newline_escape() -> None:
    payload = {"type": "t", "line": "a\nb"}
    out = _sse(payload)
    assert out.startswith("event: t\n")
    assert "data:" in out
    parsed_line = out.split("data: ", 1)[1].split("\n", 1)[0]
    data = json.loads(parsed_line)
    assert data["line"] == "a\nb"


def test_create_app_returns_fastapi_instance() -> None:
    a = create_app()
    assert a.title
    routes = {r.path for r in a.routes}
    assert "/health" in routes
