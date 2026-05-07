#!/usr/bin/env python3
"""Boundary detection and coordinate transforms for CadOwl enhanced."""

from __future__ import annotations

import math
from typing import Optional

import ezdxf

from enhanced_models import BoundingBox, CadDevice


ARTBOARD_SIZE = 1000.0
OBJECT_WIDTH = 800.0
SCALE_MODE = "FIT"


def convert_to_siteowl(x: float, y: float, bbox: BoundingBox) -> tuple[float, float]:
    """Convert CAD coordinates to SiteOwl coordinates."""
    if bbox.width <= 0 or bbox.height <= 0:
        return (0.0, 0.0)

    scale = OBJECT_WIDTH / (max(bbox.width, bbox.height) if SCALE_MODE == "FIT" else bbox.width)

    scaled_w = bbox.width * scale
    scaled_h = bbox.height * scale

    offset_x = (ARTBOARD_SIZE - scaled_w) / 2.0
    offset_y = (ARTBOARD_SIZE - scaled_h) / 2.0

    art_x = offset_x + (x - bbox.min_x) * scale
    art_y = offset_y + (bbox.max_y - y) * scale

    site_x = art_x / 10.0
    site_y = art_y / 10.0

    return (round(site_x, 2), round(site_y, 2))


def calculate_device_bbox(devices: list[CadDevice], trim_ratio: float = 0.0) -> Optional[BoundingBox]:
    """Build a device bbox, with optional percentile trim to suppress outliers."""
    if not devices:
        return None

    xs = sorted(d.x for d in devices)
    ys = sorted(d.y for d in devices)
    n = len(xs)

    if n < 4 or trim_ratio <= 0:
        return BoundingBox(xs[0], ys[0], xs[-1], ys[-1])

    trim_count = min(max(0, int(n * trim_ratio)), (n - 2) // 2)
    return BoundingBox(
        xs[trim_count],
        ys[trim_count],
        xs[-trim_count - 1],
        ys[-trim_count - 1],
    )


def score_boundary_candidate(bbox: BoundingBox, devices: list[CadDevice], baseline_area: float) -> float:
    """Score bbox quality using device coverage + sensible area ratio."""
    if not devices or bbox.area <= 0:
        return -1.0

    inside_count = sum(1 for d in devices if bbox.contains(d.x, d.y, tol=1.0))
    coverage = inside_count / len(devices)

    if coverage == 0:
        return -1.0

    area_ratio = bbox.area / max(baseline_area, 1.0)
    area_penalty = 0.0 if 0.6 <= area_ratio <= 10.0 else min(0.35, abs(math.log10(area_ratio)) * 0.2)

    return coverage - area_penalty


def get_header_extents_bbox(doc: ezdxf.document.Drawing) -> Optional[BoundingBox]:
    """Pull extents from DXF header when available."""
    try:
        extmin = doc.header.get("$EXTMIN")
        extmax = doc.header.get("$EXTMAX")
        if not extmin or not extmax:
            return None

        min_x, min_y = float(extmin[0]), float(extmin[1])
        max_x, max_y = float(extmax[0]), float(extmax[1])

        if any(math.isinf(v) or math.isnan(v) for v in [min_x, min_y, max_x, max_y]):
            return None

        bbox = BoundingBox(min(min_x, max_x), min(min_y, max_y), max(min_x, max_x), max(min_y, max_y))
        return bbox if bbox.area > 0 else None
    except Exception:
        return None


def find_boundary(doc: ezdxf.document.Drawing, devices: list[CadDevice]) -> Optional[BoundingBox]:
    """Find best-fit boundary for coordinate normalization."""
    if not devices:
        return None

    msp = doc.modelspace()
    full_device_bbox = calculate_device_bbox(devices, trim_ratio=0.0)
    trimmed_device_bbox = calculate_device_bbox(devices, trim_ratio=0.02)
    baseline_bbox = trimmed_device_bbox or full_device_bbox

    if not baseline_bbox:
        return None

    candidates: list[tuple[str, BoundingBox]] = []

    for entity in msp.query("LWPOLYLINE"):
        if not entity.closed:
            continue
        try:
            points = list(entity.get_points())
            if len(points) < 3:
                continue
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            bbox = BoundingBox(min(xs), min(ys), max(xs), max(ys))
            if bbox.area > 0:
                candidates.append((f"LWPOLYLINE:{entity.dxf.layer}", bbox))
        except Exception:
            continue

    header_bbox = get_header_extents_bbox(doc)
    if header_bbox:
        candidates.append(("DXF_HEADER_EXTENTS", header_bbox))

    if trimmed_device_bbox:
        candidates.append(("DEVICES_TRIMMED", trimmed_device_bbox))
    if full_device_bbox:
        candidates.append(("DEVICES_FULL", full_device_bbox))

    best_name = ""
    best_bbox = None
    best_score = -1.0

    for name, bbox in candidates:
        score = score_boundary_candidate(bbox, devices, baseline_bbox.area)
        if score > best_score:
            best_score = score
            best_bbox = bbox
            best_name = name

    if best_bbox:
        coverage = sum(1 for d in devices if best_bbox.contains(d.x, d.y, tol=1.0)) / len(devices)
        print(
            f"  Boundary source: {best_name} | "
            f"size={best_bbox.width:.0f}x{best_bbox.height:.0f} | "
            f"coverage={coverage:.1%}"
        )

        if coverage < 0.85 and trimmed_device_bbox:
            print("  WARNING: Low boundary coverage, falling back to trimmed device bounds")
            return trimmed_device_bbox

    return best_bbox or trimmed_device_bbox or full_device_bbox
