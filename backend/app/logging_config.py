import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from pythonjsonlogger import jsonlogger

from app.config import Settings


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(path)s %(method)s %(status_code)s %(duration_ms)s"
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())


async def logging_boundary_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    logger = logging.getLogger("api_gateway")
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "Unhandled request error",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": 500,
                "duration_ms": duration_ms,
            },
        )
        raise

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    response.headers["x-request-id"] = request_id
    logger.info(
        "Request completed",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response
