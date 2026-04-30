from typing import Any

from pydantic import BaseModel, Field


class UserContext(BaseModel):
    user_id: str
    email: str | None = None
    org_id: str | None = None
    roles: list[str] = Field(default_factory=list)
    raw_claims: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    conversation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MCPToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]


class ToolExecutionResult(BaseModel):
    tool_name: str
    result: Any
