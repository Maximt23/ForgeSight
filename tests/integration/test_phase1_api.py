import importlib
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient


def build_client(tmp_path):
    os.environ["CADOWL_JSONDB_DIR"] = str(tmp_path / "jsondb")

    import apps.api.store as store_module
    import apps.api.main as main_module

    importlib.reload(store_module)
    importlib.reload(main_module)

    return TestClient(main_module.app), Path(os.environ["CADOWL_JSONDB_DIR"])


def test_health(tmp_path):
    client, _ = build_client(tmp_path)
    r = client.get('/api/v1/health')
    assert r.status_code == 200
    body = r.json()
    assert body['status'] == 'ok'


def test_core_entity_flow_with_events_and_json_persistence(tmp_path):
    client, jsondb_path = build_client(tmp_path)

    project = client.post('/api/v1/projects', json={'name': 'Program Alpha', 'code': 'PA-001'}).json()
    site = client.post(
        '/api/v1/sites',
        json={'project_id': project['id'], 'site_number': '0041', 'name': 'Bartlesville'},
    ).json()
    floor = client.post('/api/v1/floors', json={'site_id': site['id'], 'name': 'Main', 'level': 1}).json()
    map_obj = client.post('/api/v1/maps', json={'floor_id': floor['id'], 'name': 'FP-1', 'source_type': 'dxf'}).json()

    device_a = client.post(
        '/api/v1/devices',
        json={
            'project_id': project['id'],
            'site_number': '0041',
            'floor_id': floor['id'],
            'map_id': map_obj['id'],
            'device_type': 'camera',
            'name': 'CAM-01',
            'local_x': 10.2,
            'local_y': 8.4,
        },
    ).json()
    device_b = client.post(
        '/api/v1/devices',
        json={
            'project_id': project['id'],
            'site_number': '0041',
            'floor_id': floor['id'],
            'map_id': map_obj['id'],
            'device_type': 'switch',
            'name': 'SW-01',
            'local_x': 15.0,
            'local_y': 9.1,
        },
    ).json()

    zone = client.post(
        '/api/v1/zones',
        json={'project_id': project['id'], 'floor_id': floor['id'], 'zone_name': 'Front End', 'zone_type': 'Sales Floor'},
    ).json()

    cable = client.post(
        '/api/v1/cables',
        json={
            'project_id': project['id'],
            'site_number': '0041',
            'source_device_id': device_a['id'],
            'destination_device_id': device_b['id'],
            'cable_type': 'CAT6',
        },
    ).json()

    assert zone['zone_name'] == 'Front End'
    assert cable['cable_type'] == 'CAT6'

    filtered_devices = client.get(f"/api/v1/devices?project_id={project['id']}&site_number=0041").json()
    assert len(filtered_devices) == 2

    events = client.get('/api/v1/events').json()
    assert len(events) >= 8
    assert any(e['entity_type'] == 'project' for e in events)
    assert any(e['entity_type'] == 'cable' for e in events)

    # Verify JSON persistence files were written
    expected_files = [
        "projects.json", "sites.json", "floors.json", "maps.json",
        "devices.json", "zones.json", "cables.json", "events.json",
    ]
    for name in expected_files:
        file_path = jsondb_path / name
        assert file_path.exists()
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        assert isinstance(payload, list)

    projects_rows = json.loads((jsondb_path / "projects.json").read_text(encoding="utf-8"))
    assert len(projects_rows) == 1
