"""
Tests for the observability middleware.

Verifies:
  - X-Request-ID is generated when missing
  - X-Request-ID is propagated when supplied
  - Request context variables (request_id, user_id) are populated
  - configure_logging() installs the RequestIDFilter

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import logging
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.middleware import (
    RequestContextMiddleware,
    RequestIDFilter,
    configure_logging,
    install_metrics_endpoint,
    install_middleware,
    request_id_ctx,
)


@pytest.fixture()
def app_with_middleware() -> TestClient:
    """Tiny app with the middleware wired in."""
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ping")
    async def ping() -> dict:
        # Read the request_id from the contextvar inside the handler
        return {"request_id": request_id_ctx.get()}

    return TestClient(app)


def test_request_id_generated_when_missing(app_with_middleware: TestClient) -> None:
    resp = app_with_middleware.get("/ping")
    assert resp.status_code == 200

    rid = resp.headers.get("x-request-id")
    assert rid, "Response should have an X-Request-ID header"
    # Should be a valid UUID
    uuid.UUID(rid)

    # Handler saw the same id
    assert resp.json()["request_id"] == rid


def test_request_id_propagated_when_supplied(app_with_middleware: TestClient) -> None:
    incoming = "test-correlation-id-12345"
    resp = app_with_middleware.get("/ping", headers={"X-Request-ID": incoming})

    assert resp.status_code == 200
    assert resp.headers["x-request-id"] == incoming
    assert resp.json()["request_id"] == incoming


def test_request_id_filter_injects_into_log_records() -> None:
    """The filter should set request_id + user_id on every record."""
    filt = RequestIDFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hi",
        args=(),
        exc_info=None,
    )

    result = filt.filter(record)
    assert result is True
    assert hasattr(record, "request_id")
    assert hasattr(record, "user_id")


def test_configure_logging_installs_filter() -> None:
    """configure_logging should add a handler with the filter."""
    configure_logging(level="DEBUG")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert any(
        any(isinstance(f, RequestIDFilter) for f in h.filters) for h in root.handlers
    )


def test_install_middleware_wires_both() -> None:
    """install_middleware should add the middleware AND configure logging."""
    app = FastAPI()
    install_middleware(app, log_level="WARNING")

    # Middleware stack should include RequestContextMiddleware
    middleware_classes = [m.cls.__name__ for m in app.user_middleware]
    assert "RequestContextMiddleware" in middleware_classes

    # Root logger should be at WARNING
    assert logging.getLogger().level == logging.WARNING


def test_install_metrics_endpoint_mounts_route() -> None:
    """install_metrics_endpoint should mount /metrics."""
    app = FastAPI()
    install_metrics_endpoint(app)

    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    # Either prometheus_client text format OR our placeholder dict
    assert resp.headers["content-type"].startswith(("text/plain", "application/json"))


def test_failing_handler_still_logs_and_reraises(caplog) -> None:
    """When a handler raises, the middleware should log + reraise."""
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/boom")
    async def boom() -> None:
        raise ValueError("intentional test failure")

    client = TestClient(app, raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR, logger="api.request"):
        resp = client.get("/boom")
    assert resp.status_code == 500
    assert any("request.failed" in rec.message for rec in caplog.records)
