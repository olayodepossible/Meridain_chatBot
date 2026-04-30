# Tool-Augmented AI Backend

FastAPI backend for an API Gateway + AI Orchestrator + MCP tool layer.

## Architecture

```text
User -> Next.js UI
     -> API Gateway
        - Frontend-authenticated Clerk user context headers
        - Rate limiting
        - Structured logging
        - Security boundary
     -> AI Orchestrator
        - Attaches Clerk user context
        - Calls the LLM
        - Runs a bounded MCP tool execution loop
     -> External MCP Server over Streamable HTTP
        - Tool registry
        - Only execution path to backend systems
```

The LLM never calls internal services directly. Product availability, order placement,
order history, and customer support actions must be exposed as MCP tools by:

```text
https://order-mcp-74afyau24q-uc.a.run.app/mcp
```

## Setup

```bash
cd backend
uv sync
copy .env.example .env
```

Set `OPENAI_API_KEY` in `.env`.

Clerk authentication is handled by the frontend. Backend protected endpoints expect
the frontend to pass the authenticated user context with:

```text
x-user-id: Clerk user id
x-user-email: Clerk primary email address
x-org-id: Optional Clerk organization id
x-user-roles: Optional comma-separated roles
```

## Run

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Or use the local runner:

```bash
uv run python run.py
```

## API

- `GET /health` returns service health.
- `GET /api/tools` lists tools discovered from the MCP server.
- `POST /api/chat` accepts a user query and streams Server-Sent Events.

Example chat request:

```json
{
  "message": "Is product SKU-123 available and can you place an order?",
  "conversation_id": "optional-client-thread-id"
}
```

`/api/chat` requires `x-user-id`.
