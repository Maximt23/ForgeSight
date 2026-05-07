#!/usr/bin/env python3
"""Shared data models for CadOwl enhanced workflow."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


NAME_TAGS = ["NAME", "DEVICE", "D", "ID", "TAG", "S", "115CD", "WP", "CAMERA", "NUMBER", "LABEL"]


@dataclass
class BoundingBox:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)

    def contains(self, x: float, y: float, tol: float = 0.0) -> bool:
        return (
            self.min_x - tol <= x <= self.max_x + tol
            and self.min_y - tol <= y <= self.max_y + tol
        )


@dataclass
class ExcelDevice:
    """Device data from master Excel file."""

    name: str
    abbreviated_name: str
    system_type: str
    device_type: str
    description: str
    matched: bool = False

    @property
    def match_keywords(self) -> set[str]:
        """Extract keywords for fuzzy matching."""
        text = f"{self.name} {self.description}".upper()
        words = re.findall(r"[A-Z]+", text)
        return {w for w in words if len(w) > 2}


@dataclass
class CadDevice:
    """Device extracted from CAD/DXF."""

    block_name: str
    layer: str
    x: float
    y: float
    attributes: dict[str, str] = field(default_factory=dict)

    @property
    def raw_name(self) -> str:
        """Get device name from attributes or block name."""
        for tag in NAME_TAGS:
            if tag in self.attributes and self.attributes[tag]:
                return self.attributes[tag]
        return self.block_name

    @property
    def match_keywords(self) -> set[str]:
        """Extract keywords for fuzzy matching."""
        text = f"{self.block_name} {self.layer} {self.raw_name}".upper()
        words = re.findall(r"[A-Z]+", text)
        return {w for w in words if len(w) > 2}

    @property
    def inferred_system_type(self) -> str:
        """Auto-detect system type from CAD data."""
        layer_upper = self.layer.upper()
        block_upper = self.block_name.upper()
        name_upper = self.raw_name.upper()
        combined = f"{layer_upper} {block_upper} {name_upper}"

        if any(x in combined for x in ["CCTV", "CAM", "VIDEO", "SURV"]):
            return "Video Surveillance"
        if any(x in combined for x in ["MOTION", "BURG", "DOOR", "INTRUSION"]):
            return "Intrusion Detection"
        if any(x in combined for x in ["ALARM", "NOTIF", "EFP", "FIRE", "PULL", "SMOKE", "FLOW", "RTU", "TAMPER"]):
            return "Fire Alarm"
        return "Fire Alarm"
