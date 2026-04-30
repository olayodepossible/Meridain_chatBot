"""Tests for logging configuration and request middleware."""

import logging

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.logging_config import configure_logging, logging_boundary_middleware


def test_configure_logging_sets_level() -> None:
    configure_logging(Settings(log_level="WARNING"))
    root = logging.getLogger()
    assert root.level == logging.WARNING


@pytest.mark.asyncio
async def test_logging_middleware_adds_request_id() -> None:
    app = FastAPI()

    @app.get("/x")
    async def x() -> dict[str, bool]:
        return {"ok": True}

    app.middleware("http")(logging_boundary_middleware)
    configure_logging(Settings(log_level="CRITICAL"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/x")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
