"""
Auth enforcement tests.

These run with DEV_MODE explicitly DISABLED to verify the auth layer
actually rejects unauthenticated requests in production mode.
"""

import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def prod_app(monkeypatch):
    """Build a fresh FastAPI app with DEV_MODE off so auth is enforced."""
    monkeypatch.setenv("CADOWL_DEV_MODE", "false")

    # Reload auth + downstream modules so they pick up the new env var
    import apps.api.auth
    import apps.api.auth_deps
    import apps.api.infrastructure_routes
    import apps.api.lifecycle_routes
    import apps.api.main

    importlib.reload(apps.api.auth)
    importlib.reload(apps.api.auth_deps)
    importlib.reload(apps.api.infrastructure_routes)
    importlib.reload(apps.api.lifecycle_routes)
    importlib.reload(apps.api.main)

    yield apps.api.main.app

    # Restore dev mode so other tests still pass
    monkeypatch.setenv("CADOWL_DEV_MODE", "true")
    importlib.reload(apps.api.auth)
    importlib.reload(apps.api.auth_deps)
    importlib.reload(apps.api.infrastructure_routes)
    importlib.reload(apps.api.lifecycle_routes)
    importlib.reload(apps.api.main)


def test_health_is_anonymous(prod_app):
    """Health check must work without auth (k8s probes need it)."""
    client = TestClient(prod_app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_metrics_is_anonymous(prod_app):
    """Metrics endpoint must work without auth (Prometheus scrapes it)."""
    client = TestClient(prod_app)
    response = client.get("/metrics")
    assert response.status_code == 200


def test_projects_list_requires_auth(prod_app):
    """Unauthenticated GET /projects must return 401."""
    client = TestClient(prod_app)
    response = client.get("/api/v1/projects")
    assert response.status_code == 401


def test_create_project_requires_auth(prod_app):
    """Unauthenticated POST /projects must return 401."""
    client = TestClient(prod_app)
    response = client.post("/api/v1/projects", json={"name": "X", "code": "X"})
    assert response.status_code == 401


def test_devices_list_requires_auth(prod_app):
    client = TestClient(prod_app)
    response = client.get("/api/v1/devices")
    assert response.status_code == 401


def test_import_batch_requires_auth(prod_app):
    client = TestClient(prod_app)
    response = client.post(
        "/api/v1/import/batch",
        json={"source_file_name": "x", "source_file_hash": "y", "mode": "manual", "records": []},
        headers={"Idempotency-Key": "abc"},
    )
    assert response.status_code == 401


def test_rollback_requires_auth(prod_app):
    client = TestClient(prod_app)
    response = client.post("/api/v1/revisions/rollback", json={"snapshot_id": "abc"})
    assert response.status_code == 401


def test_lifecycle_sites_requires_auth(prod_app):
    client = TestClient(prod_app)
    response = client.get("/api/v1/lifecycle/sites")
    assert response.status_code == 401


def test_lifecycle_designs_requires_auth(prod_app):
    client = TestClient(prod_app)
    response = client.get("/api/v1/lifecycle/designs")
    assert response.status_code == 401
