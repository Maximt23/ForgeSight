"""
Master Infrastructure Bridge.

Correlates data from Doris (store metadata), Saone (camera health), and
Grafana (switch/port telemetry) into a single operational view per store.

This is the "killer feature" — one call gives you the complete picture
of a store with auto-diagnosis for any camera issues.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from ..doris import DorisClient
from ..grafana import GrafanaClient
from ..saone import SaoneClient

logger = logging.getLogger(__name__)


class MasterBridge:
    """Cross-system correlation engine."""

    def __init__(
        self,
        doris: Optional[DorisClient] = None,
        saone: Optional[SaoneClient] = None,
        grafana: Optional[GrafanaClient] = None,
    ) -> None:
        self._doris = doris
        self._saone = saone
        self._grafana = grafana

    async def __aenter__(self) -> "MasterBridge":
        if self._doris is None:
            self._doris = DorisClient()
            await self._doris.__aenter__()
        if self._saone is None:
            self._saone = SaoneClient()
            await self._saone.__aenter__()
        if self._grafana is None:
            self._grafana = GrafanaClient()
            await self._grafana.__aenter__()
        return self

    async def __aexit__(self, *exc) -> None:
        await asyncio.gather(
            self._doris.__aexit__(*exc) if self._doris else asyncio.sleep(0),
            self._saone.__aexit__(*exc) if self._saone else asyncio.sleep(0),
            self._grafana.__aexit__(*exc) if self._grafana else asyncio.sleep(0),
        )

    async def build_store_view(self, store_number: str, devices: list[dict]) -> dict:
        """Return complete infrastructure view for a store."""

        # 1. Register cameras with Saone
        registered = self._saone.bulk_register(devices) if self._saone else 0

        # 2. Fetch data in parallel
        store_task = self._doris.get_store(store_number) if self._doris else asyncio.sleep(0, result=None)
        switches_task = self._grafana.get_switches(store_number) if self._grafana else asyncio.sleep(0, result=[])
        saone_task = self._saone.get_store_summary(store_number) if self._saone else asyncio.sleep(0, result={})

        store, switches, saone_summary = await asyncio.gather(store_task, switches_task, saone_task)

        # 3. Build enriched camera list (correlate Saone health + Grafana port)
        cameras = [d for d in devices if d.get("system_type") == "Video Surveillance" and d.get("ip_address")]
        enriched_cameras = []
        for cam in cameras:
            entry = dict(cam)
            health = await self._saone.get_health(cam["ip_address"]) if self._saone else None
            if health:
                entry["saone_health"] = health.to_dict()
                entry["operational_status"] = "online" if health.is_online else "offline"

            port_info = await self._grafana.find_camera_port(store_number, cam["ip_address"]) if self._grafana else None
            if port_info:
                entry["network"] = {
                    "switch_id": port_info["switch"].switch_id,
                    "switch_hostname": port_info["switch"].hostname,
                    "switch_location": port_info["switch"].location,
                    "port_number": port_info["port"].port_number,
                    "port_status": port_info["port"].status,
                    "poe_enabled": port_info["port"].poe_enabled,
                    "poe_power_watts": port_info["port"].poe_power_watts,
                    "vlan": port_info["port"].vlan,
                }
            enriched_cameras.append(entry)

        # 4. Build view
        view = {
            "store": {
                "store_number": store_number,
                "name": store.name if store else "Unknown",
                "address": store.formatted_address() if store else None,
                "store_type": store.store_type if store else None,
                "latitude": store.latitude if store else None,
                "longitude": store.longitude if store else None,
            },
            "summary": {
                "total_devices": len(devices),
                "total_cameras": len(cameras),
                "cameras_online": saone_summary.get("online", 0),
                "cameras_offline": saone_summary.get("offline", 0),
                "total_switches": len(switches),
                "switches_online": sum(1 for s in switches if s.is_online),
                "cameras_registered_with_saone": registered,
            },
            "devices": devices,
            "cameras": enriched_cameras,
            "network": {
                "switches": [
                    {
                        "switch_id": s.switch_id,
                        "hostname": s.hostname,
                        "location": s.location,
                        "is_online": s.is_online,
                        "ports_up": s.ports_up,
                        "total_ports": s.total_ports,
                        "cpu": s.cpu_usage,
                        "temperature": s.temperature_celsius,
                        "poe_used_watts": s.poe_used_watts,
                        "poe_budget_watts": s.poe_budget_watts,
                    }
                    for s in switches
                ],
            },
            "diagnosis": self._diagnose(enriched_cameras, switches),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        return view

    def _diagnose(self, cameras: list[dict], switches: list) -> dict:
        issues: dict[str, list[dict]] = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
        }

        for cam in cameras:
            name = cam.get("name") or cam.get("ip_address")
            health = cam.get("health") or cam.get("saone_health")
            network = cam.get("network")

            if not health:
                issues["medium"].append({
                    "device": name,
                    "category": "monitoring",
                    "issue": "Camera not registered with Saone",
                    "recommendation": "Register device with Saone monitoring",
                })
                continue

            if not health.get("is_online"):
                if network and network["port_status"] == "down":
                    issues["critical"].append({
                        "device": name,
                        "category": "network",
                        "issue": "Camera offline — switch port DOWN",
                        "recommendation": f"Check {network['switch_hostname']} port {network['port_number']}",
                    })
                elif network and not network["poe_enabled"]:
                    issues["critical"].append({
                        "device": name,
                        "category": "power",
                        "issue": "Camera offline — PoE disabled",
                        "recommendation": f"Enable PoE on {network['switch_hostname']} port {network['port_number']}",
                    })
                elif network and network["poe_power_watts"] == 0:
                    issues["high"].append({
                        "device": name,
                        "category": "power",
                        "issue": "PoE enabled but no power drawn",
                        "recommendation": "Check cable and physical connection",
                    })
                else:
                    issues["high"].append({
                        "device": name,
                        "category": "camera",
                        "issue": "Network healthy but camera offline",
                        "recommendation": "Reboot camera, check firmware",
                    })
            else:
                if (health.get("latency_ms") or 0) > 100:
                    issues["low"].append({
                        "device": name,
                        "category": "performance",
                        "issue": f"High latency: {health['latency_ms']:.1f}ms",
                        "recommendation": "Check network congestion",
                    })
                if (health.get("packet_loss") or 0) > 1:
                    issues["medium"].append({
                        "device": name,
                        "category": "performance",
                        "issue": f"Packet loss: {health['packet_loss']:.1f}%",
                        "recommendation": "Check cable quality",
                    })

        for sw in switches:
            if not sw.is_online:
                issues["critical"].append({
                    "device": sw.hostname,
                    "category": "network",
                    "issue": "Switch OFFLINE",
                    "recommendation": f"Investigate switch in {sw.location}",
                })
            if sw.cpu_usage > 80:
                issues["medium"].append({
                    "device": sw.hostname,
                    "category": "performance",
                    "issue": f"High CPU: {sw.cpu_usage:.1f}%",
                    "recommendation": "Investigate switch load",
                })
            if sw.temperature_celsius and sw.temperature_celsius > 60:
                issues["high"].append({
                    "device": sw.hostname,
                    "category": "environmental",
                    "issue": f"High temperature: {sw.temperature_celsius:.1f}°C",
                    "recommendation": f"Check cooling in {sw.location}",
                })

        return issues


_shared_bridge: Optional[MasterBridge] = None


def get_master_bridge() -> MasterBridge:
    """FastAPI dependency factory."""
    global _shared_bridge
    if _shared_bridge is None:
        _shared_bridge = MasterBridge()
    return _shared_bridge
