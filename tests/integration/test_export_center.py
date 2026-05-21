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

    return TestClient(main_module.app)


def seed_project(client):
    project = client.post('/api/v1/projects', json={'name': 'Export Program', 'code': 'EXP-001'}).json()
    site = client.post('/api/v1/sites', json={'project_id': project['id'], 'site_number': '2996', 'name': 'Store 2996'}).json()
    floor = client.post('/api/v1/floors', json={'site_id': site['id'], 'name': 'Main', 'level': 1}).json()
    map_obj = client.post('/api/v1/maps', json={'floor_id': floor['id'], 'name': 'FP-1', 'source_type': 'dxf'}).json()

    for i in range(3):
        r = client.post(
            '/api/v1/devices',
            json={
                'project_id': project['id'],
                'site_number': '2996',
                'floor_id': floor['id'],
                'map_id': map_obj['id'],
                'device_type': 'camera',
                'name': f'CAM-{i+1}',
                'local_x': 10 + i,
                'local_y': 20 + i,
            },
        )
        assert r.status_code == 200

    return project


def test_project_metadata_and_search(tmp_path):
    client = build_client(tmp_path)
    project = seed_project(client)

    meta = client.get(f"/api/projects/{project['id']}/metadata")
    assert meta.status_code == 200
    body = meta.json()
    assert body['project_metadata']['site_number'] == '2996'
    assert len(body['device_metadata']) == 3

    search = client.post(
        '/api/metadata/search',
        json={
            'entity_types': ['device'],
            'filters': [{'field': 'device_type', 'op': 'eq', 'value': 'camera'}],
            'limit': 20,
        },
    )
    assert search.status_code == 200
    s = search.json()
    assert s['total'] >= 3


def test_full_project_package_export(tmp_path):
    client = build_client(tmp_path)
    project = seed_project(client)

    r = client.post(
        '/api/exports/project-package',
        json={
            'project_id': project['id'],
            'created_by': 'maxim',
            'export_mode': 'full_project_intelligence_package',
            'formats': ['zip', 'json', 'csv', 'geojson'],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body['blocked'] is False
    assert body['package_path']
    assert Path(body['manifest_path']).exists()
    assert Path(body['package_path']).exists()

    manifest = Path(body['manifest_path']).read_text(encoding='utf-8')
    assert 'record_counts' in manifest

    history = client.get(f"/api/exports/{body['export_id']}/metadata")
    assert history.status_code == 200
    h = history.json()
    assert h['export_type'] == 'project-package'


def test_siteowl_and_gis_exports(tmp_path):
    client = build_client(tmp_path)
    project = seed_project(client)

    siteowl = client.post('/api/exports/siteowl', json={'project_id': project['id'], 'formats': ['csv']})
    assert siteowl.status_code == 200
    assert siteowl.json()['blocked'] is False

    gis = client.post('/api/exports/gis', json={'project_id': project['id'], 'formats': ['geojson', 'zip']})
    assert gis.status_code == 200
    assert gis.json()['blocked'] is False
