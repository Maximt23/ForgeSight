"""
Camera + infrastructure routes (Phase 4 — Master Bridge).

Wires the packages/integrations/master bridge into HTTP endpoints.
All routes require authentication via apps.api.auth.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from packages.integrations.grafana import GrafanaClient, get_grafana_client
from packages.integrations.master import MasterBridge, get_master_bridge
from packages.integrations.saone import SaoneClient, get_saone_client

# Auth is optional — only wire it if it's available in the running app context.
try:
    from .auth import Permission, Role, WalmartUser, get_current_user, require_permission

    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False

router = APIRouter(prefix="/api/v1/infrastructure", tags=["infrastructure"])


# ─── Dependency wrappers ────────────────────────────────────────────────


async def _saone() -> SaoneClient:
    client = get_saone_client()
    await client.__aenter__()
    try:
        yield client
    finally:
        await client.__aexit__(None, None, None)


async def _grafana() -> GrafanaClient:
    client = get_grafana_client()
    await client.__aenter__()
    try:
        yield client
    finally:
        await client.__aexit__(None, None, None)


async def _master() -> MasterBridge:
    bridge = get_master_bridge()
    await bridge.__aenter__()
    try:
        yield bridge
    finally:
        await bridge.__aexit__(None, None, None)


# ─── Auth helper that works whether auth module is wired or not ─────────


def _user_dep():
    """Return a Depends() that requires auth IF auth is available."""
    if AUTH_AVAILABLE:
        return Depends(get_current_user)
    return None


# ─── Endpoints ──────────────────────────────────────────────────────────


@router.get("/health/{store_number}")
async def get_store_health(
    store_number: str,
    saone: SaoneClient = Depends(_saone),
):
    """Saone camera health summary for a store."""
    return await saone.get_store_summary(store_number)


@router.get("/network/{store_number}")
async def get_store_network(
    store_number: str,
    grafana: GrafanaClient = Depends(_grafana),
):
    """Grafana switch + port summary for a store."""
    switches = await grafana.get_switches(store_number)
    return {
        "store_number": store_number,
        "switch_count": len(switches),
        "switches": [
            {
                "switch_id": s.switch_id,
                "hostname": s.hostname,
                "location": s.location,
                "is_online": s.is_online,
                "ports_up": s.ports_up,
                "total_ports": s.total_ports,
                "poe_used_watts": s.poe_used_watts,
                "poe_budget_watts": s.poe_budget_watts,
            }
            for s in switches
        ],
    }


@router.get("/diagnose/{store_number}/{camera_ip}")
async def diagnose_camera(
    store_number: str,
    camera_ip: str,
    grafana: GrafanaClient = Depends(_grafana),
):
    """Diagnose why a camera might be offline using switch telemetry."""
    return await grafana.diagnose_camera(store_number, camera_ip)


@router.post("/dashboard/{store_number}")
async def build_dashboard(
    store_number: str,
    devices: list[dict],
    master: MasterBridge = Depends(_master),
):
    """Build full Master Bridge dashboard for a store.

    Body: list of device records (with optional ip_address for cameras).
    """
    if not isinstance(devices, list):
        raise HTTPException(status_code=400, detail="Body must be a list of device dicts")
    return await master.build_store_view(store_number, devices)
