"""Tests for AI orchestrator static logic and streaming with mocks."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings
from app.orchestrator import AIOrchestrator
from app.schemas import MCPToolDefinition, UserContext


def test_orchestrator_init_requires_api_key() -> None:
    settings = Settings(openai_api_key="")
    mock_mcp = MagicMock()
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        AIOrchestrator(settings, mock_mcp)


def test_parse_tool_arguments_empty() -> None:
    assert AIOrchestrator._parse_tool_arguments(None) == {}
    assert AIOrchestrator._parse_tool_arguments("") == {}


def test_parse_tool_arguments_valid_json() -> None:
    assert AIOrchestrator._parse_tool_arguments('{"a": 1}') == {"a": 1}


def test_parse_tool_arguments_invalid_json_returns_empty() -> None:
    assert AIOrchestrator._parse_tool_arguments("not-json") == {}


def test_parse_tool_arguments_non_object_raises() -> None:
    with pytest.raises(ValueError):
        AIOrchestrator._parse_tool_arguments("[1,2]")


def test_safe_user_context() -> None:
    u = UserContext(user_id="u", email="e", org_id="o", roles=["r"])
    d = AIOrchestrator._safe_user_context(u)
    assert d == {"user_id": "u", "email": "e", "org_id": "o", "roles": ["r"]}


def test_to_openai_tool_coerces_non_object_schema() -> None:
    tool = MCPToolDefinition(name="t", description="d", input_schema={"type": "string"})
    spec = AIOrchestrator._to_openai_tool(tool)
    assert spec["type"] == "function"
    assert spec["function"]["name"] == "t"
    assert spec["function"]["parameters"]["type"] == "object"


def test_to_openai_tool_preserves_object_schema() -> None:
    schema = {"type": "object", "properties": {"sku": {"type": "string"}}, "required": ["sku"]}
    tool = MCPToolDefinition(name="get_product", description="", input_schema=schema)
    spec = AIOrchestrator._to_openai_tool(tool)
    assert spec["function"]["parameters"] == schema


def test_system_prompt_lists_tools() -> None:
    tools = [
        MCPToolDefinition(name="a", description="da", input_schema={"type": "object"}),
    ]
    prompt = AIOrchestrator._system_prompt(tools)
    assert "a" in prompt
    assert "da" in prompt


def test_system_prompt_empty_tools() -> None:
    prompt = AIOrchestrator._system_prompt([])
    assert "No tools" in prompt or "expose" in prompt.lower()


@pytest.mark.asyncio
async def test_stream_response_text_only_no_tools() -> None:
    settings = Settings(openai_api_key="sk-test")
    mock_mcp = MagicMock()
    mock_mcp.list_tools = AsyncMock(return_value=[])

    mock_message = SimpleNamespace(content="Hello user", tool_calls=None)
    mock_choice = SimpleNamespace(message=mock_message)
    mock_resp = SimpleNamespace(choices=[mock_choice])

    mock_llm = MagicMock()
    mock_llm.chat = MagicMock()
    mock_llm.chat.completions = MagicMock()
    mock_llm.chat.completions.create = AsyncMock(return_value=mock_resp)

    orch = AIOrchestrator.__new__(AIOrchestrator)
    orch._settings = settings
    orch._mcp_client = mock_mcp
    orch._llm = mock_llm

    user = UserContext(user_id="u1")
    events: list[dict[str, Any]] = []
    async for ev in orch.stream_response("hi", user):
        events.append(ev)

    assert events[0]["type"] == "status"
    assert any(e["type"] == "message.delta" and e["content"] == "Hello user" for e in events)
    assert events[-1]["type"] == "message.done"


@pytest.mark.asyncio
async def test_stream_response_with_tool_call() -> None:
    settings = Settings(openai_api_key="sk-test", max_tool_steps=2)
    tools = [
        MCPToolDefinition(
            name="get_product",
            description="d",
            input_schema={"type": "object", "properties": {"sku": {"type": "string"}}},
        )
    ]
    mock_mcp = MagicMock()
    mock_mcp.list_tools = AsyncMock(return_value=tools)
    mock_mcp.execute_tool = AsyncMock(return_value={"error": False, "content": "ok"})

    tc = MagicMock()
    tc.id = "call_1"
    tc.function = SimpleNamespace(name="get_product", arguments='{"sku":"x"}')
    tc.model_dump.return_value = {
        "id": "call_1",
        "type": "function",
        "function": {"name": "get_product", "arguments": '{"sku":"x"}'},
    }
    assistant_with_tools = SimpleNamespace(content=None, tool_calls=[tc])
    assistant_final = SimpleNamespace(content="Done.", tool_calls=None)

    mock_llm = MagicMock()
    mock_llm.chat = MagicMock()
    mock_llm.chat.completions = MagicMock()
    mock_llm.chat.completions.create = AsyncMock(
        side_effect=[
            SimpleNamespace(choices=[SimpleNamespace(message=assistant_with_tools)]),
            SimpleNamespace(choices=[SimpleNamespace(message=assistant_final)]),
        ]
    )

    orch = AIOrchestrator.__new__(AIOrchestrator)
    orch._settings = settings
    orch._mcp_client = mock_mcp
    orch._llm = mock_llm

    user = UserContext(user_id="u1")
    events: list[dict[str, Any]] = []
    async for ev in orch.stream_response("stock?", user):
        events.append(ev)

    types = [e["type"] for e in events]
    assert "tool.started" in types
    assert "tool.completed" in types
    mock_mcp.execute_tool.assert_awaited_once_with("get_product", {"sku": "x"}, user)
