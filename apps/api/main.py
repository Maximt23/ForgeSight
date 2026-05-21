from typing import Optional
from uuid import UUID

from fastapi import FastAPI

from .schemas import (
    Cable,
    CableCreate,
    Device,
    DeviceCreate,
    Floor,
    FloorCreate,
    MapCreate,
    MapModel,
    Project,
    ProjectCreate,
    Site,
    SiteCreate,
    Zone,
    ZoneCreate,
)
from .store import STORE

app = FastAPI(title="CadOwl Phase 1 API", version="0.1.0")


@app.get("/api/v1/health")
def health():
    return {
        "status": "ok",
        "service": "cadowl-api",
        "phase": "phase1-json-store",
        "tracked_entities": {
            "projects": len(STORE.projects),
            "sites": len(STORE.sites),
            "floors": len(STORE.floors),
            "maps": len(STORE.maps),
            "devices": len(STORE.devices),
            "zones": len(STORE.zones),
            "cables": len(STORE.cables),
            "events": len(STORE.events),
        },
        "storage": str(STORE.base_dir),
    }


@app.post("/api/v1/projects", response_model=Project)
def create_project(payload: ProjectCreate):
    model = Project(name=payload.name, code=payload.code)
    return STORE.add_project(model)


@app.get("/api/v1/projects", response_model=list[Project])
def list_projects():
    return list(STORE.projects.values())


@app.post("/api/v1/sites", response_model=Site)
def create_site(payload: SiteCreate):
    model = Site(project_id=payload.project_id, site_number=payload.site_number, name=payload.name)
    return STORE.add_site(model)


@app.get("/api/v1/sites", response_model=list[Site])
def list_sites(project_id: Optional[UUID] = None):
    items = list(STORE.sites.values())
    if project_id:
        return [x for x in items if x.project_id == project_id]
    return items


@app.post("/api/v1/floors", response_model=Floor)
def create_floor(payload: FloorCreate):
    model = Floor(site_id=payload.site_id, name=payload.name, level=payload.level)
    return STORE.add_floor(model)


@app.get("/api/v1/floors", response_model=list[Floor])
def list_floors(site_id: Optional[UUID] = None):
    items = list(STORE.floors.values())
    if site_id:
        return [x for x in items if x.site_id == site_id]
    return items


@app.post("/api/v1/maps", response_model=MapModel)
def create_map(payload: MapCreate):
    model = MapModel(floor_id=payload.floor_id, name=payload.name, source_type=payload.source_type)
    return STORE.add_map(model)


@app.get("/api/v1/maps", response_model=list[MapModel])
def list_maps(floor_id: Optional[UUID] = None):
    items = list(STORE.maps.values())
    if floor_id:
        return [x for x in items if x.floor_id == floor_id]
    return items


@app.post("/api/v1/devices", response_model=Device)
def create_device(payload: DeviceCreate):
    model = Device(
        project_id=payload.project_id,
        site_number=payload.site_number,
        floor_id=payload.floor_id,
        map_id=payload.map_id,
        device_type=payload.device_type,
        name=payload.name,
        local_x=payload.local_x,
        local_y=payload.local_y,
    )
    return STORE.add_device(model)


@app.get("/api/v1/devices", response_model=list[Device])
def list_devices(project_id: Optional[UUID] = None, site_number: Optional[str] = None):
    items = list(STORE.devices.values())
    if project_id:
        items = [x for x in items if x.project_id == project_id]
    if site_number:
        items = [x for x in items if x.site_number == site_number]
    return items


@app.post("/api/v1/zones", response_model=Zone)
def create_zone(payload: ZoneCreate):
    model = Zone(
        project_id=payload.project_id,
        floor_id=payload.floor_id,
        zone_name=payload.zone_name,
        zone_type=payload.zone_type,
    )
    return STORE.add_zone(model)


@app.get("/api/v1/zones", response_model=list[Zone])
def list_zones(project_id: Optional[UUID] = None, floor_id: Optional[UUID] = None):
    items = list(STORE.zones.values())
    if project_id:
        items = [x for x in items if x.project_id == project_id]
    if floor_id:
        items = [x for x in items if x.floor_id == floor_id]
    return items


@app.post("/api/v1/cables", response_model=Cable)
def create_cable(payload: CableCreate):
    model = Cable(
        project_id=payload.project_id,
        site_number=payload.site_number,
        source_device_id=payload.source_device_id,
        destination_device_id=payload.destination_device_id,
        cable_type=payload.cable_type,
    )
    return STORE.add_cable(model)


@app.get("/api/v1/cables", response_model=list[Cable])
def list_cables(project_id: Optional[UUID] = None, site_number: Optional[str] = None):
    items = list(STORE.cables.values())
    if project_id:
        items = [x for x in items if x.project_id == project_id]
    if site_number:
        items = [x for x in items if x.site_number == site_number]
    return items


@app.get("/api/v1/events")
def list_events():
    return STORE.events
