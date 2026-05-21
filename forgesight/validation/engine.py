from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ValidationCategory(str, Enum):
    SCHEMA = "schema"
    REQUIRED_FIELDS = "required_fields"
    COORDINATE = "coordinate"
    DEVICE = "device"
    CABLE = "cable"
    ZONE = "zone"
    DUPLICATE = "duplicate"
    IMPORT = "import"
    EXPORT = "export"


class ValidationFinding(BaseModel):
    severity: ValidationSeverity
    category: ValidationCategory
    field: str
    record_id: Optional[str] = None
    message: str
    technical_reason: str
    suggested_fix: str
    autofix_eligible: bool = False
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    source_evidence: dict[str, Any] = Field(default_factory=dict)


class ValidationSummary(BaseModel):
    findings: list[ValidationFinding] = Field(default_factory=list)
    design_health_score: float = 100.0
    validation_score: float = 100.0
    coordinate_confidence_score: float = 100.0
    zone_coverage_score: float = 100.0
    cable_health_score: float = 100.0
    metadata_completeness_score: float = 100.0
    export_readiness_score: float = 100.0
    ai_confidence_score: float = 85.0


def _score_from_findings(findings: list[ValidationFinding], base: float = 100.0) -> float:
    penalties = {
        ValidationSeverity.CRITICAL: 35,
        ValidationSeverity.HIGH: 20,
        ValidationSeverity.MEDIUM: 10,
        ValidationSeverity.LOW: 3,
        ValidationSeverity.INFO: 0,
    }
    total_penalty = sum(penalties[x.severity] for x in findings)
    return max(0.0, round(base - total_penalty, 2))


def _device_findings(devices: list[Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    seen = set()

    for d in devices:
        key = (str(d.project_id), d.site_number, d.device_type.strip().lower(), round(d.local_x, 2), round(d.local_y, 2))
        if key in seen:
            findings.append(
                ValidationFinding(
                    severity=ValidationSeverity.MEDIUM,
                    category=ValidationCategory.DUPLICATE,
                    field="device",
                    record_id=str(d.id),
                    message="Potential duplicate device at same coordinates/type.",
                    technical_reason="Fingerprint collision on project/site/type/local_x/local_y",
                    suggested_fix="Review duplicate and merge/remove if accidental.",
                    confidence_score=0.88,
                    source_evidence={"fingerprint": key},
                )
            )
        seen.add(key)

        if d.local_x < 0 or d.local_y < 0:
            findings.append(
                ValidationFinding(
                    severity=ValidationSeverity.HIGH,
                    category=ValidationCategory.COORDINATE,
                    field="local_x/local_y",
                    record_id=str(d.id),
                    message="Device has negative coordinate(s).",
                    technical_reason="local_x/local_y must be non-negative in current map space",
                    suggested_fix="Recalibrate map scale/rotation and re-place the device.",
                    confidence_score=1.0,
                    source_evidence={"local_x": d.local_x, "local_y": d.local_y},
                )
            )

        if not d.name or not d.name.strip():
            findings.append(
                ValidationFinding(
                    severity=ValidationSeverity.HIGH,
                    category=ValidationCategory.REQUIRED_FIELDS,
                    field="name",
                    record_id=str(d.id),
                    message="Device name is missing.",
                    technical_reason="Name is mandatory for install/QA/export traceability",
                    suggested_fix="Provide a deterministic naming convention (e.g., CAM-GROCERY-01).",
                    confidence_score=1.0,
                    source_evidence={},
                )
            )

    return findings


def _cable_findings(cables: list[Any], devices_by_id: dict[UUID, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    for c in cables:
        src = devices_by_id.get(c.source_device_id)
        dst = devices_by_id.get(c.destination_device_id)
        if src is None or dst is None:
            findings.append(
                ValidationFinding(
                    severity=ValidationSeverity.CRITICAL,
                    category=ValidationCategory.CABLE,
                    field="source_device_id/destination_device_id",
                    record_id=str(c.id),
                    message="Cable references missing device(s).",
                    technical_reason="Foreign reference not resolvable in in-memory design graph",
                    suggested_fix="Reconnect cable endpoints to existing devices.",
                    confidence_score=1.0,
                    source_evidence={"source_device_id": str(c.source_device_id), "destination_device_id": str(c.destination_device_id)},
                )
            )

        if c.estimated_length is not None and c.estimated_length < 0:
            findings.append(
                ValidationFinding(
                    severity=ValidationSeverity.HIGH,
                    category=ValidationCategory.CABLE,
                    field="estimated_length",
                    record_id=str(c.id),
                    message="Cable estimated length is negative.",
                    technical_reason="Length must be >= 0",
                    suggested_fix="Recompute route geometry and estimated length.",
                    confidence_score=1.0,
                    source_evidence={"estimated_length": c.estimated_length},
                )
            )

    return findings


def _zone_findings(zones: list[Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    for z in zones:
        points = getattr(z, "points", None) or []
        if len(points) < 3:
            findings.append(
                ValidationFinding(
                    severity=ValidationSeverity.MEDIUM,
                    category=ValidationCategory.ZONE,
                    field="points",
                    record_id=str(z.id),
                    message="Zone polygon has fewer than 3 points.",
                    technical_reason="A valid polygon requires at least 3 points",
                    suggested_fix="Redraw zone boundary with at least 3 vertices.",
                    confidence_score=1.0,
                    source_evidence={"points_count": len(points)},
                )
            )

    return findings


def run_design_validation(*, devices: list[Any], cables: list[Any], zones: list[Any]) -> ValidationSummary:
    findings: list[ValidationFinding] = []
    findings.extend(_device_findings(devices))

    devices_by_id = {d.id: d for d in devices}
    findings.extend(_cable_findings(cables, devices_by_id))
    findings.extend(_zone_findings(zones))

    validation_score = _score_from_findings(findings)

    coord_related = [x for x in findings if x.category == ValidationCategory.COORDINATE]
    cable_related = [x for x in findings if x.category == ValidationCategory.CABLE]
    zone_related = [x for x in findings if x.category == ValidationCategory.ZONE]
    req_related = [x for x in findings if x.category == ValidationCategory.REQUIRED_FIELDS]

    coordinate_confidence_score = _score_from_findings(coord_related)
    cable_health_score = _score_from_findings(cable_related)
    zone_coverage_score = _score_from_findings(zone_related)
    metadata_completeness_score = _score_from_findings(req_related)

    critical_count = len([x for x in findings if x.severity == ValidationSeverity.CRITICAL])
    export_readiness_score = max(0.0, round(validation_score - (critical_count * 10), 2))
    ai_confidence_score = max(0.0, round(90 - (len(findings) * 1.5), 2))

    return ValidationSummary(
        findings=findings,
        design_health_score=validation_score,
        validation_score=validation_score,
        coordinate_confidence_score=coordinate_confidence_score,
        zone_coverage_score=zone_coverage_score,
        cable_health_score=cable_health_score,
        metadata_completeness_score=metadata_completeness_score,
        export_readiness_score=export_readiness_score,
        ai_confidence_score=ai_confidence_score,
    )
