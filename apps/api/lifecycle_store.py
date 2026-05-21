"""
Lifecycle Data Store

Persistent JSON-based storage for sites, designs, and sandbox configs.
Thread-safe with event logging for audit trail.

Usage:
    from apps.api.lifecycle_store import lifecycle_store
    
    # Create a site
    site = lifecycle_store.create_site(site_data, user="maxim@walmart.com")
    
    # Get designs by status
    designs = lifecycle_store.list_designs(status=DesignStatus.IN_REVIEW)
"""

import json
import os
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel

from .lifecycle import (
    Design, DesignCreate, DesignStatus, DesignType,
    SiteExtended, SiteCreate, SiteType,
    SandboxConfig, StatusChange, Priority, VendorStatus,
    DESIGN_STATUS_TRANSITIONS, SITE_TYPE_TRANSITIONS
)


class LifecycleEvent(BaseModel):
    """Audit event for lifecycle changes."""
    id: str
    timestamp: str
    entity_type: str  # "site", "design", "sandbox"
    entity_id: str
    action: str       # "create", "update", "delete", "transition"
    actor: str        # User who performed action
    changes: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


class LifecycleStore:
    """
    Persistent storage for lifecycle entities.
    
    Stores data in JSON files with append-only event log.
    Thread-safe for concurrent access.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(os.getenv(
            "CADOWL_DATA_DIR", 
            "C:/MAXILLM/CadOwl/data/lifecycle"
        ))
        self._lock = RLock()
        
        # In-memory caches
        self._sites: Dict[str, SiteExtended] = {}
        self._designs: Dict[str, Design] = {}
        self._sandboxes: Dict[str, SandboxConfig] = {}
        self._events: List[LifecycleEvent] = []
        
        # Initialize storage
        self._ensure_storage()
        self._load_all()
    
    # =========================================================================
    # STORAGE MANAGEMENT
    # =========================================================================
    
    def _ensure_storage(self):
        """Create storage directories and files if needed."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        files = ["sites.json", "designs.json", "sandboxes.json"]
        for fname in files:
            fpath = self.base_dir / fname
            if not fpath.exists():
                fpath.write_text("[]", encoding="utf-8")
        
        # Event log (JSONL format)
        events_path = self.base_dir / "events.jsonl"
        if not events_path.exists():
            events_path.touch()
    
    def _read_json(self, filename: str) -> list:
        """Read JSON array from file."""
        fpath = self.base_dir / filename
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _write_json(self, filename: str, data: list):
        """Write JSON array to file."""
        fpath = self.base_dir / filename
        fpath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    
    def _append_event(self, event: LifecycleEvent):
        """Append event to log."""
        fpath = self.base_dir / "events.jsonl"
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.model_dump(), default=str) + "\n")
        self._events.append(event)
    
    def _load_all(self):
        """Load all entities from storage."""
        with self._lock:
            # Load sites
            for data in self._read_json("sites.json"):
                try:
                    site = SiteExtended.model_validate(data)
                    self._sites[str(site.id)] = site
                except Exception:
                    pass
            
            # Load designs
            for data in self._read_json("designs.json"):
                try:
                    design = Design.model_validate(data)
                    self._designs[str(design.id)] = design
                except Exception:
                    pass
            
            # Load sandboxes
            for data in self._read_json("sandboxes.json"):
                try:
                    sandbox = SandboxConfig.model_validate(data)
                    self._sandboxes[str(sandbox.id)] = sandbox
                except Exception:
                    pass
            
            # Load events
            events_path = self.base_dir / "events.jsonl"
            if events_path.exists():
                for line in events_path.read_text(encoding="utf-8").strip().split("\n"):
                    if line:
                        try:
                            self._events.append(LifecycleEvent.model_validate(json.loads(line)))
                        except Exception:
                            pass
    
    def _persist_sites(self):
        """Persist sites to storage."""
        data = [s.model_dump(mode="json") for s in self._sites.values()]
        self._write_json("sites.json", data)
    
    def _persist_designs(self):
        """Persist designs to storage."""
        data = [d.model_dump(mode="json") for d in self._designs.values()]
        self._write_json("designs.json", data)
    
    def _persist_sandboxes(self):
        """Persist sandboxes to storage."""
        data = [s.model_dump(mode="json") for s in self._sandboxes.values()]
        self._write_json("sandboxes.json", data)
    
    def _log_event(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        actor: str,
        changes: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ):
        """Log an audit event."""
        from uuid import uuid4
        event = LifecycleEvent(
            id=str(uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor=actor,
            changes=changes or {},
            metadata=metadata or {}
        )
        self._append_event(event)
    
    # =========================================================================
    # SITES
    # =========================================================================
    
    def create_site(self, payload: SiteCreate, user: str = "system") -> SiteExtended:
        """Create a new site."""
        with self._lock:
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
            self._sites[str(site.id)] = site
            self._persist_sites()
            self._log_event("site", str(site.id), "create", user, 
                           {"site_type": site.site_type.value})
            return site
    
    def get_site(self, site_id: str) -> Optional[SiteExtended]:
        """Get a site by ID."""
        return self._sites.get(str(site_id))
    
    def list_sites(
        self,
        project_id: Optional[str] = None,
        site_type: Optional[SiteType] = None,
        search: Optional[str] = None
    ) -> List[SiteExtended]:
        """List sites with optional filters."""
        results = list(self._sites.values())
        
        if project_id:
            results = [s for s in results if str(s.project_id) == str(project_id)]
        if site_type:
            results = [s for s in results if s.site_type == site_type]
        if search:
            search_lower = search.lower()
            results = [s for s in results 
                      if search_lower in s.name.lower() 
                      or search_lower in s.site_number.lower()]
        
        return results
    
    def transition_site(
        self,
        site_id: str,
        new_type: SiteType,
        user: str,
        reason: str = None
    ) -> SiteExtended:
        """Transition site to new type."""
        with self._lock:
            site = self._sites.get(str(site_id))
            if not site:
                raise ValueError(f"Site not found: {site_id}")
            
            if not site.can_transition_to(new_type):
                allowed = SITE_TYPE_TRANSITIONS.get(site.site_type, [])
                raise ValueError(
                    f"Cannot transition from {site.site_type.value} to {new_type.value}. "
                    f"Allowed: {[t.value for t in allowed]}"
                )
            
            old_type = site.site_type
            
            # Record change
            change = StatusChange(
                from_status=old_type.value,
                to_status=new_type.value,
                changed_by=user,
                reason=reason
            )
            site.type_history.append(change)
            site.site_type = new_type
            site.updated_at = datetime.utcnow()
            
            self._persist_sites()
            self._log_event("site", str(site_id), "transition", user,
                           {"from": old_type.value, "to": new_type.value, "reason": reason})
            
            return site
    
    def update_site(self, site_id: str, updates: Dict[str, Any], user: str) -> SiteExtended:
        """Update site fields."""
        with self._lock:
            site = self._sites.get(str(site_id))
            if not site:
                raise ValueError(f"Site not found: {site_id}")
            
            changes = {}
            for key, value in updates.items():
                if hasattr(site, key) and key not in ["id", "created_at", "type_history"]:
                    old_value = getattr(site, key)
                    if old_value != value:
                        changes[key] = {"old": old_value, "new": value}
                        setattr(site, key, value)
            
            if changes:
                site.updated_at = datetime.utcnow()
                self._persist_sites()
                self._log_event("site", str(site_id), "update", user, changes)
            
            return site
    
    # =========================================================================
    # DESIGNS
    # =========================================================================
    
    def create_design(self, payload: DesignCreate, user: str = "system") -> Design:
        """Create a new design."""
        with self._lock:
            design = Design(
                project_id=payload.project_id,
                site_id=payload.site_id,
                name=payload.name,
                design_type=payload.design_type,
                description=payload.description,
                priority=payload.priority,
                created_by=user
            )
            self._designs[str(design.id)] = design
            self._persist_designs()
            self._log_event("design", str(design.id), "create", user,
                           {"design_type": design.design_type.value})
            return design
    
    def get_design(self, design_id: str) -> Optional[Design]:
        """Get a design by ID."""
        return self._designs.get(str(design_id))
    
    def list_designs(
        self,
        project_id: Optional[str] = None,
        site_id: Optional[str] = None,
        design_type: Optional[DesignType] = None,
        status: Optional[DesignStatus] = None,
        assigned_to: Optional[str] = None,
        vendor_id: Optional[str] = None,
        overdue_only: bool = False
    ) -> List[Design]:
        """List designs with optional filters."""
        results = list(self._designs.values())
        
        if project_id:
            results = [d for d in results if str(d.project_id) == str(project_id)]
        if site_id:
            results = [d for d in results if str(d.site_id) == str(site_id)]
        if design_type:
            results = [d for d in results if d.design_type == design_type]
        if status:
            results = [d for d in results if d.status == status]
        if assigned_to:
            results = [d for d in results if d.assigned_to == assigned_to]
        if vendor_id:
            results = [d for d in results if str(d.vendor_id) == str(vendor_id)]
        if overdue_only:
            now = datetime.utcnow()
            results = [d for d in results if d.due_date and d.due_date < now]
        
        return results
    
    def transition_design(
        self,
        design_id: str,
        new_status: DesignStatus,
        user: str,
        reason: str = None
    ) -> Design:
        """Transition design to new status."""
        with self._lock:
            design = self._designs.get(str(design_id))
            if not design:
                raise ValueError(f"Design not found: {design_id}")
            
            old_status = design.status
            
            if not design.transition_to(new_status, user, reason):
                allowed = DESIGN_STATUS_TRANSITIONS.get(design.status, [])
                raise ValueError(
                    f"Cannot transition from {old_status.value} to {new_status.value}. "
                    f"Allowed: {[s.value for s in allowed]}"
                )
            
            self._persist_designs()
            self._log_event("design", str(design_id), "transition", user,
                           {"from": old_status.value, "to": new_status.value, "reason": reason})
            
            return design
    
    def assign_design(self, design_id: str, assigned_to: str, user: str) -> Design:
        """Assign design to a user."""
        with self._lock:
            design = self._designs.get(str(design_id))
            if not design:
                raise ValueError(f"Design not found: {design_id}")
            
            old_assignee = design.assigned_to
            design.assigned_to = assigned_to
            design.updated_at = datetime.utcnow()
            
            self._persist_designs()
            self._log_event("design", str(design_id), "assign", user,
                           {"from": old_assignee, "to": assigned_to})
            
            return design
    
    def assign_vendor(
        self,
        design_id: str,
        vendor_id: str,
        vendor_status: VendorStatus,
        user: str
    ) -> Design:
        """Assign vendor to a design."""
        with self._lock:
            design = self._designs.get(str(design_id))
            if not design:
                raise ValueError(f"Design not found: {design_id}")
            
            from uuid import UUID
            design.vendor_id = UUID(vendor_id)
            design.vendor_status = vendor_status
            design.updated_at = datetime.utcnow()
            
            self._persist_designs()
            self._log_event("design", str(design_id), "vendor_assign", user,
                           {"vendor_id": vendor_id, "vendor_status": vendor_status.value})
            
            return design
    
    # =========================================================================
    # SANDBOX
    # =========================================================================
    
    def create_sandbox(
        self,
        source_site_id: str,
        sandbox_name: str,
        user: str,
        expires_days: int = 30
    ) -> Dict[str, Any]:
        """Clone a site to sandbox."""
        with self._lock:
            source = self._sites.get(str(source_site_id))
            if not source:
                raise ValueError(f"Source site not found: {source_site_id}")
            
            # Create sandbox site
            from uuid import uuid4
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
            self._sites[str(sandbox_site.id)] = sandbox_site
            
            # Create config
            from datetime import timedelta
            config = SandboxConfig(
                site_id=sandbox_site.id,
                cloned_from=UUID(source_site_id),
                expires_at=datetime.utcnow() + timedelta(days=expires_days),
                purpose="clone"
            )
            self._sandboxes[str(config.id)] = config
            
            # Clone designs
            cloned_designs = []
            for design in self._designs.values():
                if str(design.site_id) == str(source_site_id):
                    cloned = Design(
                        project_id=design.project_id,
                        site_id=sandbox_site.id,
                        name=f"[SANDBOX] {design.name}",
                        design_type=design.design_type,
                        description=design.description,
                        priority=design.priority,
                        status=DesignStatus.DRAFT,
                        created_by=user
                    )
                    self._designs[str(cloned.id)] = cloned
                    cloned_designs.append(str(cloned.id))
            
            self._persist_sites()
            self._persist_designs()
            self._persist_sandboxes()
            
            self._log_event("sandbox", str(config.id), "create", user,
                           {"source_site": source_site_id, "cloned_designs": len(cloned_designs)})
            
            return {
                "sandbox_site": sandbox_site,
                "config": config,
                "cloned_designs": cloned_designs
            }
    
    def list_templates(self) -> List[SandboxConfig]:
        """List sandbox templates."""
        return [s for s in self._sandboxes.values() if s.is_template]
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def get_stats(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Get aggregated statistics."""
        sites = self.list_sites(project_id=project_id)
        designs = self.list_designs(project_id=project_id)
        
        now = datetime.utcnow()
        
        return {
            "sites_by_type": {
                "sandbox": len([s for s in sites if s.site_type == SiteType.SANDBOX]),
                "design": len([s for s in sites if s.site_type == SiteType.DESIGN]),
                "installation": len([s for s in sites if s.site_type == SiteType.INSTALLATION]),
                "live": len([s for s in sites if s.site_type == SiteType.LIVE]),
                "archived": len([s for s in sites if s.site_type == SiteType.ARCHIVED])
            },
            "designs_by_status": {
                "draft": len([d for d in designs if d.status == DesignStatus.DRAFT]),
                "submitted": len([d for d in designs if d.status == DesignStatus.SUBMITTED]),
                "in_review": len([d for d in designs if d.status == DesignStatus.IN_REVIEW]),
                "approved": len([d for d in designs if d.status == DesignStatus.APPROVED]),
                "in_progress": len([d for d in designs if d.status == DesignStatus.IN_PROGRESS]),
                "complete": len([d for d in designs if d.status == DesignStatus.COMPLETE]),
                "live": len([d for d in designs if d.status == DesignStatus.LIVE])
            },
            "overdue_designs": len([d for d in designs 
                                   if d.due_date and d.due_date < now 
                                   and d.status not in [DesignStatus.COMPLETE, DesignStatus.LIVE]]),
            "pending_reviews": len([d for d in designs 
                                   if d.status in [DesignStatus.SUBMITTED, DesignStatus.IN_REVIEW]]),
            "active_installations": len([d for d in designs 
                                        if d.status == DesignStatus.IN_PROGRESS])
        }
    
    def get_events(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 100
    ) -> List[LifecycleEvent]:
        """Get audit events."""
        events = self._events
        
        if entity_type:
            events = [e for e in events if e.entity_type == entity_type]
        if entity_id:
            events = [e for e in events if e.entity_id == str(entity_id)]
        
        return list(reversed(events[-limit:]))


# Global store instance
lifecycle_store = LifecycleStore()
