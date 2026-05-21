import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient


def build_client(tmp_path):
    os.environ["CADOWL_JSONDB_DIR"] = str(tmp_path / "jsondb")
    os.environ["CADOWL_SCHEMA_DIR"] = str(Path("C:/MAXILLM/cadowl/apps/api/schemas_json"))
    os.environ["CADOWL_DEV_MODE"] = "true"

    import apps.api.store as store_module
    import apps.api.main as main_module

    importlib.reload(store_module)
    importlib.reload(main_module)

    return TestClient(main_module.app)


def seed_core(client):
    project = client.post('/api/v1/projects', json={'name': 'Design OS', 'code': 'DOS-01'}).json()
    site = client.post('/api/v1/sites', json={'project_id': project['id'], 'site_number': '2996', 'name': 'Pilot'}).json()
    floor = client.post('/api/v1/floors', json={'site_id': site['id'], 'name': 'Ground', 'level': 0}).json()
    return project, site, floor


def test_design_entities_support_geometry_and_fov(tmp_path):
    client = build_client(tmp_path)
    project, _, floor = seed_core(client)

    cam_1 = client.post(
        '/api/v1/devices',
        json={
            'project_id': project['id'],
            'site_number': '2996',
            'floor_id': floor['id'],
            'device_type': 'camera',
            'name': 'CAM-ENTRY',
            'local_x': 10,
            'local_y': 20,
            'fov_degrees': 100,
            'fov_range': 25,
        },
    )
    cam_2 = client.post(
        '/api/v1/devices',
        json={
            'project_id': project['id'],
            'site_number': '2996',
            'floor_id': floor['id'],
            'device_type': 'camera',
            'name': 'CAM-EXIT',
            'local_x': 70,
            'local_y': 40,
            'fov_degrees': 120,
            'fov_range': 30,
        },
    )

    assert cam_1.status_code == 200
    assert cam_2.status_code == 200
    assert cam_1.json()['fov_degrees'] == 100

    zone = client.post(
        '/api/v1/zones',
        json={
            'project_id': project['id'],
            'floor_id': floor['id'],
            'zone_name': 'Front Sales',
            'zone_type': 'security',
            'points': [
                {'x': 5, 'y': 5},
                {'x': 40, 'y': 5},
                {'x': 40, 'y': 35},
                {'x': 5, 'y': 35},
            ],
        },
    )
    assert zone.status_code == 200
    assert len(zone.json()['points']) == 4

    cable = client.post(
        '/api/v1/cables',
        json={
            'project_id': project['id'],
            'site_number': '2996',
            'source_device_id': cam_1.json()['id'],
            'destination_device_id': cam_2.json()['id'],
            'cable_type': 'cat6',
            'path_points': [
                {'x': 10, 'y': 20},
                {'x': 35, 'y': 22},
                {'x': 70, 'y': 40},
            ],
            'estimated_length': 64.5,
        },
    )
    assert cable.status_code == 200
    assert len(cable.json()['path_points']) == 3

    listed_zones = client.get(f"/api/v1/zones?project_id={project['id']}&floor_id={floor['id']}")
    listed_cables = client.get(f"/api/v1/cables?project_id={project['id']}&site_number=2996")

    assert listed_zones.status_code == 200
    assert listed_cables.status_code == 200
    assert len(listed_zones.json()) == 1
    assert len(listed_cables.json()) == 1
