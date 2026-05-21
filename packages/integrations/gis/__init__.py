"""GIS / geocoding / building footprint integration (OpenStreetMap)."""

from .client import BuildingFootprint, GISClient, GISSettings, GPSCoordinate, get_gis_client

__all__ = ["BuildingFootprint", "GISClient", "GISSettings", "GPSCoordinate", "get_gis_client"]
