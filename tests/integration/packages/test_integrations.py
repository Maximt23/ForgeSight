"""
Smoke tests for the integrations packages.

Verify that all packages import cleanly and the basic mock paths work
without external network calls.
"""

import asyncio
from pathlib import Path

import pytest


def test_all_packages_import():
    """Every integration package imports without error."""
    from packages.integrations import axis, doris, gis, grafana, master, saone

    assert hasattr(doris, "DorisClient")
    assert hasattr(saone, "SaoneClient")
    assert hasattr(grafana, "GrafanaClient")
    assert hasattr(axis, "AxisImporter")
    assert hasattr(gis, "GISClient")
    assert hasattr(master, "MasterBridge")


@pytest.mark.asyncio
async def test_doris_mock_store():
    from packages.integrations.doris import DorisClient

    async with DorisClient() as client:
        store = await client.get_store("3508")
        assert store is not None
        assert store.store_number == "3508"
        assert store.city == "Broken Arrow"
        assert store.state == "OK"


@pytest.mark.asyncio
async def test_doris_address_formatting():
    from packages.integrations.doris import DorisClient

    async with DorisClient() as client:
        addr = await client.get_address("3508")
        assert addr == "702 N Aspen Ave, Broken Arrow, OK 74012"


@pytest.mark.asyncio
async def test_saone_mock_health():
    from packages.integrations.saone import SaoneClient

    async with SaoneClient() as client:
        client.register_device("cam-001", "192.168.1.101", "AXIS P3245-LV", "3508")
        health = await client.get_health("192.168.1.101")
        assert health is not None
        assert health.camera_id.startswith("saone-")
        assert health.device_id == "cam-001"


@pytest.mark.asyncio
async def test_saone_unregistered_returns_none():
    from packages.integrations.saone import SaoneClient

    async with SaoneClient() as client:
        health = await client.get_health("10.0.0.99")
        assert health is None


@pytest.mark.asyncio
async def test_saone_store_summary():
    from packages.integrations.saone import SaoneClient

    async with SaoneClient() as client:
        client.bulk_register([
            {"device_id": "cam-001", "ip_address": "192.168.1.101", "store_number": "3508"},
            {"device_id": "cam-002", "ip_address": "192.168.1.102", "store_number": "3508"},
        ])
        summary = await client.get_store_summary("3508")
        assert summary["total_cameras"] == 2
        assert "cameras" in summary


@pytest.mark.asyncio
async def test_grafana_mock_switches():
    from packages.integrations.grafana import GrafanaClient

    async with GrafanaClient() as client:
        switches = await client.get_switches("3508")
        assert len(switches) == 2
        assert all(s.store_number == "3508" for s in switches)
        assert switches[0].model == "Cisco Catalyst 9300-48P"


@pytest.mark.asyncio
async def test_grafana_finds_camera_port():
    from packages.integrations.grafana import GrafanaClient

    async with GrafanaClient() as client:
        # First populate switches (which builds the port index)
        switches = await client.get_switches("3508")
        # Pick a known camera IP from the mock data
        sample_cam_ip = None
        for sw in switches:
            for p in sw.ports:
                if p.connected_ip:
                    sample_cam_ip = p.connected_ip
                    break
            if sample_cam_ip:
                break
        assert sample_cam_ip is not None

        port_info = await client.find_camera_port("3508", sample_cam_ip)
        assert port_info is not None
        assert "switch" in port_info
        assert "port" in port_info


@pytest.mark.asyncio
async def test_grafana_diagnose_unmapped_camera():
    from packages.integrations.grafana import GrafanaClient

    async with GrafanaClient() as client:
        result = await client.diagnose_camera("3508", "10.99.99.99")
        assert result["severity"] == "critical"
        assert "diagnosis" in result


def test_axis_importer_parses_sample(tmp_path: Path):
    from packages.integrations.axis import AxisImporter

    sample = {
        "name": "Test Project",
        "floorplan": {"width": 100, "height": 100},
        "cameras": [
            {
                "id": "cam-1",
                "name": "Front Entrance",
                "model": "AXIS P3245-LV",
                "position": {"x": 50, "y": 10, "z": 3},
                "orientation": {"pan": 180, "tilt": -20},
            }
        ],
    }
    import json
    path = tmp_path / "sample.json"
    path.write_text(json.dumps(sample))

    importer = AxisImporter()
    cameras = importer.import_from_json(path)
    assert len(cameras) == 1
    assert cameras[0].name == "Front Entrance"
    assert cameras[0].model == "AXIS P3245-LV"
    assert cameras[0].fov_horizontal == 111


def test_axis_to_cadowl_devices():
    from packages.integrations.axis import AxisImporter, AxisCamera

    importer = AxisImporter()
    cam = AxisCamera(
        id="c1", name="Test", model="AXIS P3245-LV",
        x=50, y=10, z=3, pan=180, tilt=-20,
        fov_horizontal=111, fov_vertical=61, resolution="1920x1080",
        ip_address="192.168.1.50",
    )
    devices = importer.to_cadowl_devices([cam], store_number="3508", floorplan_width=100, floorplan_height=100)
    assert len(devices) == 1
    assert devices[0]["x"] == 50
    assert devices[0]["y"] == 10
    assert devices[0]["store_number"] == "3508"
    assert devices[0]["ip_address"] == "192.168.1.50"


def test_gis_device_to_gps_mapping():
    from packages.integrations.gis import BuildingFootprint, GISClient, GPSCoordinate

    fp = BuildingFootprint(
        coordinates=[(36.06, -95.80), (36.06, -95.79), (36.05, -95.79), (36.05, -95.80)],
        center=GPSCoordinate(36.055, -95.795),
        area_sqm=10_000,
        store_number="3508",
    )
    client = GISClient()
    # Device at (0,0) = top-left = NW corner = (max_lat, min_lon)
    gps = client.device_to_gps(0, 0, fp)
    assert abs(gps.latitude - 36.06) < 0.001
    assert abs(gps.longitude - (-95.80)) < 0.001

    # Device at (100,100) = bottom-right = SE corner
    gps = client.device_to_gps(100, 100, fp)
    assert abs(gps.latitude - 36.05) < 0.001
    assert abs(gps.longitude - (-95.79)) < 0.001


@pytest.mark.asyncio
async def test_master_bridge_builds_view():
    from packages.integrations.master import MasterBridge

    devices = [
        {
            "id": "cam-001",
            "name": "Front Entrance",
            "system_type": "Video Surveillance",
            "ip_address": "192.168.1.101",
            "store_number": "3508",
        },
    ]
    async with MasterBridge() as bridge:
        view = await bridge.build_store_view("3508", devices)

    assert view["store"]["store_number"] == "3508"
    assert "summary" in view
    assert "cameras" in view
    assert "diagnosis" in view
    assert all(k in view["diagnosis"] for k in ["critical", "high", "medium", "low"])
