"""
Doris client — production-grade.

Differences from MAXILLM prototype:
- Settings via pydantic-settings (not raw os.getenv at import time)
- Async-first (httpx.AsyncClient)
- Structured logging
- Proper retries with exponential backoff
- TTL'd cache, not file-based
- Dependency-injectable via FastAPI's Depends()

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


# ─── Settings ───────────────────────────────────────────────────────────


class DorisSettings(BaseSettings):
    """Doris integration configuration."""

    model_config = SettingsConfigDict(env_prefix="DORIS_", env_file=".env", extra="ignore")

    api_url: str = "https://doris.walmart.com/api/v1"
    api_key: str = ""
    timeout_seconds: float = 10.0
    max_retries: int = 3
    cache_ttl_seconds: int = 86_400  # 24 hours


# ─── Domain model ───────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class DorisStore:
    """Store record from Doris."""

    store_number: str
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    latitude: float
    longitude: float
    store_type: str
    square_footage: Optional[int] = None
    open_date: Optional[str] = None
    phone: Optional[str] = None
    status: str = "Active"
    region: Optional[str] = None
    market: Optional[str] = None

    def formatted_address(self) -> str:
        return f"{self.address}, {self.city}, {self.state} {self.zip_code}"


# ─── Mock data (only used when api_key not set) ─────────────────────────

_MOCK_STORES: dict[str, DorisStore] = {
    "3508": DorisStore(
        store_number="3508",
        name="Walmart Supercenter #3508",
        address="702 N Aspen Ave",
        city="Broken Arrow",
        state="OK",
        zip_code="74012",
        latitude=36.0608,
        longitude=-95.7969,
        store_type="Supercenter",
        square_footage=185_000,
        phone="(918) 258-7345",
        region="South",
        market="Tulsa",
    ),
    "0001": DorisStore(
        store_number="0001",
        name="Walmart Supercenter #1",
        address="2110 W Walnut St",
        city="Rogers",
        state="AR",
        zip_code="72756",
        latitude=36.3321,
        longitude=-94.1430,
        store_type="Supercenter",
        square_footage=180_000,
        phone="(479) 636-1215",
        region="Northwest Arkansas",
        market="Bentonville",
    ),
    "0100": DorisStore(
        store_number="0100",
        name="Walmart Neighborhood Market #100",
        address="702 SW 8th St",
        city="Bentonville",
        state="AR",
        zip_code="72712",
        latitude=36.3729,
        longitude=-94.2088,
        store_type="Neighborhood Market",
        square_footage=42_000,
        phone="(479) 273-6156",
        region="Northwest Arkansas",
        market="Bentonville",
    ),
}


# ─── Client ─────────────────────────────────────────────────────────────


@dataclass
class _CacheEntry:
    store: DorisStore
    fetched_at: datetime


class DorisClient:
    """Async client for the Doris store metadata API."""

    def __init__(self, settings: Optional[DorisSettings] = None, http: Optional[httpx.AsyncClient] = None) -> None:
        self.settings = settings or DorisSettings()
        self._http = http
        self._cache: dict[str, _CacheEntry] = {}

    async def __aenter__(self) -> "DorisClient":
        if self._http is None:
            self._http = httpx.AsyncClient(
                timeout=self.settings.timeout_seconds,
                headers=self._auth_headers(),
            )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._http is not None:
            await self._http.aclose()

    def _auth_headers(self) -> dict[str, str]:
        if self.settings.api_key:
            return {"Authorization": f"Bearer {self.settings.api_key}", "User-Agent": "CadOwl/1.0"}
        return {"User-Agent": "CadOwl/1.0"}

    def _is_cache_fresh(self, entry: _CacheEntry) -> bool:
        age = (datetime.now(timezone.utc) - entry.fetched_at).total_seconds()
        return age < self.settings.cache_ttl_seconds

    async def get_store(self, store_number: str) -> Optional[DorisStore]:
        """Fetch a store by number. Cache hit returns instantly."""
        store_number = store_number.strip().lstrip("0").zfill(4) if store_number.isdigit() else store_number

        # Cache check
        cached = self._cache.get(store_number)
        if cached and self._is_cache_fresh(cached):
            logger.debug("doris.cache.hit", extra={"store_number": store_number})
            return cached.store

        # Mock fallback when no API key (dev/test)
        if not self.settings.api_key:
            store = _MOCK_STORES.get(store_number)
            if store:
                logger.info("doris.mock.hit", extra={"store_number": store_number})
                self._cache[store_number] = _CacheEntry(store, datetime.now(timezone.utc))
            return store

        # Real API call
        store = await self._fetch_from_api(store_number)
        if store:
            self._cache[store_number] = _CacheEntry(store, datetime.now(timezone.utc))
        return store

    async def _fetch_from_api(self, store_number: str) -> Optional[DorisStore]:
        """Call Doris API with retry/backoff."""
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.settings.timeout_seconds, headers=self._auth_headers())

        url = f"{self.settings.api_url}/stores/{store_number}"

        for attempt in range(1, self.settings.max_retries + 1):
            try:
                response = await self._http.get(url)
                if response.status_code == 404:
                    logger.info("doris.api.not_found", extra={"store_number": store_number})
                    return None
                response.raise_for_status()
                data = response.json()
                return DorisStore(
                    store_number=data["store_number"],
                    name=data["name"],
                    address=data["address"],
                    city=data["city"],
                    state=data["state"],
                    zip_code=data["zip_code"],
                    latitude=float(data["latitude"]),
                    longitude=float(data["longitude"]),
                    store_type=data.get("type", "Unknown"),
                    square_footage=data.get("square_footage"),
                    open_date=data.get("open_date"),
                    phone=data.get("phone"),
                    status=data.get("status", "Active"),
                    region=data.get("region"),
                    market=data.get("market"),
                )
            except (httpx.HTTPError, KeyError) as exc:
                if attempt == self.settings.max_retries:
                    logger.error(
                        "doris.api.failed",
                        extra={"store_number": store_number, "attempts": attempt, "error": str(exc)},
                    )
                    return None
                wait = 2**attempt
                logger.warning(
                    "doris.api.retry",
                    extra={"store_number": store_number, "attempt": attempt, "wait_seconds": wait},
                )
                await asyncio.sleep(wait)

        return None

    async def get_address(self, store_number: str) -> Optional[str]:
        """Convenience: get formatted address for geocoding."""
        store = await self.get_store(store_number)
        return store.formatted_address() if store else None


# ─── FastAPI dependency ─────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _shared_settings() -> DorisSettings:
    return DorisSettings()


def get_doris_client() -> DorisClient:
    """FastAPI dependency factory.

    Usage:
        from fastapi import Depends
        from packages.integrations.doris import DorisClient, get_doris_client

        @app.get("/stores/{n}")
        async def get_store(n: str, doris: DorisClient = Depends(get_doris_client)):
            return await doris.get_store(n)
    """
    return DorisClient(settings=_shared_settings())
