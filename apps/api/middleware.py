"""
Observability middleware for the CadOwl API.

Adds:
- Request ID generation + propagation (X-Request-ID header)
- Structured logging with request context
- Request timing
- Prometheus /metrics endpoint scaffolding

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Request-scoped context variables (accessible from anywhere in the request)
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="-")


class RequestIDFilter(logging.Filter):
    """Inject request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        record.user_id = user_id_ctx.get()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with structured format + request ID."""
    handler = logging.StreamHandler()
    handler.addFilter(RequestIDFilter())
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s [req=%(request_id)s user=%(user_id)s] %(name)s - %(message)s",
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Quiet down noisy loggers
    for noisy in ("httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Generate/propagate X-Request-ID and time every request."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Use incoming X-Request-ID or generate fresh one
        rid = request.headers.get("x-request-id", str(uuid.uuid4()))
        request_id_ctx.set(rid)

        # Stash on request.state for handlers that want it
        request.state.request_id = rid

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logging.getLogger("api.request").exception(
                "request.failed",
                extra={"method": request.method, "path": request.url.path, "duration_ms": round(duration_ms, 2)},
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = rid

        logging.getLogger("api.request").info(
            "request.completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response


def install_middleware(app: FastAPI, *, log_level: str = "INFO") -> None:
    """One-shot wiring helper."""
    configure_logging(level=log_level)
    app.add_middleware(RequestContextMiddleware)


# ─── Prometheus metrics endpoint (scaffold) ────────────────────────────


def install_metrics_endpoint(app: FastAPI) -> None:
    """Mount /metrics for Prometheus scraping.

    Uses prometheus_client if available; otherwise returns a placeholder.
    """
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        @app.get("/metrics", include_in_schema=False)
        async def metrics() -> Response:
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except ImportError:

        @app.get("/metrics", include_in_schema=False)
        async def metrics_placeholder() -> dict:
            return {"status": "prometheus_client not installed"}
