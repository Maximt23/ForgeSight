import csv
import json
import math
import re
from pathlib import Path
from typing import Any

from cadowl.core.exporter import SITEOWL_HEADERS

DEFAULT_PRICING = {
    "02018-001": 455.57,
    "02375-001": 0.00,
    "03184-001": 742.84,
    "02757-001": 1782.71,
    "02985-001": 1321.63,
    "02635-001": 1221.63,
    "02944-001": 963.74,
    "01682-004": 0.00,
    "02657-001": 1704.26,
    "02658-001": 1704.26,
    "02487-001": 1053.11,
    "02960-001": 1393.99,
    "02784-001": 2387.32,
}

PART_MODEL_MAP = {
    "02018-001": ("AXIS M3077-PLVE", "Fisheye Camera"),
    "02375-001": ("AXIS M3088-V", "Dome Camera"),
    "03184-001": ("AXIS P1488-LE", "Bullet Camera"),
    "02757-001": ("AXIS P1518-LE", "Bullet Camera"),
    "02985-001": ("AXIS P3288-LV", "Dome Camera"),
    "02635-001": ("AXIS P3738-PLE", "Panoramic Camera"),
    "02944-001": ("AXIS P4708-PLVE", "Panoramic Camera"),
    "01682-004": ("AXIS P5655-E", "PTZ Camera"),
    "02657-001": ("AXIS Q3839-PVE", "Panoramic Camera"),
    "02658-001": ("AXIS Q4809-PVE", "Panoramic Camera"),
    "02487-001": ("AXIS Q9307-LV", "Dome Camera"),
    "02960-001": ("AXIS C1720", "General Video Surveillance"),
    "02784-001": ("AXIS I8307-VE", "General Video Surveillance"),
}


def _normalize_angle(angle: Any) -> int:
    if not isinstance(angle, (int, float)):
        return 0
    x = int(round(angle)) % 360
    return x if x >= 0 else x + 360


def _fmt_coordinates(x: float, y: float) -> str:
    x = min(99.99, max(0.0, x))
    y = min(99.99, max(0.0, y))
    return f'"({x:05.2f}, {y:05.2f})"'


def _extract_children(payload: dict[str, Any]) -> list[dict[str, Any]]:
    root_children = payload.get("children")
    if isinstance(root_children, list):
        return [x for x in root_children if isinstance(x, dict)]
    project = payload.get("project", {})
    project_children = project.get("children") if isinstance(project, dict) else None
    if isinstance(project_children, list):
        return [x for x in project_children if isinstance(x, dict)]
    return []


def _infer_site_number(asdpx_path: Path, payload: dict[str, Any]) -> str:
    project = payload.get("project", {})
    candidate_values = []
    if isinstance(project, dict):
        candidate_values.append(str(project.get("name") or ""))
    candidate_values.append(asdpx_path.stem)

    for candidate in candidate_values:
        match = re.search(r"(\d{3,})", candidate)
        if match:
            return match.group(1)
    return asdpx_path.stem

def convert_asdpx_to_siteowl_rows(asdpx_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = json.loads(asdpx_path.read_text(encoding="utf-8"))
    children = _extract_children(data)
    site_number = _infer_site_number(asdpx_path, data)

    floor_plans = [x for x in children if x.get("type") == "floorPlan" and isinstance(x.get("image"), dict)]
    if not floor_plans:
        raise ValueError("No floorPlan with image found in ASDPX")
    floor_plan = floor_plans[0]

    img = floor_plan["image"]
    dims = img.get("dimensions") or {"width": 1000, "height": 1000}
    bounds = img.get("bounds")
    if not bounds or not bounds.get("topLeft") or not bounds.get("bottomRight"):
        raise ValueError("floorPlan image missing GPS bounds")

    img_width = float(dims.get("width") or 1000)
    img_height = float(dims.get("height") or 1000)

    geo = img.get("geoLocation") or {}
    width_m = float(geo.get("width") or 0)
    height_m = float(geo.get("height") or 0)

    if width_m <= 0 or height_m <= 0:
        lat_range = bounds["topLeft"]["lat"] - bounds["bottomRight"]["lat"]
        lng_range = bounds["bottomRight"]["lng"] - bounds["topLeft"]["lng"]
        avg_lat = (bounds["topLeft"]["lat"] + bounds["bottomRight"]["lat"]) / 2
        feet_per_degree_lat = 364000
        feet_per_degree_lng = 364000 * math.cos(avg_lat * math.pi / 180)
        width_m = (abs(lng_range) * feet_per_degree_lng) / 3.28084
        height_m = (abs(lat_range) * feet_per_degree_lat) / 3.28084

    width_ft = width_m * 3.28084
    height_ft = height_m * 3.28084

    target_width = 80.0
    scale = target_width / max(width_ft, 1.0)
    target_height = height_ft * scale
    offset_x = 50.0 - target_width / 2.0
    offset_y = 50.0 - target_height / 2.0

    quotation = next((x for x in children if x.get("type") == "quotation"), None)
    pricing = quotation.get("pricesByPartNumber") if isinstance(quotation, dict) else None
    if not isinstance(pricing, dict) or not pricing:
        pricing = DEFAULT_PRICING
    parts = list(pricing.keys())

    points = [x for x in children if x.get("type") == "installationPoint"]
    rows: list[dict[str, Any]] = []

    lat_range = bounds["topLeft"]["lat"] - bounds["bottomRight"]["lat"]
    lng_range = bounds["bottomRight"]["lng"] - bounds["topLeft"]["lng"]
    px_to_feet_x = width_ft / max(img_width, 1.0)
    px_to_feet_y = height_ft / max(img_height, 1.0)

    for idx, point in enumerate(points, start=1):
        loc = point.get("location") or {}
        lat = loc.get("lat")
        lng = loc.get("lng")
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            continue

        pixel_x = ((lng - bounds["topLeft"]["lng"]) / max(lng_range, 1e-9)) * img_width
        pixel_y = ((bounds["topLeft"]["lat"] - lat) / max(lat_range, 1e-9)) * img_height
        feet_x = pixel_x * px_to_feet_x
        feet_y = pixel_y * px_to_feet_y

        display_x = (feet_x / max(width_ft, 1.0)) * target_width + offset_x
        display_y = (feet_y / max(height_ft, 1.0)) * target_height + offset_y

        sensors = point.get("sensors") or []
        sensor = sensors[0] if sensors else {}
        settings = sensor.get("settings") or {}
        target = sensor.get("target") or {}

        coverage_angle = int(round(settings.get("horizontalFov", 90)))
        coverage_range = int(round(target.get("distance", 30)))
        coverage_direction = _normalize_angle(target.get("horizontalAngle", 0))

        height_ft_device = float(point.get("height", 3)) * 3.28084

        part_number = parts[(idx - 1) % len(parts)] if parts else ""
        model_name, device_type = PART_MODEL_MAP.get(part_number, (f"Camera {idx}", "Fixed Camera"))
        replacement_cost = float(pricing.get(part_number, 0)) if part_number else 0.0

        row = {h: "" for h in SITEOWL_HEADERS}
        row["Project ID"] = site_number
        row["Plan ID"] = str(idx)
        row["Device ID"] = f"New{idx:04d}"
        row["Name"] = model_name
        row["Device / Task"] = "Device"
        row["System Type"] = "Video Surveillance"
        row["Device/Task Type"] = device_type
        row["Part Number"] = part_number
        row["Manufacturer"] = "Axis"
        row["IP / Analog"] = "IP"
        row["Coverage Direction"] = str(coverage_direction)
        row["Coverage Angle"] = str(coverage_angle)
        row["Coverage Range"] = str(coverage_range)
        row["Height (ft)"] = f"{height_ft_device:.1f}"
        gps_text = f"{lat:.6f},{lng:.6f}"
        row["Barcode"] = gps_text
        row["Field Notes"] = f'"{gps_text}"'
        row["Replacement Cost"] = f"{replacement_cost:.2f}"
        row["Coordinates"] = _fmt_coordinates(display_x, display_y)

        rows.append(row)

    if not rows:
        raise ValueError("No valid installationPoint entries with GPS coordinates were found")

    metadata = {
        "source": str(asdpx_path),
        "site_number": site_number,
        "row_count": len(rows),
        "floorplan_count": len(floor_plans),
        "target_width": target_width,
        "target_height": target_height,
    }
    return rows, metadata


def write_siteowl_csv(rows: list[dict[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=SITEOWL_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return output_path
