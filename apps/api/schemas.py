from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BaseEntity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectCreate(BaseModel):
    name: str
    code: str


class Project(BaseEntity):
    name: str
    code: str


class SiteCreate(BaseModel):
    project_id: UUID
    site_number: str
    name: str


class Site(BaseEntity):
    project_id: UUID
    site_number: str
    name: str


class FloorCreate(BaseModel):
    site_id: UUID
    name: str
    level: int = 0


class Floor(BaseEntity):
    site_id: UUID
    name: str
    level: int = 0


class MapCreate(BaseModel):
    floor_id: UUID
    name: str
    source_type: Literal["pdf", "dxf", "image", "unknown"] = "unknown"


class MapModel(BaseEntity):
    floor_id: UUID
    name: str
    source_type: Literal["pdf", "dxf", "image", "unknown"] = "unknown"


class DeviceCreate(BaseModel):
    project_id: UUID
    site_number: str
    floor_id: Optional[UUID] = None
    map_id: Optional[UUID] = None
    device_type: str
    name: str
    local_x: float = Field(ge=0)
    local_y: float = Field(ge=0)
    fov_degrees: Optional[float] = Field(default=None, ge=1, le=360)
    fov_range: Optional[float] = Field(default=None, ge=0)


class Device(BaseEntity):
    project_id: UUID
    site_number: str
    floor_id: Optional[UUID] = None
    map_id: Optional[UUID] = None
    device_type: str
    name: str
    local_x: float = Field(ge=0)
    local_y: float = Field(ge=0)
    fov_degrees: Optional[float] = Field(default=None, ge=1, le=360)
    fov_range: Optional[float] = Field(default=None, ge=0)


class ZoneCreate(BaseModel):
    project_id: UUID
    floor_id: UUID
    zone_name: str
    zone_type: str
    points: list[dict[str, float]] = Field(default_factory=list)


class Zone(BaseEntity):
    project_id: UUID
    floor_id: UUID
    zone_name: str
    zone_type: str
    points: list[dict[str, float]] = Field(default_factory=list)


class CableCreate(BaseModel):
    project_id: UUID
    site_number: str
    source_device_id: UUID
    destination_device_id: UUID
    cable_type: str
    path_points: list[dict[str, float]] = Field(default_factory=list)
    estimated_length: Optional[float] = Field(default=None, ge=0)


class Cable(BaseEntity):
    project_id: UUID
    site_number: str
    source_device_id: UUID
    destination_device_id: UUID
    cable_type: str
    path_points: list[dict[str, float]] = Field(default_factory=list)
    estimated_length: Optional[float] = Field(default=None, ge=0)


class ImportBatchCreate(BaseModel):
    source_file_name: str
    source_file_hash: str
    mode: Literal["merge", "overwrite", "append", "replace_batch"] = "merge"
    records: list[dict[str, Any]] = Field(default_factory=list)


class ImportBatch(BaseEntity):
    source_file_name: str
    source_file_hash: str
    mode: str
    status: Literal["uploaded", "validated", "committed", "quarantined", "reuploaded", "reverted"] = "uploaded"
    record_count: int = 0


class ImportBatchValidationIssue(BaseModel):
    row_index: int
    field: str
    message: str


class ImportBatchValidateResponse(BaseModel):
    batch_id: UUID
    total_rows: int
    valid_rows: int
    quarantined_rows: int
    health_score: float
    status: str
    issues: list[ImportBatchValidationIssue] = Field(default_factory=list)


class ImportDeletePreviewRequest(BaseModel):
    batch_id: UUID


class ImportDeletePreviewResponse(BaseModel):
    batch_id: UUID
    deletable_device_ids: list[UUID] = Field(default_factory=list)
    deletable_count: int = 0


class ImportDeleteCommitRequest(BaseModel):
    actor: str = "system"


class ImportDeleteCommitResponse(BaseModel):
    batch_id: UUID
    deleted_devices: int
    rollback_snapshot_id: str
    status: str


class ImportReuploadPreviewRequest(BaseModel):
    records: list[dict[str, Any]] = Field(default_factory=list)


class ImportReuploadPreviewResponse(BaseModel):
    batch_id: UUID
    old_count: int
    new_count: int
    added_count: int
    removed_count: int


class ImportReuploadCommitRequest(BaseModel):
    source_file_hash: str
    records: list[dict[str, Any]] = Field(default_factory=list)


class ImportReuploadCommitResponse(BaseModel):
    batch_id: UUID
    record_count: int
    status: str


class AsdpxPreviewRequest(BaseModel):
    source_path: str


class AsdpxDevicePreview(BaseModel):
    device_id: str
    name: str
    system_type: str
    device_task_type: str
    part_number: str
    coordinates: str
    field_notes: str


class AsdpxPreviewResponse(BaseModel):
    source_path: str
    row_count: int
    sample_rows: list[AsdpxDevicePreview]


class AsdpxBatchStageRequest(BaseModel):
    source_path: str
    mode: Literal["merge", "overwrite", "append", "replace_batch"] = "merge"


class AsdpxBatchStageResponse(BaseModel):
    batch: ImportBatch
    staged_row_count: int


class ImportBatchCommitRequest(BaseModel):
    project_id: UUID
    site_number: str
    floor_id: Optional[UUID] = None
    map_id: Optional[UUID] = None
    actor: str = "system"


class ImportBatchCommitResponse(BaseModel):
    batch_id: UUID
    committed_devices: int
    status: str


class RollbackRequest(BaseModel):
    snapshot_id: Optional[str] = None


class RollbackResult(BaseModel):
    restored_snapshot_id: str
    restored_event_id: Optional[str] = None
    restored_at: datetime = Field(default_factory=datetime.utcnow)


class Event(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    event_type: str
    entity_type: str
    entity_id: UUID
    actor: str = "system"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
