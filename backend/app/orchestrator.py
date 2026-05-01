import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.config import Settings
from app.conversation_memory import ConversationMemory
from app.mcp_client import MCPToolClient
from app.schemas import MCPToolDefinition, UserContext
from app.context import prompt

logger = logging.getLogger("ai_orchestrator")


class AIOrchestrator:
    """Core brain: plans with the LLM and executes actions only through MCP tools."""

    def __init__(self, settings: Settings, mcp_client: MCPToolClient) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be configured.")
        self._settings = settings
        self._mcp_client = mcp_client
        self._memory = ConversationMemory(settings)
        self._llm = AsyncOpenAI(api_key=settings.openai_api_key, base_url="https://openrouter.ai/api/v1")

    async def stream_response(
        self,
        user_query: str,
        user_context: UserContext,
        conversation_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        tools = await self._mcp_client.list_tools()
        tool_names = {tool.name for tool in tools}
        # STEP 1: Fetch conversation history (from memory store / S3 / DB)
        history = await self._get_conversation_history(conversation_id)

        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": prompt() + "\n\n" + self._system_prompt(tools),
            },
        ]

        # STEP 2: Inject past conversation (VERY IMPORTANT)
        for msg in history:
            messages.append(msg)

        # STEP 3: Add current user input LAST
        messages.append(
            {
                "role": "user",
                "content": user_query
            }
        )

        yield {"type": "status", "message": "orchestrator_started"}

        for step in range(self._settings.max_tool_steps):
            completion_args: dict[str, Any] = {
                "model": self._settings.openai_model,
                "messages": messages,
            }
            if tools:
                completion_args["tools"] = [self._to_openai_tool(tool) for tool in tools]
                completion_args["tool_choice"] = "auto"

            response = await self._llm.chat.completions.create(**completion_args)
            assistant_message = response.choices[0].message
            tool_calls = assistant_message.tool_calls or []

            if not tool_calls:
                content = assistant_message.content or ""
                if content:
                    yield {"type": "message.delta", "content": content}
                yield {"type": "message.done"}
                await self._persist_full_conversation(conversation_id, messages)
                return

            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [tc.model_dump(exclude_none=True) for tc in tool_calls],
                }
            )

            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                if tool_name not in tool_names:
                    result = {"error": True, "message": f"Unknown MCP tool: {tool_name}"}
                else:
                    arguments = self._parse_tool_arguments(tool_call.function.arguments)
                    logger.info(
                        "Executing MCP tool",
                        extra={
                            "request_id": None,
                            "path": "mcp_tool",
                            "method": tool_name,
                            "status_code": 0,
                            "duration_ms": 0,
                        },
                    )
                    yield {"type": "tool.started", "tool_name": tool_name, "step": step + 1}
                    result = await self._mcp_client.execute_tool(tool_name, arguments, user_context)
                    yield {"type": "tool.completed", "tool_name": tool_name, "step": step + 1}

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": json.dumps(result, default=str),
                    }
                )

        messages.append(
            {
                "role": "system",
                "content": (
                    "The maximum tool execution depth was reached. Summarize what is known "
                    "and ask for the minimum next clarification if needed."
                ),
            }
        )
        final_response = await self._llm.chat.completions.create(
            model=self._settings.openai_model,
            messages=messages,
        )
        final_content = final_response.choices[0].message.content or ""
        yield {"type": "message.delta", "content": final_content}
        yield {"type": "message.done"}
        await self._persist_conversation_turn(conversation_id, user_query, final_content)

    @staticmethod
    def _parse_tool_arguments(arguments: str | None) -> dict[str, Any]:
        if not arguments:
            return {}
        try:
            parsed = json.loads(arguments)
            if not isinstance(parsed, dict):
                raise ValueError("Tool arguments must be a JSON object.")
            return parsed
        except json.JSONDecodeError:
            logger.warning("Failed to parse tool arguments", extra={"arguments": arguments})
            return {}

    @staticmethod
    def _safe_user_context(user_context: UserContext) -> dict[str, Any]:
        return {
            "user_id": user_context.user_id,
            "email": user_context.email,
            "org_id": user_context.org_id,
            "roles": user_context.roles,
        }

    @staticmethod
    def _to_openai_tool(tool: MCPToolDefinition) -> dict[str, Any]:
        parameters = tool.input_schema
        if parameters.get("type") != "object":
            parameters = {"type": "object", "properties": {}, "additionalProperties": True}

        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or f"Execute the {tool.name} MCP tool.",
                "parameters": parameters,
            },
        }

    @staticmethod
    def _system_prompt(tools: list[MCPToolDefinition]) -> str:
        tool_list = "\n".join(f"- {tool.name}: {tool.description}" for tool in tools)
        return f"""
You are the AI Orchestrator Service for a commerce support assistant.

Security and architecture rules:
- You may answer general questions directly.
- For product availability lookup, order placement, order history retrieval, and customer-authenticated support actions, you must use MCP tools.
- Never claim to access databases, internal services, product services, order services, or customer systems directly.
- Never ask the user for raw JWTs, API keys, passwords, or secrets.
- Use the provided frontend-authenticated user context for customer identity.
- If a required backend action is not represented by an MCP tool, explain that the tool layer does not expose that action.

Reasoning rules:
- Choose the smallest tool call that can answer the request.
- For multi-step tasks, call tools sequentially and use previous tool results to decide the next tool.
- After tool execution, format a concise, user-friendly final response.

Available MCP tools:
{tool_list or "- No tools are currently exposed by the MCP server."}
""".strip()

    async def _get_conversation_history(
        self, conversation_id: str | None
    ) -> list[dict[str, Any]]:
        """Load prior user/assistant turns (S3 when USE_S3+S3_BUCKET, else local `.memory`)."""
        if not conversation_id:
            return []
        try:
            return await self._memory.load(conversation_id)
        except Exception as e:
            logger.warning("Failed to load conversation history", extra={"error": str(e)})
            return []

    async def _persist_conversation_turn(
        self,
        conversation_id: str | None,
        user_query: str,
        assistant_text: str,
    ) -> None:
        if not conversation_id or not assistant_text.strip():
            return
        try:
            await self._memory.append(conversation_id, user_query, assistant_text)
        except Exception as e:
            logger.warning("Failed to persist conversation turn", extra={"error": str(e)})

async def _persist_full_conversation(
    self,
    conversation_id: str | None,
    messages: list[dict[str, Any]],
) -> None:
    if not conversation_id:
        return

    try:
        # Only store user + assistant (filter out tool noise)
        cleaned = [
            {"role": m["role"], "content": m.get("content", "")}
            for m in messages
            if m["role"] in ("user", "assistant") and m.get("content")
        ]

        await self._memory.overwrite(conversation_id, cleaned)

    except Exception as e:
        logger.warning("Failed to persist full conversation", extra={"error": str(e)})