from uuid import UUID

from fastapi import APIRouter, HTTPException

from .schemas import ExportRequest, ExportResult, MetadataSearchRequest, MetadataSearchResponse
from .service import EXPORT_SERVICE

router = APIRouter(prefix="/api", tags=["export-center"])


def _store():
    from .. import store as store_module

    return store_module.STORE


def _find_entity_metadata(key: str, field: str, value: str):
    for project_id in _store().projects.keys():
        snapshot = EXPORT_SERVICE.metadata_snapshot(project_id)
        match = next((x for x in snapshot.get(key, []) if x.get(field) == value), None)
        if match:
            return match
    return None


@router.get("/projects/{project_id}/metadata")
def get_project_metadata(project_id: UUID):
    try:
        return EXPORT_SERVICE.metadata_snapshot(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/devices/{device_id}/metadata")
def get_device_metadata(device_id: UUID):
    match = _find_entity_metadata("device_metadata", "device_id", str(device_id))
    if not match:
        raise HTTPException(status_code=404, detail=f"Device metadata not found: {device_id}")
    return match


@router.get("/zones/{zone_id}/metadata")
def get_zone_metadata(zone_id: UUID):
    match = _find_entity_metadata("zone_metadata", "zone_id", str(zone_id))
    if not match:
        raise HTTPException(status_code=404, detail=f"Zone metadata not found: {zone_id}")
    return match


@router.get("/cables/{cable_id}/metadata")
def get_cable_metadata(cable_id: UUID):
    match = _find_entity_metadata("cable_metadata", "cable_id", str(cable_id))
    if not match:
        raise HTTPException(status_code=404, detail=f"Cable metadata not found: {cable_id}")
    return match


@router.get("/imports/{import_id}/metadata")
def get_import_metadata(import_id: UUID):
    match = _find_entity_metadata("import_metadata", "import_batch_id", str(import_id))
    if not match:
        raise HTTPException(status_code=404, detail=f"Import metadata not found: {import_id}")
    return match


@router.get("/exports/{export_id}/metadata")
def get_export_metadata(export_id: str):
    record = EXPORT_SERVICE.repo.get(export_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Export metadata not found: {export_id}")
    return record


@router.post("/metadata/search", response_model=MetadataSearchResponse)
def metadata_search(payload: MetadataSearchRequest):
    rows = EXPORT_SERVICE.search_metadata(payload)
    return MetadataSearchResponse(total=len(rows), results=rows)


@router.post("/exports/project-package", response_model=ExportResult)
def export_project_package(payload: ExportRequest):
    if "zip" not in payload.formats:
        payload.formats.append("zip")
    try:
        return EXPORT_SERVICE.create_export("project-package", payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/exports/siteowl", response_model=ExportResult)
def export_siteowl(payload: ExportRequest):
    if not payload.formats:
        payload.formats = ["csv"]
    try:
        return EXPORT_SERVICE.create_export("siteowl", payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/exports/gis", response_model=ExportResult)
def export_gis(payload: ExportRequest):
    if "geojson" not in payload.formats:
        payload.formats.append("geojson")
    try:
        return EXPORT_SERVICE.create_export("gis", payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/exports/cad", response_model=ExportResult)
def export_cad(payload: ExportRequest):
    if not payload.formats:
        payload.formats = ["svg", "png", "dxf", "pdf"]
    try:
        return EXPORT_SERVICE.create_export("cad", payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/exports/qa-package", response_model=ExportResult)
def export_qa_package(payload: ExportRequest):
    if "zip" not in payload.formats:
        payload.formats.append("zip")
    try:
        return EXPORT_SERVICE.create_export("qa-package", payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/exports/executive-report", response_model=ExportResult)
def export_executive(payload: ExportRequest):
    if "pdf" not in payload.formats:
        payload.formats.append("pdf")
    try:
        return EXPORT_SERVICE.create_export("executive-report", payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
