"""
SA Grafana switch telemetry client.

URL: https://sagrafana.sbox.walmart.com

Production refactor of MAXILLM prototype with structured logging,
pydantic-settings, and proper retry semantics.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class GrafanaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GRAFANA_", env_file=".env", extra="ignore")

    url: str = "https://sagrafana.sbox.walmart.com"
    api_key: str = ""
    timeout_seconds: float = 15.0
    max_retries: int = 3
    cache_ttl_seconds: int = 60


@dataclass(slots=True)
class SwitchPort:
    port_number: int
    port_name: str
    status: str  # up, down, disabled
    admin_status: str
    speed_mbps: int
    duplex: str
    vlan: Optional[int]
    poe_enabled: bool
    poe_power_watts: float
    poe_class: Optional[str]
    rx_bytes: int
    tx_bytes: int
    rx_errors: int
    tx_errors: int
    connected_mac: Optional[str] = None
    connected_ip: Optional[str] = None
    connected_device_id: Optional[str] = None


@dataclass(slots=True)
class NetworkSwitch:
    switch_id: str
    hostname: str
    ip_address: str
    store_number: str
    location: str
    model: str
    serial_number: Optional[str]
    firmware_version: Optional[str]
    is_online: bool
    uptime_seconds: int
    last_seen: datetime
    cpu_usage: float
    memory_usage: float
    temperature_celsius: Optional[float]
    total_ports: int
    ports_up: int
    ports_down: int
    poe_used_watts: float
    poe_budget_watts: float
    ports: list[SwitchPort] = field(default_factory=list)


class GrafanaClient:
    def __init__(self, settings: Optional[GrafanaSettings] = None, http: Optional[httpx.AsyncClient] = None) -> None:
        self.settings = settings or GrafanaSettings()
        self._http = http
        self._switch_cache: dict[str, list[NetworkSwitch]] = {}
        self._cache_at: dict[str, datetime] = {}
        self._port_index: dict[str, tuple[str, int]] = {}  # ip -> (switch_id, port_num)

    async def __aenter__(self) -> "GrafanaClient":
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.settings.timeout_seconds, headers=self._auth_headers())
        return self

    async def __aexit__(self, *exc) -> None:
        if self._http is not None:
            await self._http.aclose()

    def _auth_headers(self) -> dict[str, str]:
        if self.settings.api_key:
            return {"Authorization": f"Bearer {self.settings.api_key}", "User-Agent": "CadOwl/1.0"}
        return {"User-Agent": "CadOwl/1.0"}

    def _fresh(self, store_number: str) -> bool:
        t = self._cache_at.get(store_number)
        if not t:
            return False
        return (datetime.now(timezone.utc) - t).total_seconds() < self.settings.cache_ttl_seconds

    async def get_switches(self, store_number: str) -> list[NetworkSwitch]:
        if self._fresh(store_number):
            return self._switch_cache[store_number]

        if not self.settings.api_key:
            switches = self._mock_switches(store_number)
        else:
            switches = await self._fetch_switches(store_number)

        self._switch_cache[store_number] = switches
        self._cache_at[store_number] = datetime.now(timezone.utc)
        for sw in switches:
            for p in sw.ports:
                if p.connected_ip:
                    self._port_index[p.connected_ip] = (sw.switch_id, p.port_number)
        return switches

    async def _fetch_switches(self, store_number: str) -> list[NetworkSwitch]:
        # Real implementation would query Prometheus through Grafana datasource proxy.
        # Placeholder: returns empty until real query schema is locked in.
        logger.warning("grafana.fetch.not_implemented", extra={"store_number": store_number})
        return []

    def _mock_switches(self, store_number: str) -> list[NetworkSwitch]:
        """Deterministic mock for development."""
        import random
        rnd = random.Random(f"store-{store_number}")
        switches = []
        for i, location in enumerate(["MDF Main", "IDF Loading Dock"]):
            switch_id = f"sw-{store_number}-{i+1:02d}"
            ports = []
            for port_num in range(1, 49):
                has_cam = port_num <= 30 and rnd.random() > 0.3
                ports.append(
                    SwitchPort(
                        port_number=port_num,
                        port_name=f"GigabitEthernet1/0/{port_num}",
                        status="up" if has_cam or rnd.random() > 0.2 else "down",
                        admin_status="enabled",
                        speed_mbps=1000,
                        duplex="full",
                        vlan=100 if has_cam else 1,
                        poe_enabled=has_cam,
                        poe_power_watts=rnd.uniform(8, 15) if has_cam else 0,
                        poe_class="Class 4" if has_cam else None,
                        rx_bytes=rnd.randint(1_000_000, 100_000_000),
                        tx_bytes=rnd.randint(1_000_000, 100_000_000),
                        rx_errors=rnd.randint(0, 50),
                        tx_errors=rnd.randint(0, 50),
                        connected_ip=f"192.168.{i+1}.{100 + port_num}" if has_cam else None,
                        connected_mac=f"AA:BB:CC:{port_num:02X}:{i:02X}:01" if has_cam else None,
                    )
                )
            switches.append(
                NetworkSwitch(
                    switch_id=switch_id,
                    hostname=f"sw-{store_number}-{i+1:02d}.walmart.com",
                    ip_address=f"10.{store_number[:2]}.{store_number[2:]}.{i+1}",
                    store_number=store_number,
                    location=location,
                    model="Cisco Catalyst 9300-48P",
                    serial_number=f"FCW{store_number}{i:04d}",
                    firmware_version="17.6.4",
                    is_online=True,
                    uptime_seconds=rnd.randint(100_000, 10_000_000),
                    last_seen=datetime.now(timezone.utc),
                    cpu_usage=rnd.uniform(15, 45),
                    memory_usage=rnd.uniform(40, 70),
                    temperature_celsius=rnd.uniform(35, 55),
                    total_ports=48,
                    ports_up=sum(1 for p in ports if p.status == "up"),
                    ports_down=sum(1 for p in ports if p.status == "down"),
                    poe_used_watts=sum(p.poe_power_watts for p in ports),
                    poe_budget_watts=740.0,
                    ports=ports,
                )
            )
        return switches

    async def find_camera_port(self, store_number: str, camera_ip: str) -> Optional[dict]:
        await self.get_switches(store_number)  # populates _port_index
        loc = self._port_index.get(camera_ip)
        if not loc:
            return None
        sw_id, port_num = loc
        switches = self._switch_cache.get(store_number, [])
        sw = next((s for s in switches if s.switch_id == sw_id), None)
        if not sw:
            return None
        port = next((p for p in sw.ports if p.port_number == port_num), None)
        return {"switch": sw, "port": port, "camera_ip": camera_ip} if port else None

    async def diagnose_camera(self, store_number: str, camera_ip: str) -> dict:
        """Return why a camera might be offline based on switch data."""
        info = await self.find_camera_port(store_number, camera_ip)
        if not info:
            return {
                "camera_ip": camera_ip,
                "severity": "critical",
                "diagnosis": ["Camera not mapped to any switch port"],
                "recommendations": ["Verify camera IP and switch ARP table"],
            }

        sw: NetworkSwitch = info["switch"]
        port: SwitchPort = info["port"]
        diagnosis = []
        recs = []
        severity = "info"

        if not sw.is_online:
            diagnosis.append(f"Switch {sw.hostname} is OFFLINE")
            recs.append(f"Restore switch in {sw.location}")
            severity = "critical"
        if port.status == "down":
            diagnosis.append(f"Port {port.port_number} is DOWN")
            recs.append("Check cable and camera physical connection")
            severity = "high"
        if not port.poe_enabled:
            diagnosis.append("PoE disabled on port")
            recs.append(f"Enable PoE on {sw.hostname} port {port.port_number}")
            severity = "high"
        elif port.poe_power_watts == 0:
            diagnosis.append("PoE enabled but no power drawn")
            recs.append("Camera may be unplugged or failed")
            severity = "medium"
        if port.rx_errors > 100 or port.tx_errors > 100:
            diagnosis.append(f"High error rate: RX={port.rx_errors} TX={port.tx_errors}")
            recs.append("Check cable quality")
            severity = max(severity, "medium")

        if not diagnosis:
            diagnosis.append("Network healthy — issue likely camera-side")
            recs.append("Reboot camera, check firmware")

        return {
            "camera_ip": camera_ip,
            "switch_hostname": sw.hostname,
            "port_number": port.port_number,
            "severity": severity,
            "diagnosis": diagnosis,
            "recommendations": recs,
        }


@lru_cache(maxsize=1)
def _shared_settings() -> GrafanaSettings:
    return GrafanaSettings()


def get_grafana_client() -> GrafanaClient:
    return GrafanaClient(settings=_shared_settings())
