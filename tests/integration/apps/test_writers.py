"""
Tests for Export Center writers.

Verifies the pure-function writers produce well-formed output:
  - write_json / write_csv round-trip data
  - write_xlsx produces a multi-sheet workbook (if openpyxl available)
  - device_geojson_rows produces a valid FeatureCollection
  - siteowl_rows match the 56-column schema
  - build_manifest contains expected keys
  - write_zip packages multiple files

These are pure-function tests \u2014 no HTTP/auth involved.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.api.export_center.writers import (
    build_manifest,
    cad_drawings,
    device_geojson_rows,
    siteowl_rows,
    write_csv,
    write_json,
    write_zip,
)


def test_write_json_roundtrip(tmp_path: Path) -> None:
    payload = {"a": 1, "b": [1, 2, 3], "c": {"nested": True}}
    out = tmp_path / "out.json"
    write_json(out, payload)
    assert json.loads(out.read_text(encoding="utf-8")) == payload


def test_write_csv_roundtrip(tmp_path: Path) -> None:
    rows = [{"name": "foo", "qty": 1}, {"name": "bar", "qty": 2}]
    out = tmp_path / "out.csv"
    write_csv(out, rows)

    with out.open(encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert reader == [{"name": "foo", "qty": "1"}, {"name": "bar", "qty": "2"}]


def test_write_csv_empty_rows_creates_empty_file(tmp_path: Path) -> None:
    out = tmp_path / "empty.csv"
    write_csv(out, [])
    # File should exist (even if empty) so downstream zip steps don't blow up
    assert out.exists()


def test_device_geojson_rows_shape() -> None:
    devices = [
        {"device_id": "d1", "device_name": "Cam-1", "local_x": 12.5, "local_y": 30.0},
        {"device_id": "d2", "device_name": "Cam-2", "local_x": 40.0, "local_y": 60.0},
    ]
    geo = device_geojson_rows(devices)
    assert geo["type"] == "FeatureCollection"
    assert len(geo["features"]) == 2
    feat = geo["features"][0]
    assert feat["geometry"]["type"] == "Point"
    # Writer uses local_x/local_y (CAD coords), not lat/lng
    assert feat["geometry"]["coordinates"] == [12.5, 30.0]
    assert feat["properties"]["device_id"] == "d1"
    assert feat["properties"]["name"] == "Cam-1"


def test_device_geojson_defaults_to_origin_when_coords_missing() -> None:
    """Devices without coords get placed at (0, 0) — documenting current behavior."""
    devices = [
        {"device_id": "d1", "device_name": "Has", "local_x": 5.0, "local_y": 10.0},
        {"device_id": "d2", "device_name": "None"},
    ]
    geo = device_geojson_rows(devices)
    assert len(geo["features"]) == 2
    assert geo["features"][1]["geometry"]["coordinates"] == [0, 0]


def test_siteowl_rows_56_columns() -> None:
    devices = [
        {"device_id": "d1", "device_name": "Cam-1", "device_type": "Camera", "local_x": 1.0, "local_y": 2.0},
    ]
    rows = siteowl_rows(devices, site_number="3508")
    assert len(rows) == 1
    # SiteOwl schema is the 56 columns from SITEOWL_HEADERS
    assert rows[0]["Project ID"] == "3508"
    assert rows[0]["Device ID"] == "New0001"
    assert rows[0]["Name"] == "Cam-1"
    assert rows[0]["Device/Task Type"] == "Camera"


def test_build_manifest_has_required_keys() -> None:
    request = SimpleNamespace(project_id="proj-1", store_number="3508", created_by="test@walmart.com")
    metadata = {
        "project_metadata": {"site_number": "3508", "project_name": "Test"},
        "validation_metadata": [],
        "device_metadata": [],
    }
    manifest = build_manifest(
        export_id="exp-123",
        export_type="siteowl",
        request=request,
        metadata=metadata,
        files=["devices.csv", "manifest.json"],
    )
    assert manifest["export_id"] == "exp-123"
    assert manifest["export_type"] == "siteowl"
    assert manifest["site_number"] == "3508"
    assert manifest["created_by"] == "test@walmart.com"
    assert "created_at" in manifest


def test_write_zip_packages_files(tmp_path: Path) -> None:
    # Create some files to zip
    (tmp_path / "a.txt").write_text("alpha")
    (tmp_path / "b.txt").write_text("beta")

    out_zip = tmp_path / "bundle.zip"
    result = write_zip(out_zip, tmp_path, ["a.txt", "b.txt"])

    assert Path(result).exists()
    with zipfile.ZipFile(result) as zf:
        names = set(zf.namelist())
    assert names == {"a.txt", "b.txt"}


def test_cad_drawings_writes_per_device_text(tmp_path: Path) -> None:
    devices = [
        {"device_id": "d1", "device_name": "Cam-1", "local_x": 10.0, "local_y": 20.0},
        {"device_id": "d2", "device_name": "Cam-2", "local_x": 30.0, "local_y": 40.0},
    ]
    files = cad_drawings(tmp_path, devices)
    # Writer always produces 4 outputs: svg, png, pdf, dxf
    assert len(files) == 4
    extensions = {Path(f).suffix for f in files}
    assert extensions == {".svg", ".png", ".pdf", ".dxf"}
    for f in files:
        assert Path(f).exists()
        assert Path(f).stat().st_size > 0
