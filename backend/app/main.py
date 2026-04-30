import json
import logging
from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.logging_config import configure_logging, logging_boundary_middleware
from app.mcp_client import MCPToolClient
from app.orchestrator import AIOrchestrator
from app.rate_limit import enforce_rate_limit
from app.schemas import (
    ChatRequest,
    UserContext,
)

logger = logging.getLogger("api_gateway")


@lru_cache
def get_mcp_client() -> MCPToolClient:
    return MCPToolClient(get_settings())


@lru_cache
def get_orchestrator() -> AIOrchestrator:
    settings = get_settings()
    return AIOrchestrator(settings, get_mcp_client())


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="API Gateway and AI Orchestrator for MCP-only backend tool execution.",
    )
    app.middleware("http")(logging_boundary_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/tools")
    async def list_tools(
        user: Annotated[UserContext, Depends(enforce_rate_limit)],
    ) -> dict[str, Any]:
        tools = await get_mcp_client().list_tools()
        return {
            "user_id": user.user_id,
            "tools": [tool.model_dump(mode="json") for tool in tools],
        }

    @app.post("/api/chat")
    async def chat(
        payload: ChatRequest,
        request: Request,
        user: Annotated[UserContext, Depends(enforce_rate_limit)],
    ) -> StreamingResponse:
        try:
            orchestrator = get_orchestrator()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

        async def event_stream():
            try:
                async for event in orchestrator.stream_response(
                    payload.message,
                    user,
                    payload.conversation_id,
                ):
                    yield _sse(event)
            except Exception as exc:
                logger.exception(
                    "Chat orchestration failed",
                    extra={
                        "request_id": getattr(request.state, "request_id", None),
                        "path": request.url.path,
                        "method": request.method,
                        "status_code": 500,
                        "duration_ms": 0,
                    },
                )
                yield _sse({"type": "error", "message": "The assistant could not complete the request."})

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "cache-control": "no-cache",
                "x-accel-buffering": "no",
            },
        )

    return app


def _sse(event: dict[str, Any]) -> str:
    event_type = event.get("type", "message")
    return f"event: {event_type}\ndata: {json.dumps(event, default=str)}\n\n"


app = create_app()
