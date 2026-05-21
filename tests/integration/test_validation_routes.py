from __future__ import annotations

import importlib
import os
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient


def build_client(tmp_path: Path) -> TestClient:
    os.environ["CADOWL_JSONDB_DIR"] = str(tmp_path / "jsondb")
    os.environ["CADOWL_SCHEMA_DIR"] = str(Path("C:/MAXILLM/cadowl/apps/api/schemas_json"))
    os.environ["CADOWL_DEV_MODE"] = "true"

    import apps.api.store as store_module
    import apps.api.validation_routes as validation_routes_module
    import apps.api.main as main_module

    importlib.reload(store_module)
    importlib.reload(validation_routes_module)
    importlib.reload(main_module)

    return TestClient(main_module.app)


def seed_project_graph(client: TestClient):
    project = client.post("/api/v1/projects", json={"name": "Validation Project", "code": "VAL-01"}).json()
    site = client.post(
        "/api/v1/sites",
        json={"project_id": project["id"], "site_number": "0042", "name": "Tulsa"},
    ).json()
    floor = client.post(
        "/api/v1/floors",
        json={"site_id": site["id"], "name": "Main", "level": 1},
    ).json()
    map_obj = client.post(
        "/api/v1/maps",
        json={"floor_id": floor["id"], "name": "FP-VAL", "source_type": "dxf"},
    ).json()
    return project, site, floor, map_obj


def test_validation_routes_registered(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    paths = {r.path for r in client.app.routes}
    assert "/api/v1/validation/run" in paths
    assert "/api/v1/validation/autofix/preview" in paths


def test_validation_run_returns_findings_and_writes_event(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    project, site, floor, map_obj = seed_project_graph(client)

    # Two devices at same coordinates => duplicate finding.
    device_payload = {
        "project_id": project["id"],
        "site_number": site["site_number"],
        "floor_id": floor["id"],
        "map_id": map_obj["id"],
        "device_type": "camera",
        "local_x": 10,
        "local_y": 20,
    }
    d1 = client.post("/api/v1/devices", json={**device_payload, "name": "CAM-A"}).json()
    d2 = client.post("/api/v1/devices", json={**device_payload, "name": "CAM-B"}).json()

    # Cable to a non-existent destination => critical cable finding.
    cable = {
        "project_id": project["id"],
        "site_number": site["site_number"],
        "source_device_id": d1["id"],
        "destination_device_id": str(uuid4()),
        "cable_type": "cat6",
        "path_points": [],
    }
    c_resp = client.post("/api/v1/cables", json=cable)
    assert c_resp.status_code == 200

    events_before = len(client.get("/api/v1/events").json())
    run = client.post("/api/v1/validation/run", json={"project_id": project["id"]})
    assert run.status_code == 200
    body = run.json()

    assert body["validation_score"] < 100
    assert len(body["findings"]) >= 2
    assert any(f["category"] == "duplicate" for f in body["findings"])
    assert any(f["category"] == "cable" for f in body["findings"])

    events_after = len(client.get("/api/v1/events").json())
    assert events_after == events_before + 1


def test_validation_run_honors_project_filter(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    project_a, site_a, floor_a, map_a = seed_project_graph(client)
    project_b = client.post("/api/v1/projects", json={"name": "Other", "code": "VAL-02"}).json()

    client.post(
        "/api/v1/devices",
        json={
            "project_id": project_a["id"],
            "site_number": site_a["site_number"],
            "floor_id": floor_a["id"],
            "map_id": map_a["id"],
            "device_type": "camera",
            "name": "A-CAM-1",
            "local_x": 11,
            "local_y": 22,
        },
    )
    client.post(
        "/api/v1/devices",
        json={
            "project_id": project_b["id"],
            "site_number": "9999",
            "device_type": "camera",
            "name": "B-CAM-1",
            "local_x": 11,
            "local_y": 22,
        },
    )
    client.post(
        "/api/v1/devices",
        json={
            "project_id": project_b["id"],
            "site_number": "9999",
            "device_type": "camera",
            "name": "B-CAM-2",
            "local_x": 11,
            "local_y": 22,
        },
    )

    # project B has duplicates; project A does not.
    run_a = client.post("/api/v1/validation/run", json={"project_id": project_a["id"]})
    assert run_a.status_code == 200
    assert not any(f["category"] == "duplicate" for f in run_a.json()["findings"])


def test_autofix_preview_returns_safe_fixes_list(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    project, site, floor, map_obj = seed_project_graph(client)

    # Create one duplicate finding (currently not autofix-eligible in engine).
    payload = {
        "project_id": project["id"],
        "site_number": site["site_number"],
        "floor_id": floor["id"],
        "map_id": map_obj["id"],
        "device_type": "camera",
        "local_x": 5,
        "local_y": 5,
    }
    client.post("/api/v1/devices", json={**payload, "name": "CAM-1"})
    client.post("/api/v1/devices", json={**payload, "name": "CAM-2"})

    resp = client.post("/api/v1/validation/autofix/preview", json={"project_id": project["id"]})
    assert resp.status_code == 200
    body = resp.json()
    assert "safe_fixes" in body
    assert isinstance(body["safe_fixes"], list)
