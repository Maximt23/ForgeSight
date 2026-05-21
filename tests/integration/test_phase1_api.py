import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient


def build_client(tmp_path):
    os.environ["CADOWL_JSONDB_DIR"] = str(tmp_path / "jsondb")
    os.environ["CADOWL_SCHEMA_DIR"] = str(Path("C:/MAXILLM/cadowl/apps/api/schemas_json"))

    import apps.api.store as store_module
    import apps.api.main as main_module

    importlib.reload(store_module)
    importlib.reload(main_module)

    return TestClient(main_module.app), Path(os.environ["CADOWL_JSONDB_DIR"])


def seed_core(client):
    project = client.post('/api/v1/projects', json={'name': 'Program Alpha', 'code': 'PA-001'}).json()
    site = client.post('/api/v1/sites', json={'project_id': project['id'], 'site_number': '0041', 'name': 'Bartlesville'}).json()
    floor = client.post('/api/v1/floors', json={'site_id': site['id'], 'name': 'Main', 'level': 1}).json()
    map_obj = client.post('/api/v1/maps', json={'floor_id': floor['id'], 'name': 'FP-1', 'source_type': 'dxf'}).json()
    return project, site, floor, map_obj


def test_health(tmp_path):
    client, _ = build_client(tmp_path)
    r = client.get('/api/v1/health')
    assert r.status_code == 200
    body = r.json()
    assert body['status'] == 'ok'
    assert body['phase'] == 'perfect-mode-phase-2'


def test_schema_validation_blocks_empty_device_name(tmp_path):
    client, _ = build_client(tmp_path)
    project, _, floor, map_obj = seed_core(client)

    r = client.post(
        '/api/v1/devices',
        json={
            'project_id': project['id'],
            'site_number': '0041',
            'floor_id': floor['id'],
            'map_id': map_obj['id'],
            'device_type': 'camera',
            'name': '   ',
            'local_x': 10.2,
            'local_y': 8.4,
        },
    )
    assert r.status_code == 400
    assert 'Schema validation failed' in r.json()['detail']


def test_import_batch_idempotency_key_enforced(tmp_path):
    client, _ = build_client(tmp_path)

    payload = {
        'source_file_name': 'devices_0041.csv',
        'source_file_hash': 'abc123',
        'mode': 'merge',
        'records': [{'name': 'CAM-1'}],
    }

    missing = client.post('/api/v1/import/batch', json=payload)
    assert missing.status_code == 400

    headers = {'Idempotency-Key': 'batch-key-1'}
    first = client.post('/api/v1/import/batch', json=payload, headers=headers)
    second = client.post('/api/v1/import/batch', json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()['id'] == second.json()['id']

    list_resp = client.get('/api/v1/import/batches').json()
    assert len(list_resp) == 1


def test_snapshot_and_rollback_flow(tmp_path):
    client, _ = build_client(tmp_path)
    project, _, floor, map_obj = seed_core(client)

    # 4 events from seed_core; add 6 device events to reach 10 and trigger auto snapshot
    for i in range(6):
        r = client.post(
            '/api/v1/devices',
            json={
                'project_id': project['id'],
                'site_number': '0041',
                'floor_id': floor['id'],
                'map_id': map_obj['id'],
                'device_type': 'camera',
                'name': f'CAM-{i + 1}',
                'local_x': 10 + i,
                'local_y': 20 + i,
            },
        )
        assert r.status_code == 200

    snapshots = client.get('/api/v1/revisions/snapshots').json()
    assert len(snapshots) >= 1
    target_snapshot = snapshots[-1]['snapshot_id']

    # Add one more event so rollback has visible effect
    extra = client.post(
        '/api/v1/devices',
        json={
            'project_id': project['id'],
            'site_number': '0041',
            'floor_id': floor['id'],
            'map_id': map_obj['id'],
            'device_type': 'camera',
            'name': 'CAM-EXTRA',
            'local_x': 99,
            'local_y': 88,
        },
    )
    assert extra.status_code == 200

    before = client.get(f"/api/v1/devices?project_id={project['id']}&site_number=0041").json()
    assert len(before) == 7

    rollback = client.post('/api/v1/revisions/rollback', json={'snapshot_id': target_snapshot})
    assert rollback.status_code == 200

    after = client.get(f"/api/v1/devices?project_id={project['id']}&site_number=0041").json()
    assert len(after) == 6


def test_event_ledger_file_exists_and_has_lines(tmp_path):
    client, jsondb_path = build_client(tmp_path)
    seed_core(client)

    ledger = jsondb_path / 'event_ledger.jsonl'
    assert ledger.exists()
    lines = [x for x in ledger.read_text(encoding='utf-8').splitlines() if x.strip()]
    assert len(lines) >= 4
