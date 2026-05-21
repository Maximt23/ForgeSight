from __future__ import annotations

import os

from fastapi.testclient import TestClient

os.environ["CADOWL_DEV_MODE"] = "true"

from apps.api.main import app  # noqa: E402


def test_forgesearch_routes_registered() -> None:
    paths = {r.path for r in app.routes}
    assert "/api/forgesearch/classify" in paths
    assert "/api/forgesearch/execute" in paths


def test_forgesearch_classify_and_execute() -> None:
    client = TestClient(app)

    classify = client.post("/api/forgesearch/classify", json={"input": "validate this design"})
    assert classify.status_code == 200
    assert classify.json()["intent"] == "validate"

    execute = client.post("/api/forgesearch/execute", json={"intent": "query", "results": []})
    assert execute.status_code == 200
    body = execute.json()
    assert body["status"] == "accepted"
    assert body["intent"] == "query"
