"""
CadOwl - CAD to SiteOwl coordinate converter.

A modular library for extracting device coordinates from CAD files
and converting them to SiteOwl's coordinate system.
"""

__version__ = "2.0.0"
__author__ = "Maxim Tsitolovsky"

from .core.mapper import CoordinateMapper, ScaleMode, BoundingBox
from .core.detector import DeviceDetector, Device, DeviceMatch
from .core.exporter import SiteOwlExporter

__all__ = [
    "CoordinateMapper",
    "ScaleMode", 
    "BoundingBox",
    "DeviceDetector",
    "Device",
    "DeviceMatch",
    "SiteOwlExporter",
]
