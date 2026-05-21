"""
Lifecycle API Routes

CRUD and workflow operations for sites and designs with lifecycle management.
All routes require authentication and a specific permission. The mapping
follows the Role/Permission model in `apps.api.auth`.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth_deps import Permission, perm
from .lifecycle import (
    Design, DesignCreate, DesignFilter, DesignStatus, DesignType,
    SiteExtended, SiteCreate, SiteFilter, SiteType,
    SandboxConfig, DashboardStats, SitesByType, DesignsByStatus,
    Priority, VendorStatus, DESIGN_STATUS_TRANSITIONS
)

router = APIRouter(prefix="/api/v1/lifecycle", tags=["lifecycle"])

# In-memory stores (replace with database in production)
_sites: dict[UUID, SiteExtended] = {}
_designs: dict[UUID, Design] = {}
_sandboxes: dict[UUID, SandboxConfig] = {}


# =============================================================================
# SITES
# =============================================================================

@router.post("/sites", response_model=SiteExtended, dependencies=[Depends(perm(Permission.SITE_CREATE))])
def create_site(payload: SiteCreate):
    """Create a new site."""
    site = SiteExtended(
        project_id=payload.project_id,
        site_number=payload.site_number,
        name=payload.name,
        site_type=payload.site_type,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        zip_code=payload.zip_code
    )
    _sites[site.id] = site
    return site


@router.get("/sites", response_model=List[SiteExtended], dependencies=[Depends(perm(Permission.SITE_VIEW))])
def list_sites(
    project_id: Optional[UUID] = None,
    site_type: Optional[SiteType] = None,
    search: Optional[str] = None
):
    """List sites with optional filters."""
    results = list(_sites.values())
    
    if project_id:
        results = [s for s in results if s.project_id == project_id]
    if site_type:
        results = [s for s in results if s.site_type == site_type]
    if search:
        search_lower = search.lower()
        results = [s for s in results 
                   if search_lower in s.name.lower() 
                   or search_lower in s.site_number.lower()]
    
    return results


@router.get("/sites/by-type", response_model=SitesByType, dependencies=[Depends(perm(Permission.SITE_VIEW))])
def get_sites_by_type(project_id: Optional[UUID] = None):
    """Get count of sites grouped by type."""
    sites = list(_sites.values())
    if project_id:
        sites = [s for s in sites if s.project_id == project_id]
    
    return SitesByType(
        sandbox=len([s for s in sites if s.site_type == SiteType.SANDBOX]),
        design=len([s for s in sites if s.site_type == SiteType.DESIGN]),
        installation=len([s for s in sites if s.site_type == SiteType.INSTALLATION]),
        live=len([s for s in sites if s.site_type == SiteType.LIVE]),
        archived=len([s for s in sites if s.site_type == SiteType.ARCHIVED])
    )


@router.get("/sites/{site_id}", response_model=SiteExtended, dependencies=[Depends(perm(Permission.SITE_VIEW))])
def get_site(site_id: UUID):
    """Get a specific site."""
    if site_id not in _sites:
        raise HTTPException(status_code=404, detail="Site not found")
    return _sites[site_id]


@router.patch("/sites/{site_id}/type", dependencies=[Depends(perm(Permission.SITE_TRANSITION))])
def change_site_type(site_id: UUID, new_type: SiteType, changed_by: str = "system"):
    """Change site type (lifecycle transition)."""
    if site_id not in _sites:
        raise HTTPException(status_code=404, detail="Site not found")
    
    site = _sites[site_id]
    if not site.can_transition_to(new_type):
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot transition from {site.site_type.value} to {new_type.value}"
        )
    
    # Record transition
    from .lifecycle import StatusChange
    change = StatusChange(
        from_status=site.site_type.value,
        to_status=new_type.value,
        changed_by=changed_by
    )
    site.type_history.append(change)
    site.site_type = new_type
    site.updated_at = datetime.utcnow()
    
    return {"success": True, "site_type": new_type.value}


# =============================================================================
# DESIGNS
# =============================================================================

@router.post("/designs", response_model=Design, dependencies=[Depends(perm(Permission.DESIGN_CREATE))])
def create_design(payload: DesignCreate):
    """Create a new design."""
    design = Design(
        project_id=payload.project_id,
        site_id=payload.site_id,
        name=payload.name,
        design_type=payload.design_type,
        description=payload.description,
        priority=payload.priority
    )
    _designs[design.id] = design
    return design


@router.get("/designs", response_model=List[Design], dependencies=[Depends(perm(Permission.DESIGN_VIEW))])
def list_designs(
    project_id: Optional[UUID] = None,
    site_id: Optional[UUID] = None,
    design_type: Optional[DesignType] = None,
    status: Optional[DesignStatus] = None,
    assigned_to: Optional[str] = None,
    overdue_only: bool = False
):
    """List designs with optional filters."""
    results = list(_designs.values())
    
    if project_id:
        results = [d for d in results if d.project_id == project_id]
    if site_id:
        results = [d for d in results if d.site_id == site_id]
    if design_type:
        results = [d for d in results if d.design_type == design_type]
    if status:
        results = [d for d in results if d.status == status]
    if assigned_to:
        results = [d for d in results if d.assigned_to == assigned_to]
    if overdue_only:
        now = datetime.utcnow()
        results = [d for d in results if d.due_date and d.due_date < now]
    
    return results


@router.get("/designs/by-status", response_model=DesignsByStatus, dependencies=[Depends(perm(Permission.DESIGN_VIEW))])
def get_designs_by_status(project_id: Optional[UUID] = None, site_id: Optional[UUID] = None):
    """Get count of designs grouped by status."""
    designs = list(_designs.values())
    if project_id:
        designs = [d for d in designs if d.project_id == project_id]
    if site_id:
        designs = [d for d in designs if d.site_id == site_id]
    
    return DesignsByStatus(
        draft=len([d for d in designs if d.status == DesignStatus.DRAFT]),
        submitted=len([d for d in designs if d.status == DesignStatus.SUBMITTED]),
        in_review=len([d for d in designs if d.status == DesignStatus.IN_REVIEW]),
        revision_required=len([d for d in designs if d.status == DesignStatus.REVISION_REQUIRED]),
        approved=len([d for d in designs if d.status == DesignStatus.APPROVED]),
        in_progress=len([d for d in designs if d.status == DesignStatus.IN_PROGRESS]),
        on_hold=len([d for d in designs if d.status == DesignStatus.ON_HOLD]),
        complete=len([d for d in designs if d.status == DesignStatus.COMPLETE]),
        commissioned=len([d for d in designs if d.status == DesignStatus.COMMISSIONED]),
        live=len([d for d in designs if d.status == DesignStatus.LIVE])
    )


@router.get("/designs/{design_id}", response_model=Design, dependencies=[Depends(perm(Permission.DESIGN_VIEW))])
def get_design(design_id: UUID):
    """Get a specific design."""
    if design_id not in _designs:
        raise HTTPException(status_code=404, detail="Design not found")
    return _designs[design_id]


@router.get("/designs/{design_id}/allowed-transitions", dependencies=[Depends(perm(Permission.DESIGN_VIEW))])
def get_allowed_transitions(design_id: UUID):
    """Get allowed status transitions for a design."""
    if design_id not in _designs:
        raise HTTPException(status_code=404, detail="Design not found")
    
    design = _designs[design_id]
    allowed = DESIGN_STATUS_TRANSITIONS.get(design.status, [])
    
    return {
        "current_status": design.status.value,
        "allowed_transitions": [s.value for s in allowed]
    }


@router.patch("/designs/{design_id}/status", dependencies=[Depends(perm(Permission.DESIGN_EDIT))])
def change_design_status(
    design_id: UUID, 
    new_status: DesignStatus, 
    changed_by: str = "system",
    reason: Optional[str] = None
):
    """Change design status (workflow transition)."""
    if design_id not in _designs:
        raise HTTPException(status_code=404, detail="Design not found")
    
    design = _designs[design_id]
    old_status = design.status
    
    if not design.transition_to(new_status, changed_by, reason):
        allowed = DESIGN_STATUS_TRANSITIONS.get(design.status, [])
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot transition from {old_status.value} to {new_status.value}. "
                   f"Allowed: {[s.value for s in allowed]}"
        )
    
    return {
        "success": True, 
        "old_status": old_status.value,
        "new_status": new_status.value
    }


@router.patch("/designs/{design_id}/assign", dependencies=[Depends(perm(Permission.DESIGN_EDIT))])
def assign_design(design_id: UUID, assigned_to: str):
    """Assign design to a user."""
    if design_id not in _designs:
        raise HTTPException(status_code=404, detail="Design not found")
    
    design = _designs[design_id]
    design.assigned_to = assigned_to
    design.updated_at = datetime.utcnow()
    
    return {"success": True, "assigned_to": assigned_to}


@router.patch("/designs/{design_id}/vendor", dependencies=[Depends(perm(Permission.DESIGN_EDIT))])
def assign_vendor(design_id: UUID, vendor_id: UUID, vendor_status: VendorStatus = VendorStatus.ASSIGNED):
    """Assign vendor to a design."""
    if design_id not in _designs:
        raise HTTPException(status_code=404, detail="Design not found")
    
    design = _designs[design_id]
    design.vendor_id = vendor_id
    design.vendor_status = vendor_status
    design.updated_at = datetime.utcnow()
    
    return {"success": True, "vendor_id": str(vendor_id), "vendor_status": vendor_status.value}


# =============================================================================
# SANDBOX
# =============================================================================

@router.post("/sandbox/clone/{source_site_id}", dependencies=[Depends(perm(Permission.SANDBOX_CREATE))])
def clone_to_sandbox(source_site_id: UUID, sandbox_name: str, expires_days: int = 30):
    """Clone a site to sandbox for experimentation."""
    if source_site_id not in _sites:
        raise HTTPException(status_code=404, detail="Source site not found")
    
    source = _sites[source_site_id]
    
    # Create sandbox site
    sandbox_site = SiteExtended(
        project_id=source.project_id,
        site_number=f"SB-{source.site_number}",
        name=sandbox_name,
        site_type=SiteType.SANDBOX,
        address=source.address,
        city=source.city,
        state=source.state,
        zip_code=source.zip_code
    )
    _sites[sandbox_site.id] = sandbox_site
    
    # Create sandbox config
    from datetime import timedelta
    config = SandboxConfig(
        site_id=sandbox_site.id,
        cloned_from=source_site_id,
        expires_at=datetime.utcnow() + timedelta(days=expires_days),
        purpose="clone"
    )
    _sandboxes[config.id] = config
    
    # Clone designs
    cloned_designs = []
    for design in _designs.values():
        if design.site_id == source_site_id:
            cloned = Design(
                project_id=design.project_id,
                site_id=sandbox_site.id,
                name=f"[SANDBOX] {design.name}",
                design_type=design.design_type,
                description=design.description,
                priority=design.priority,
                status=DesignStatus.DRAFT  # Reset to draft
            )
            _designs[cloned.id] = cloned
            cloned_designs.append(cloned.id)
    
    return {
        "sandbox_site": sandbox_site,
        "config": config,
        "cloned_designs": cloned_designs
    }


@router.post("/sandbox/template", dependencies=[Depends(perm(Permission.SANDBOX_TEMPLATE))])
def create_template(site_id: UUID, template_name: str):
    """Save a site as a reusable template."""
    if site_id not in _sites:
        raise HTTPException(status_code=404, detail="Site not found")
    
    config = SandboxConfig(
        site_id=site_id,
        is_template=True,
        template_name=template_name,
        purpose="template"
    )
    _sandboxes[config.id] = config
    
    return {"success": True, "template_name": template_name, "config_id": str(config.id)}


@router.get("/sandbox/templates", dependencies=[Depends(perm(Permission.DESIGN_VIEW))])
def list_templates():
    """List available templates."""
    templates = [c for c in _sandboxes.values() if c.is_template]
    return [
        {
            "config_id": str(c.id),
            "template_name": c.template_name,
            "site_id": str(c.site_id)
        }
        for c in templates
    ]


# =============================================================================
# DASHBOARD
# =============================================================================

@router.get("/dashboard/stats", response_model=DashboardStats, dependencies=[Depends(perm(Permission.SITE_VIEW))])
def get_dashboard_stats(project_id: Optional[UUID] = None):
    """Get aggregated stats for dashboard."""
    sites = list(_sites.values())
    designs = list(_designs.values())
    
    if project_id:
        sites = [s for s in sites if s.project_id == project_id]
        designs = [d for d in designs if d.project_id == project_id]
    
    now = datetime.utcnow()
    overdue = [d for d in designs if d.due_date and d.due_date < now and d.status not in [
        DesignStatus.COMPLETE, DesignStatus.COMMISSIONED, DesignStatus.LIVE, DesignStatus.ARCHIVED
    ]]
    
    pending_reviews = [d for d in designs if d.status in [
        DesignStatus.SUBMITTED, DesignStatus.IN_REVIEW
    ]]
    
    active_installations = [d for d in designs if d.status == DesignStatus.IN_PROGRESS]
    
    return DashboardStats(
        sites_by_type=SitesByType(
            sandbox=len([s for s in sites if s.site_type == SiteType.SANDBOX]),
            design=len([s for s in sites if s.site_type == SiteType.DESIGN]),
            installation=len([s for s in sites if s.site_type == SiteType.INSTALLATION]),
            live=len([s for s in sites if s.site_type == SiteType.LIVE]),
            archived=len([s for s in sites if s.site_type == SiteType.ARCHIVED])
        ),
        designs_by_status=DesignsByStatus(
            draft=len([d for d in designs if d.status == DesignStatus.DRAFT]),
            submitted=len([d for d in designs if d.status == DesignStatus.SUBMITTED]),
            in_review=len([d for d in designs if d.status == DesignStatus.IN_REVIEW]),
            revision_required=len([d for d in designs if d.status == DesignStatus.REVISION_REQUIRED]),
            approved=len([d for d in designs if d.status == DesignStatus.APPROVED]),
            in_progress=len([d for d in designs if d.status == DesignStatus.IN_PROGRESS]),
            on_hold=len([d for d in designs if d.status == DesignStatus.ON_HOLD]),
            complete=len([d for d in designs if d.status == DesignStatus.COMPLETE]),
            commissioned=len([d for d in designs if d.status == DesignStatus.COMMISSIONED]),
            live=len([d for d in designs if d.status == DesignStatus.LIVE])
        ),
        overdue_designs=len(overdue),
        pending_reviews=len(pending_reviews),
        active_installations=len(active_installations)
    )
