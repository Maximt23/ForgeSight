from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from forgesight.validation import ValidationSummary, run_design_validation

from .auth_deps import Permission, perm
from .store import STORE


class ValidationRunRequest(BaseModel):
    project_id: Optional[UUID] = None
    site_number: Optional[str] = None


class ValidationAutoFixPreview(BaseModel):
    safe_fixes: list[str] = Field(default_factory=list)


router = APIRouter(prefix="/api/v1/validation", tags=["validation"])


@router.post("/run", response_model=ValidationSummary, dependencies=[Depends(perm(Permission.DESIGN_VIEW))])
def run_validation(payload: ValidationRunRequest):
    devices = list(STORE.devices.values())
    cables = list(STORE.cables.values())
    zones = list(STORE.zones.values())

    if payload.project_id:
        devices = [x for x in devices if x.project_id == payload.project_id]
        cables = [x for x in cables if x.project_id == payload.project_id]
        zones = [x for x in zones if x.project_id == payload.project_id]

    if payload.site_number:
        devices = [x for x in devices if x.site_number == payload.site_number]
        cables = [x for x in cables if x.site_number == payload.site_number]

    summary = run_design_validation(devices=devices, cables=cables, zones=zones)

    STORE._event(
        "validation_run",
        "validation",
        uuid4(),
        metadata={
            "project_id": str(payload.project_id) if payload.project_id else None,
            "site_number": payload.site_number,
            "findings": len(summary.findings),
            "validation_score": summary.validation_score,
        },
    )

    return summary


@router.post("/autofix/preview", response_model=ValidationAutoFixPreview, dependencies=[Depends(perm(Permission.DESIGN_EDIT))])
def preview_autofix(payload: ValidationRunRequest):
    summary = run_validation(payload)

    fixes: list[str] = []
    for finding in summary.findings:
        if finding.autofix_eligible:
            fixes.append(f"{finding.record_id or 'record'}: {finding.suggested_fix}")

    return ValidationAutoFixPreview(safe_fixes=fixes)
