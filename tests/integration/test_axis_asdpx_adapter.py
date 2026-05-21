import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.adapters.axis_siteowl_adapter import convert_asdpx_to_siteowl_rows

SAMPLE_ASDPX = Path(r"C:\MAXILLM\cadowl\data\sample-imports\siteowl_workflow_v2\Sample_2996.asdpx")


def build_client(tmp_path):
    os.environ["CADOWL_JSONDB_DIR"] = str(tmp_path / "jsondb")
    os.environ["CADOWL_SCHEMA_DIR"] = str(Path("C:/MAXILLM/cadowl/apps/api/schemas_json"))

    import apps.api.store as store_module
    import apps.api.main as main_module

    importlib.reload(store_module)
    importlib.reload(main_module)

    return TestClient(main_module.app)


def test_asdpx_conversion_rows():
    assert SAMPLE_ASDPX.exists()
    rows, meta = convert_asdpx_to_siteowl_rows(SAMPLE_ASDPX)
    assert meta["row_count"] > 0
    assert len(rows) == meta["row_count"]

    sample = rows[0]
    assert sample["System Type"] == "Video Surveillance"
    assert sample["Coordinates"].startswith('"(')
    assert "," in sample["Field Notes"]


def test_asdpx_preview_endpoint(tmp_path):
    client = build_client(tmp_path)
    r = client.post("/api/v1/import/asdpx/preview", json={"source_path": str(SAMPLE_ASDPX)})
    assert r.status_code == 200
    body = r.json()
    assert body["row_count"] > 0
    assert len(body["sample_rows"]) > 0


def test_asdpx_stage_and_commit_flow(tmp_path):
    client = build_client(tmp_path)

    project = client.post('/api/v1/projects', json={'name': 'Axis Import Program', 'code': 'AX-001'}).json()

    stage = client.post(
        '/api/v1/import/asdpx/batch',
        json={'source_path': str(SAMPLE_ASDPX), 'mode': 'merge'},
        headers={'Idempotency-Key': 'asdpx-stage-1'},
    )
    assert stage.status_code == 200
    stage_body = stage.json()
    assert stage_body['staged_row_count'] > 0
    batch_id = stage_body['batch']['id']

    commit = client.post(
        f'/api/v1/import/{batch_id}/commit',
        json={
            'project_id': project['id'],
            'site_number': '2996',
            'actor': 'integration-test',
        },
    )
    assert commit.status_code == 200
    commit_body = commit.json()
    assert commit_body['status'] == 'committed'
    assert commit_body['committed_devices'] == stage_body['staged_row_count']

    devices = client.get(f"/api/v1/devices?project_id={project['id']}&site_number=2996").json()
    assert len(devices) == stage_body['staged_row_count']

    events = client.get('/api/v1/events').json()
    assert any(e['event_type'] == 'import_batch_staged' for e in events)
    assert any(e['event_type'] == 'import_batch_committed' for e in events)
