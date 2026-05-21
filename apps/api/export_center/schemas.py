from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

ExportType = Literal[
    "project-package",
    "siteowl",
    "gis",
    "cad",
    "qa-package",
    "executive-report",
]

ExportMode = Literal[
    "basic",
    "siteowl_compatibility",
    "cad",
    "gis",
    "executive_report",
    "field_install_package",
    "qa_package",
    "full_project_intelligence_package",
]


class MetadataSearchFilter(BaseModel):
    field: str
    op: Literal["eq", "contains", "lt", "lte", "gt", "gte", "in", "is_null"] = "eq"
    value: Any = None


class MetadataSearchRequest(BaseModel):
    entity_types: list[str] = Field(default_factory=list)
    filters: list[MetadataSearchFilter] = Field(default_factory=list)
    limit: int = Field(default=200, ge=1, le=5000)


class MetadataSearchResponse(BaseModel):
    total: int
    results: list[dict[str, Any]]


class ExportRequest(BaseModel):
    project_id: UUID
    created_by: str = "system"
    export_mode: ExportMode = "full_project_intelligence_package"
    formats: list[str] = Field(default_factory=lambda: ["zip"])
    include_raw_files: bool = True
    include_validation_history: bool = True
    include_ai_suggestions: bool = True
    include_audit_log: bool = True
    include_coordinate_transforms: bool = True
    floor_ids: list[UUID] = Field(default_factory=list)
    zone_ids: list[UUID] = Field(default_factory=list)
    device_status: Optional[str] = None
    override_risk: bool = False
    override_reason: Optional[str] = None


class ExportResult(BaseModel):
    export_id: str
    export_type: ExportType
    created_at: datetime
    output_files: list[str]
    manifest_path: str
    package_path: Optional[str] = None
    blocked: bool = False
    block_reason: Optional[str] = None


class ExportHistoryRecord(BaseModel):
    export_id: str
    project_id: str
    site_number: str
    export_type: ExportType
    export_mode: str
    created_by: str
    created_at: datetime
    app_version: str = "1.0.0"
    schema_version: str = "2026.05"
    files_included: list[str] = Field(default_factory=list)
    record_counts: dict[str, int] = Field(default_factory=dict)
    validation_score: float = 100.0
    coordinate_confidence: float = 100.0
    rollback_available: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
