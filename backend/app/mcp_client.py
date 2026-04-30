import time
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.config import Settings
from app.schemas import MCPToolDefinition, UserContext


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


class MCPToolClient:
    """Registry and execution layer for the external order MCP server."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cached_tools: list[MCPToolDefinition] | None = None
        self._cached_at = 0.0

    def _headers_for_user(self, user_context: UserContext | None = None) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._settings.mcp_server_auth_token:
            headers["authorization"] = f"Bearer {self._settings.mcp_server_auth_token}"
        if user_context:
            headers["x-user-id"] = user_context.user_id
            if user_context.email:
                headers["x-user-email"] = user_context.email
            if user_context.org_id:
                headers["x-org-id"] = user_context.org_id
        return headers

    def _session(self, user_context: UserContext | None = None):
        return streamablehttp_client(
            str(self._settings.mcp_server_url),
            headers=self._headers_for_user(user_context),
        )

    async def list_tools(self) -> list[MCPToolDefinition]:
        now = time.monotonic()
        if (
            self._cached_tools is not None
            and now - self._cached_at < self._settings.mcp_tool_cache_seconds
        ):
            return self._cached_tools

        async with self._session() as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tool_response = await session.list_tools()

        tools: list[MCPToolDefinition] = []
        for tool in tool_response.tools:
            input_schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None)
            tools.append(
                MCPToolDefinition(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=_jsonable(input_schema) or {"type": "object", "properties": {}},
                )
            )

        self._cached_tools = tools
        self._cached_at = now
        return tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user_context: UserContext,
    ) -> Any:
        async with self._session(user_context) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)

        if getattr(result, "isError", False):
            return {
                "error": True,
                "tool_name": tool_name,
                "content": _jsonable(result.content),
            }

        return {
            "error": False,
            "tool_name": tool_name,
            "content": _jsonable(result.content),
        }
