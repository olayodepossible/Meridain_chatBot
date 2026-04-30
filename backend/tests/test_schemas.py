"""Tests for Pydantic request/response models."""

import pytest
from pydantic import ValidationError

from app.schemas import ChatRequest, MCPToolDefinition, ToolExecutionResult, UserContext


def test_user_context_defaults() -> None:
    user = UserContext(user_id="u1")
    assert user.email is None
    assert user.org_id is None
    assert user.roles == []
    assert user.raw_claims == {}


def test_user_context_full() -> None:
    user = UserContext(
        user_id="u1",
        email="a@b.com",
        org_id="o1",
        roles=["r1"],
        raw_claims={"k": 1},
    )
    assert user.user_id == "u1"
    assert user.email == "a@b.com"


def test_chat_request_valid() -> None:
    req = ChatRequest(message="hello")
    assert req.message == "hello"
    assert req.conversation_id is None
    assert req.metadata == {}


def test_chat_request_empty_message_rejected() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_request_metadata() -> None:
    req = ChatRequest(message="x", conversation_id="cid", metadata={"a": 1})
    assert req.metadata == {"a": 1}


def test_mcp_tool_definition() -> None:
    t = MCPToolDefinition(
        name="n",
        description="d",
        input_schema={"type": "object", "properties": {"x": {"type": "string"}}},
    )
    dumped = t.model_dump(mode="json")
    assert dumped["name"] == "n"


def test_tool_execution_result() -> None:
    r = ToolExecutionResult(tool_name="t", result={"ok": True})
    assert r.tool_name == "t"
