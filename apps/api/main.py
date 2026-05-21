from typing import Optional
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException

from .schemas import (
    Cable,
    CableCreate,
    Device,
    DeviceCreate,
    Floor,
    FloorCreate,
    ImportBatch,
    ImportBatchCreate,
    MapCreate,
    MapModel,
    Project,
    ProjectCreate,
    RollbackRequest,
    RollbackResult,
    Site,
    SiteCreate,
    Zone,
    ZoneCreate,
)
from .store import STORE

app = FastAPI(title="CadOwl Phase 2 API", version="0.2.0")


def _safe_write(operation):
    try:
        return operation()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/health")
def health():
    return {
        "status": "ok",
        "service": "cadowl-api",
        "phase": "perfect-mode-phase-2",
        "tracked_entities": {
            "projects": len(STORE.projects),
            "sites": len(STORE.sites),
            "floors": len(STORE.floors),
            "maps": len(STORE.maps),
            "devices": len(STORE.devices),
            "zones": len(STORE.zones),
            "cables": len(STORE.cables),
            "import_batches": len(STORE.import_batches),
            "events": len(STORE.events),
        },
        "storage": str(STORE.base_dir),
        "ledger": str(STORE.ledger_path),
        "snapshots": str(STORE.snapshots_path),
    }


@app.post("/api/v1/projects", response_model=Project)
def create_project(payload: ProjectCreate):
    return _safe_write(lambda: STORE.add_project(Project(name=payload.name, code=payload.code)))


@app.get("/api/v1/projects", response_model=list[Project])
def list_projects():
    return list(STORE.projects.values())


@app.post("/api/v1/sites", response_model=Site)
def create_site(payload: SiteCreate):
    model = Site(project_id=payload.project_id, site_number=payload.site_number, name=payload.name)
    return _safe_write(lambda: STORE.add_site(model))


@app.get("/api/v1/sites", response_model=list[Site])
def list_sites(project_id: Optional[UUID] = None):
    items = list(STORE.sites.values())
    if project_id:
        return [x for x in items if x.project_id == project_id]
    return items


@app.post("/api/v1/floors", response_model=Floor)
def create_floor(payload: FloorCreate):
    return _safe_write(lambda: STORE.add_floor(Floor(site_id=payload.site_id, name=payload.name, level=payload.level)))


@app.get("/api/v1/floors", response_model=list[Floor])
def list_floors(site_id: Optional[UUID] = None):
    items = list(STORE.floors.values())
    if site_id:
        return [x for x in items if x.site_id == site_id]
    return items


@app.post("/api/v1/maps", response_model=MapModel)
def create_map(payload: MapCreate):
    model = MapModel(floor_id=payload.floor_id, name=payload.name, source_type=payload.source_type)
    return _safe_write(lambda: STORE.add_map(model))


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
    return _safe_write(lambda: STORE.add_device(model))


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
    return _safe_write(lambda: STORE.add_zone(model))


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
    return _safe_write(lambda: STORE.add_cable(model))


@app.get("/api/v1/cables", response_model=list[Cable])
def list_cables(project_id: Optional[UUID] = None, site_number: Optional[str] = None):
    items = list(STORE.cables.values())
    if project_id:
        items = [x for x in items if x.project_id == project_id]
    if site_number:
        items = [x for x in items if x.site_number == site_number]
    return items


@app.post("/api/v1/import/batch", response_model=ImportBatch)
def create_import_batch(payload: ImportBatchCreate, idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required for import batch writes")

    model = ImportBatch(
        source_file_name=payload.source_file_name,
        source_file_hash=payload.source_file_hash,
        mode=payload.mode,
        status="uploaded",
        record_count=len(payload.records),
    )

    def op() -> dict:
        created = STORE.add_import_batch(model)
        return created.model_dump(mode="json")

    return _safe_write(
        lambda: ImportBatch.model_validate(
            STORE.idempotent_execute(idempotency_key, "import_batch", payload.model_dump(mode="json"), op)
        )
    )


@app.get("/api/v1/import/batches", response_model=list[ImportBatch])
def list_import_batches():
    return list(STORE.import_batches.values())


@app.get("/api/v1/events")
def list_events():
    return STORE.events


@app.get("/api/v1/revisions/snapshots")
def list_snapshots():
    return STORE.list_snapshots()


@app.post("/api/v1/revisions/rollback", response_model=RollbackResult)
def rollback(payload: RollbackRequest):
    if not payload.snapshot_id:
        raise HTTPException(status_code=400, detail="snapshot_id is required")
    result = _safe_write(lambda: STORE.rollback_to_snapshot(payload.snapshot_id))
    return RollbackResult.model_validate(result)
