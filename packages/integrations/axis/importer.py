"""
Axis Site Designer importer.

Reads exported Axis Site Designer JSON files and converts them to
CadOwl device records with computed coverage polygons.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class AxisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AXIS_", env_file=".env", extra="ignore")

    default_mounting_height_m: float = 3.0
    default_tilt_degrees: float = -20.0


@dataclass(slots=True)
class AxisCamera:
    id: str
    name: str
    model: str
    x: float
    y: float
    z: float
    pan: float
    tilt: float
    fov_horizontal: float
    fov_vertical: float
    resolution: str
    coverage_area: list[tuple[float, float]] = field(default_factory=list)
    coverage_distance: float = 0.0
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    firmware: Optional[str] = None


# Axis camera model database (extend as needed)
_CAMERA_SPECS: dict[str, dict] = {
    "AXIS P3245-LV": {"fov_h": 111, "fov_v": 61, "resolution": "1920x1080", "max_distance": 25},
    "AXIS P3245-VE": {"fov_h": 111, "fov_v": 61, "resolution": "1920x1080", "max_distance": 25},
    "AXIS Q6155-E": {"fov_h": 360, "fov_v": 90, "resolution": "1920x1080", "max_distance": 100},
    "AXIS P1448-LE": {"fov_h": 103, "fov_v": 55, "resolution": "3840x2160", "max_distance": 30},
    "AXIS M3057-PLVE": {"fov_h": 360, "fov_v": 360, "resolution": "2592x1944", "max_distance": 15},
}


class AxisImporter:
    """Axis Site Designer importer."""

    def __init__(self, settings: Optional[AxisSettings] = None) -> None:
        self.settings = settings or AxisSettings()

    def import_from_json(self, path: Path) -> list[AxisCamera]:
        """Parse exported Axis Site Designer JSON file."""
        if not path.exists():
            raise FileNotFoundError(f"Axis project file not found: {path}")

        data = json.loads(path.read_text())
        floorplan = data.get("floorplan", {})

        cameras: list[AxisCamera] = []
        for cam_data in data.get("cameras", []):
            cam = self._parse_camera(cam_data, floorplan)
            if cam:
                cameras.append(cam)

        logger.info("axis.import.done", extra={"count": len(cameras), "path": str(path)})
        return cameras

    def _parse_camera(self, data: dict, floorplan: dict) -> Optional[AxisCamera]:
        try:
            position = data.get("position", {})
            orientation = data.get("orientation", {})
            model = data.get("model", "Unknown")
            specs = _CAMERA_SPECS.get(model, {
                "fov_h": 90,
                "fov_v": 60,
                "resolution": "1080p",
                "max_distance": 20,
            })

            x = float(position.get("x", 0))
            y = float(position.get("y", 0))
            z = float(position.get("z", self.settings.default_mounting_height_m))
            pan = float(orientation.get("pan", 0))
            tilt = float(orientation.get("tilt", self.settings.default_tilt_degrees))

            coverage = self._coverage_polygon(x, y, z, pan, tilt, specs["fov_h"], specs["max_distance"])

            return AxisCamera(
                id=str(data.get("id", f"axis-{x}-{y}")),
                name=str(data.get("name", f"Camera {x},{y}")),
                model=model,
                x=x,
                y=y,
                z=z,
                pan=pan,
                tilt=tilt,
                fov_horizontal=float(specs["fov_h"]),
                fov_vertical=float(specs["fov_v"]),
                resolution=str(specs["resolution"]),
                coverage_area=coverage["polygon"],
                coverage_distance=coverage["effective_distance"],
                ip_address=data.get("ip_address"),
                mac_address=data.get("mac_address"),
                firmware=data.get("firmware"),
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("axis.parse.failed", extra={"error": str(exc)})
            return None

    @staticmethod
    def _coverage_polygon(x: float, y: float, z: float, pan: float, tilt: float, fov_h: float, max_dist: float) -> dict:
        pan_rad = math.radians(pan)
        tilt_rad = math.radians(tilt)
        fov_h_rad = math.radians(fov_h)

        if abs(tilt_rad) > 1e-6:
            effective_dist = min(max_dist, z / abs(math.tan(tilt_rad)))
        else:
            effective_dist = max_dist

        left = pan_rad - fov_h_rad / 2
        right = pan_rad + fov_h_rad / 2

        polygon = [
            (x, y),
            (x + effective_dist * math.cos(left), y + effective_dist * math.sin(left)),
            (x + effective_dist * math.cos(right), y + effective_dist * math.sin(right)),
        ]
        return {"polygon": polygon, "effective_distance": effective_dist}

    def to_cadowl_devices(self, cameras: list[AxisCamera], store_number: str, floorplan_width: float = 100.0, floorplan_height: float = 100.0) -> list[dict]:
        """Convert AxisCameras to CadOwl device dicts in 0-100 coordinate space."""
        devices = []
        for cam in cameras:
            x_pct = (cam.x / floorplan_width) * 100 if floorplan_width > 0 else cam.x
            y_pct = (cam.y / floorplan_height) * 100 if floorplan_height > 0 else cam.y
            devices.append({
                "name": cam.name,
                "device_type": "Camera",
                "system_type": "Video Surveillance",
                "manufacturer": "Axis",
                "model": cam.model,
                "x": x_pct,
                "y": y_pct,
                "height_ft": cam.z * 3.28084,
                "coverage_angle": cam.fov_horizontal,
                "coverage_range": cam.coverage_distance,
                "pan": cam.pan,
                "tilt": cam.tilt,
                "resolution": cam.resolution,
                "ip_address": cam.ip_address,
                "mac_address": cam.mac_address,
                "source": "axis_site_designer",
                "store_number": store_number,
            })
        return devices


_shared_importer: Optional[AxisImporter] = None


def get_axis_importer() -> AxisImporter:
    global _shared_importer
    if _shared_importer is None:
        _shared_importer = AxisImporter()
    return _shared_importer
