"""
GIS client — geocoding + building footprint via OpenStreetMap.

Uses Nominatim for geocoding and Overpass for building footprints.
Rate-limit-aware. Cache-heavy (geocoding is expensive and stable).

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class GISSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GIS_", env_file=".env", extra="ignore")

    nominatim_url: str = "https://nominatim.openstreetmap.org"
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    user_agent: str = "CadOwl/1.0 (Walmart Internal)"
    timeout_seconds: float = 30.0
    rate_limit_delay_seconds: float = 1.1  # Nominatim asks for 1 req/sec


@dataclass(slots=True)
class GPSCoordinate:
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: Optional[float] = None


@dataclass(slots=True)
class BuildingFootprint:
    coordinates: list[tuple[float, float]]
    center: GPSCoordinate
    area_sqm: float
    store_number: Optional[str] = None


class GISClient:
    def __init__(self, settings: Optional[GISSettings] = None, http: Optional[httpx.AsyncClient] = None) -> None:
        self.settings = settings or GISSettings()
        self._http = http
        self._geocode_cache: dict[str, GPSCoordinate] = {}
        self._footprint_cache: dict[str, BuildingFootprint] = {}
        self._last_call: Optional[datetime] = None

    async def __aenter__(self) -> "GISClient":
        if self._http is None:
            self._http = httpx.AsyncClient(
                timeout=self.settings.timeout_seconds,
                headers={"User-Agent": self.settings.user_agent},
            )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._http is not None:
            await self._http.aclose()

    async def _throttle(self) -> None:
        """Respect OSM rate limit."""
        if self._last_call:
            elapsed = (datetime.now(timezone.utc) - self._last_call).total_seconds()
            wait = self.settings.rate_limit_delay_seconds - elapsed
            if wait > 0:
                await asyncio.sleep(wait)
        self._last_call = datetime.now(timezone.utc)

    async def geocode(self, address: str) -> Optional[GPSCoordinate]:
        if address in self._geocode_cache:
            return self._geocode_cache[address]

        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.settings.timeout_seconds, headers={"User-Agent": self.settings.user_agent})

        await self._throttle()
        try:
            resp = await self._http.get(
                f"{self.settings.nominatim_url}/search",
                params={"q": address, "format": "json", "limit": 1},
            )
            resp.raise_for_status()
            results = resp.json()
            if not results:
                logger.info("gis.geocode.empty", extra={"address": address})
                return None

            gps = GPSCoordinate(
                latitude=float(results[0]["lat"]),
                longitude=float(results[0]["lon"]),
                accuracy=10.0,
            )
            self._geocode_cache[address] = gps
            return gps
        except httpx.HTTPError as exc:
            logger.error("gis.geocode.failed", extra={"address": address, "error": str(exc)})
            return None

    async def get_building_footprint(self, store_number: str, address: Optional[str] = None, gps: Optional[GPSCoordinate] = None, radius_m: int = 50) -> Optional[BuildingFootprint]:
        if store_number in self._footprint_cache:
            return self._footprint_cache[store_number]

        if not gps and address:
            gps = await self.geocode(address)

        if not gps:
            return None

        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.settings.timeout_seconds, headers={"User-Agent": self.settings.user_agent})

        query = f"""
        [out:json];
        (
          way["building"](around:{radius_m},{gps.latitude},{gps.longitude});
          relation["building"](around:{radius_m},{gps.latitude},{gps.longitude});
        );
        out geom;
        """

        await self._throttle()
        try:
            resp = await self._http.post(self.settings.overpass_url, data={"data": query})
            resp.raise_for_status()
            data = resp.json()
            elements = data.get("elements", [])
            if not elements:
                return None

            # take first building
            b = elements[0]
            if b["type"] == "way":
                coords = [(n["lat"], n["lon"]) for n in b.get("geometry", [])]
            else:
                coords = []
                for member in b.get("members", []):
                    if member.get("role") == "outer":
                        coords.extend([(n["lat"], n["lon"]) for n in member.get("geometry", [])])

            if not coords:
                return None

            center_lat = sum(c[0] for c in coords) / len(coords)
            center_lon = sum(c[1] for c in coords) / len(coords)

            footprint = BuildingFootprint(
                coordinates=coords,
                center=GPSCoordinate(center_lat, center_lon),
                area_sqm=self._polygon_area_m2(coords),
                store_number=store_number,
            )
            self._footprint_cache[store_number] = footprint
            return footprint
        except httpx.HTTPError as exc:
            logger.error("gis.footprint.failed", extra={"store_number": store_number, "error": str(exc)})
            return None

    @staticmethod
    def _polygon_area_m2(coords: list[tuple[float, float]]) -> float:
        if len(coords) < 3:
            return 0.0
        total = 0.0
        for i in range(len(coords)):
            j = (i + 1) % len(coords)
            total += coords[i][0] * coords[j][1]
            total -= coords[j][0] * coords[i][1]
        area_deg2 = abs(total) / 2.0
        return area_deg2 * (111_000**2)

    def device_to_gps(self, device_x: float, device_y: float, footprint: BuildingFootprint) -> GPSCoordinate:
        """Map 0-100 device coordinate to real GPS using building bounding box.

        Coordinate system: (0,0) top-left, (100,100) bottom-right.
        """
        lats = [c[0] for c in footprint.coordinates]
        lons = [c[1] for c in footprint.coordinates]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)

        # Y flipped: 0 = north (max_lat), 100 = south (min_lat)
        lat = max_lat - (device_y / 100.0) * (max_lat - min_lat)
        lon = min_lon + (device_x / 100.0) * (max_lon - min_lon)
        return GPSCoordinate(lat, lon, accuracy=5.0)


@lru_cache(maxsize=1)
def _shared_settings() -> GISSettings:
    return GISSettings()


def get_gis_client() -> GISClient:
    return GISClient(settings=_shared_settings())
