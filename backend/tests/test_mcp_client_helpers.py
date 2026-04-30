"""Tests for MCP client JSON normalization and header building."""

from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.mcp_client import MCPToolClient, _jsonable
from app.schemas import UserContext


def test_jsonable_dict_list_primitive() -> None:
    assert _jsonable({"a": 1}) == {"a": 1}
    assert _jsonable([1, "b"]) == [1, "b"]
    assert _jsonable(42) == 42


def test_jsonable_pydantic_like() -> None:
    m = MagicMock()
    m.model_dump.return_value = {"type": "object", "x": 1}
    assert _jsonable(m) == {"type": "object", "x": 1}


def test_headers_for_user_with_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_SERVER_AUTH_TOKEN", "secret-token")
    s = Settings()
    client = MCPToolClient(s)
    user = UserContext(user_id="u1", email="e@x.com", org_id="o1")
    h = client._headers_for_user(user)
    assert h["authorization"] == "Bearer secret-token"
    assert h["x-user-id"] == "u1"
    assert h["x-user-email"] == "e@x.com"
    assert h["x-org-id"] == "o1"


def test_headers_for_user_no_token_no_user() -> None:
    s = Settings()
    client = MCPToolClient(s)
    assert client._headers_for_user(None) == {}
