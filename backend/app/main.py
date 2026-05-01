import json
import logging
from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from app.config import  get_settings
from app.logging_config import configure_logging, logging_boundary_middleware
from app.mcp_client import MCPToolClient
from app.orchestrator import AIOrchestrator
from app.rate_limit import enforce_rate_limit
from app.schemas import (
    ChatRequest,
    UserContext,
)

import os

logger = logging.getLogger("api_gateway")


def _cors_allow_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return ["http://localhost:3000"]
    return [o.strip() for o in raw.split(",") if o.strip()]


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
        headers={
            "cache-control": "no-cache",
            "x-accel-buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )
    app.middleware("http")(logging_boundary_middleware)
    # Explicit allow_origins from CORS_ORIGINS (Terraform sets the CloudFront HTTPS URL).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_allow_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    @app.options("/api/chat")
    async def _preflight_chat() -> Response:
        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS,HEAD",
                "Access-Control-Allow-Headers": "*",
            },
        )

    @app.options("/api/tools")
    async def _preflight_tools() -> Response:
        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS,HEAD",
                "Access-Control-Allow-Headers": "*",
            },
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/tools")
    async def list_tools(
        user: Annotated[UserContext, Depends(enforce_rate_limit)],
    ) -> dict[str, Any]:
        tools = await get_mcp_client().list_tools()
        for tool in tools:
            logger.info("Tool schema", extra={
                "name": tool.name,
                "schema": tool.input_schema
            })
        return {
            "user_id": user.user_id,
            "tools": [tool.model_dump(mode="json")],
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
                    if await request.is_disconnected():
                        logger.info("Client disconnected early")
                        break

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
                yield _sse({
    "type": "error",
    "message": str(exc)[:300]  # TEMP for debugging
})
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
    data = json.dumps(event, default=str).replace("\n", "\\n")
    return f"event: {event_type}\ndata: {data}\n\n"


app = create_app()
