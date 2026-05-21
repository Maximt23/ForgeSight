"""
Site & Design Lifecycle Enums and Models

Defines the lifecycle states, types, and statuses for sites and designs.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class SiteType(str, Enum):
    """Type/phase of a site in its lifecycle."""
    SANDBOX = "sandbox"           # Testing, prototyping, training
    DESIGN = "design"             # Active design/planning phase
    INSTALLATION = "installation" # Being built/installed
    LIVE = "live"                 # Operational site
    ARCHIVED = "archived"         # Historical/closed


class DesignType(str, Enum):
    """Type of security design/system."""
    CCTV = "cctv"                 # Video surveillance
    FIRE_ALARM = "fire_alarm"     # Fire detection & notification
    INTRUSION = "intrusion"       # Burglar alarm, motion sensors
    ACCESS_CONTROL = "access_control"  # Card readers, doors
    INTEGRATED = "integrated"     # All security systems
    NETWORK = "network"           # Infrastructure (IDF, cabling)
    AUDIO_VISUAL = "audio_visual" # PVM, speakers, intercoms


class DesignStatus(str, Enum):
    """Status of a design in the approval workflow."""
    DRAFT = "draft"                       # Initial creation
    SUBMITTED = "submitted"               # Sent for review
    IN_REVIEW = "in_review"               # Being reviewed
    REVISION_REQUIRED = "revision_required"  # Needs changes
    REJECTED = "rejected"                 # Not approved
    APPROVED = "approved"                 # Ready to build
    IN_PROGRESS = "in_progress"           # Being installed
    ON_HOLD = "on_hold"                   # Paused
    COMPLETE = "complete"                 # Installation done
    COMMISSIONED = "commissioned"         # Tested & verified
    LIVE = "live"                         # In production
    ARCHIVED = "archived"                 # Closed/historical


class Priority(str, Enum):
    """Priority level for designs/tasks."""
    CRITICAL = "critical"   # Urgent, drop everything
    HIGH = "high"           # Important, prioritize
    NORMAL = "normal"       # Standard priority
    LOW = "low"             # When time permits
    BACKLOG = "backlog"     # Future consideration


class VendorStatus(str, Enum):
    """Status of vendor assignment."""
    UNASSIGNED = "unassigned"
    ASSIGNED = "assigned"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


# =============================================================================
# STATUS TRANSITIONS (Workflow Rules)
# =============================================================================

DESIGN_STATUS_TRANSITIONS: Dict[DesignStatus, List[DesignStatus]] = {
    DesignStatus.DRAFT: [DesignStatus.SUBMITTED],
    DesignStatus.SUBMITTED: [DesignStatus.IN_REVIEW, DesignStatus.REVISION_REQUIRED],
    DesignStatus.IN_REVIEW: [DesignStatus.APPROVED, DesignStatus.REJECTED, DesignStatus.REVISION_REQUIRED],
    DesignStatus.REVISION_REQUIRED: [DesignStatus.SUBMITTED],
    DesignStatus.REJECTED: [],  # Terminal state (can clone to new draft)
    DesignStatus.APPROVED: [DesignStatus.IN_PROGRESS],
    DesignStatus.IN_PROGRESS: [DesignStatus.COMPLETE, DesignStatus.ON_HOLD],
    DesignStatus.ON_HOLD: [DesignStatus.IN_PROGRESS],
    DesignStatus.COMPLETE: [DesignStatus.COMMISSIONED],
    DesignStatus.COMMISSIONED: [DesignStatus.LIVE],
    DesignStatus.LIVE: [DesignStatus.ARCHIVED],
    DesignStatus.ARCHIVED: [],  # Terminal state
}

SITE_TYPE_TRANSITIONS: Dict[SiteType, List[SiteType]] = {
    SiteType.SANDBOX: [SiteType.DESIGN, SiteType.ARCHIVED],
    SiteType.DESIGN: [SiteType.INSTALLATION, SiteType.ARCHIVED],
    SiteType.INSTALLATION: [SiteType.LIVE, SiteType.ARCHIVED],
    SiteType.LIVE: [SiteType.ARCHIVED],
    SiteType.ARCHIVED: [],  # Terminal state
}


# =============================================================================
# MODELS
# =============================================================================

class StatusChange(BaseModel):
    """Record of a status change for audit trail."""
    id: UUID = Field(default_factory=uuid4)
    from_status: str
    to_status: str
    changed_by: str
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    reason: Optional[str] = None
    notes: Optional[str] = None


class DesignCreate(BaseModel):
    """Create a new design."""
    project_id: UUID
    site_id: UUID
    name: str
    design_type: DesignType
    description: Optional[str] = None
    priority: Priority = Priority.NORMAL


class Design(BaseModel):
    """A security system design for a site."""
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    site_id: UUID
    name: str
    design_type: DesignType
    status: DesignStatus = DesignStatus.DRAFT
    priority: Priority = Priority.NORMAL
    description: Optional[str] = None
    
    # Ownership
    created_by: Optional[str] = None
    assigned_to: Optional[str] = None
    reviewer: Optional[str] = None
    
    # Vendor
    vendor_id: Optional[UUID] = None
    vendor_status: VendorStatus = VendorStatus.UNASSIGNED
    
    # Dates
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Version control
    version: int = 1
    parent_design_id: Optional[UUID] = None  # For revisions
    
    # Audit
    status_history: List[StatusChange] = Field(default_factory=list)
    
    def can_transition_to(self, new_status: DesignStatus) -> bool:
        """Check if transition to new status is allowed."""
        allowed = DESIGN_STATUS_TRANSITIONS.get(self.status, [])
        return new_status in allowed
    
    def transition_to(self, new_status: DesignStatus, changed_by: str, reason: str = None) -> bool:
        """Attempt to transition to new status."""
        if not self.can_transition_to(new_status):
            return False
        
        change = StatusChange(
            from_status=self.status.value,
            to_status=new_status.value,
            changed_by=changed_by,
            reason=reason
        )
        self.status_history.append(change)
        self.status = new_status
        self.updated_at = datetime.utcnow()
        
        # Set timestamp fields
        if new_status == DesignStatus.SUBMITTED:
            self.submitted_at = datetime.utcnow()
        elif new_status == DesignStatus.APPROVED:
            self.approved_at = datetime.utcnow()
        elif new_status in [DesignStatus.COMPLETE, DesignStatus.COMMISSIONED]:
            self.completed_at = datetime.utcnow()
        
        return True


class SiteCreate(BaseModel):
    """Create a new site."""
    project_id: UUID
    site_number: str
    name: str
    site_type: SiteType = SiteType.DESIGN
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


class SiteExtended(BaseModel):
    """Extended site model with lifecycle management."""
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    site_number: str
    name: str
    site_type: SiteType = SiteType.DESIGN
    
    # Location
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    # Metadata
    store_format: Optional[str] = None  # Supercenter, NHM, Sam's, etc.
    square_footage: Optional[int] = None
    
    # Dates
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    go_live_date: Optional[datetime] = None
    
    # Status tracking
    type_history: List[StatusChange] = Field(default_factory=list)
    
    # Related designs
    active_design_ids: List[UUID] = Field(default_factory=list)
    
    def can_transition_to(self, new_type: SiteType) -> bool:
        """Check if transition to new type is allowed."""
        allowed = SITE_TYPE_TRANSITIONS.get(self.site_type, [])
        return new_type in allowed


class SandboxConfig(BaseModel):
    """Configuration for sandbox sites."""
    id: UUID = Field(default_factory=uuid4)
    site_id: UUID
    
    # Sandbox settings
    is_template: bool = False
    template_name: Optional[str] = None
    cloned_from: Optional[UUID] = None  # Source site if cloned
    
    # Expiration
    expires_at: Optional[datetime] = None
    auto_archive: bool = True
    
    # Permissions
    shared_with: List[str] = Field(default_factory=list)  # User IDs
    is_public: bool = False  # Visible to all users
    
    # Purpose
    purpose: Optional[str] = None  # "training", "demo", "prototype", etc.


# =============================================================================
# FILTERS
# =============================================================================

class SiteFilter(BaseModel):
    """Filter criteria for querying sites."""
    project_id: Optional[UUID] = None
    site_type: Optional[SiteType] = None
    site_types: Optional[List[SiteType]] = None  # Multiple types
    search: Optional[str] = None  # Name/number search
    city: Optional[str] = None
    state: Optional[str] = None


class DesignFilter(BaseModel):
    """Filter criteria for querying designs."""
    project_id: Optional[UUID] = None
    site_id: Optional[UUID] = None
    design_type: Optional[DesignType] = None
    status: Optional[DesignStatus] = None
    statuses: Optional[List[DesignStatus]] = None  # Multiple statuses
    priority: Optional[Priority] = None
    assigned_to: Optional[str] = None
    vendor_id: Optional[UUID] = None
    overdue_only: bool = False


# =============================================================================
# DASHBOARD VIEWS
# =============================================================================

class SitesByType(BaseModel):
    """Count of sites by type for dashboard."""
    sandbox: int = 0
    design: int = 0
    installation: int = 0
    live: int = 0
    archived: int = 0


class DesignsByStatus(BaseModel):
    """Count of designs by status for dashboard."""
    draft: int = 0
    submitted: int = 0
    in_review: int = 0
    revision_required: int = 0
    approved: int = 0
    in_progress: int = 0
    on_hold: int = 0
    complete: int = 0
    commissioned: int = 0
    live: int = 0


class DashboardStats(BaseModel):
    """Aggregated stats for dashboard."""
    sites_by_type: SitesByType
    designs_by_status: DesignsByStatus
    overdue_designs: int = 0
    pending_reviews: int = 0
    active_installations: int = 0
