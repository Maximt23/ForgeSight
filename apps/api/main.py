import hashlib
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException

from .adapters.axis_siteowl_adapter import convert_asdpx_to_siteowl_rows
from .infrastructure_routes import router as infrastructure_router
from .middleware import install_metrics_endpoint, install_middleware
from .schemas import (
    AsdpxBatchStageRequest,
    AsdpxBatchStageResponse,
    AsdpxDevicePreview,
    AsdpxPreviewRequest,
    AsdpxPreviewResponse,
    Cable,
    CableCreate,
    Device,
    DeviceCreate,
    Floor,
    FloorCreate,
    ImportBatch,
    ImportBatchCommitRequest,
    ImportBatchCommitResponse,
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

app = FastAPI(title="CadOwl Phase 2 API", version="0.2.1")

# Production hardening: structured logging + request IDs + metrics endpoint.
# Safe to call multiple times; idempotent.
install_middleware(app)
install_metrics_endpoint(app)

# Mount the infrastructure router (Saone + Grafana + Master Bridge).
app.include_router(infrastructure_router)


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
    model = Floor(site_id=payload.site_id, name=payload.name, level=payload.level)
    return _safe_write(lambda: STORE.add_floor(model))


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
        if payload.records:
            STORE.stage_batch_payload(created.id, payload.records, {"source": "manual_batch"})
        return created.model_dump(mode="json")

    return _safe_write(
        lambda: ImportBatch.model_validate(
            STORE.idempotent_execute(idempotency_key, "import_batch", payload.model_dump(mode="json"), op)
        )
    )


@app.get("/api/v1/import/batches", response_model=list[ImportBatch])
def list_import_batches():
    return list(STORE.import_batches.values())


@app.post("/api/v1/import/asdpx/preview", response_model=AsdpxPreviewResponse)
def preview_asdpx(payload: AsdpxPreviewRequest):
    src = payload.source_path.strip()
    if not src.lower().endswith(".asdpx"):
        raise HTTPException(status_code=400, detail="source_path must point to an .asdpx file")

    path = Path(src)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"ASDPX file not found: {src}")

    rows, meta = _safe_write(lambda: convert_asdpx_to_siteowl_rows(path))
    sample = rows[:10]
    return AsdpxPreviewResponse(
        source_path=str(path),
        row_count=meta["row_count"],
        sample_rows=[
            AsdpxDevicePreview(
                device_id=x.get("Device ID", ""),
                name=x.get("Name", ""),
                system_type=x.get("System Type", ""),
                device_task_type=x.get("Device/Task Type", ""),
                part_number=x.get("Part Number", ""),
                coordinates=x.get("Coordinates", ""),
                field_notes=x.get("Field Notes", ""),
            )
            for x in sample
        ],
    )


@app.post("/api/v1/import/asdpx/batch", response_model=AsdpxBatchStageResponse)
def stage_asdpx_batch(
    payload: AsdpxBatchStageRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required for import batch writes")

    path = Path(payload.source_path.strip())
    if not path.exists() or path.suffix.lower() != ".asdpx":
        raise HTTPException(status_code=400, detail="source_path must be an existing .asdpx file")

    def op() -> dict:
        rows, meta = convert_asdpx_to_siteowl_rows(path)
        hash_value = hashlib.sha256(path.read_bytes()).hexdigest()
        batch = STORE.add_import_batch(
            ImportBatch(
                source_file_name=path.name,
                source_file_hash=hash_value,
                mode=payload.mode,
                status="validated",
                record_count=len(rows),
            )
        )
        STORE.stage_batch_payload(batch.id, rows, {"source": "axis_asdpx", **meta})
        return {"batch": batch.model_dump(mode="json"), "staged_row_count": len(rows)}

    result = _safe_write(
        lambda: STORE.idempotent_execute(
            idempotency_key,
            "import_asdpx_batch",
            payload.model_dump(mode="json"),
            op,
        )
    )
    return AsdpxBatchStageResponse(batch=ImportBatch.model_validate(result["batch"]), staged_row_count=result["staged_row_count"])


@app.post("/api/v1/import/{batch_id}/commit", response_model=ImportBatchCommitResponse)
def commit_batch(batch_id: UUID, payload: ImportBatchCommitRequest):
    result = _safe_write(
        lambda: STORE.commit_import_batch(
            batch_id=batch_id,
            project_id=payload.project_id,
            site_number=payload.site_number,
            floor_id=payload.floor_id,
            map_id=payload.map_id,
            actor=payload.actor,
        )
    )
    return ImportBatchCommitResponse.model_validate(result)


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
