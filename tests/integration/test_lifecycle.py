"""
Lifecycle Integration Tests

Tests for site/design lifecycle workflows including:
- Site type transitions
- Design status workflows
- SSO/permission enforcement
- Sandbox cloning
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from pathlib import Path
import tempfile
import shutil

# Import modules under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.api.lifecycle import (
    Design, DesignCreate, DesignStatus, DesignType,
    SiteExtended, SiteCreate, SiteType,
    SandboxConfig, Priority, VendorStatus,
    DESIGN_STATUS_TRANSITIONS, SITE_TYPE_TRANSITIONS
)
from apps.api.auth import (
    WalmartUser, Role, Permission, ROLE_PERMISSIONS
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_data_dir():
    """Create temporary data directory for tests."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def lifecycle_store(temp_data_dir):
    """Create lifecycle store with temp directory."""
    from apps.api.lifecycle_store import LifecycleStore
    return LifecycleStore(base_dir=temp_data_dir)


@pytest.fixture
def sample_project_id():
    """Sample project UUID."""
    return uuid4()


@pytest.fixture
def designer_user():
    """User with designer role."""
    return WalmartUser(
        id="user-001",
        email="designer@walmart.com",
        display_name="Test Designer",
        roles=[Role.DESIGNER]
    )


@pytest.fixture
def reviewer_user():
    """User with reviewer role."""
    return WalmartUser(
        id="user-002",
        email="reviewer@walmart.com",
        display_name="Test Reviewer",
        roles=[Role.REVIEWER]
    )


@pytest.fixture
def pm_user():
    """User with PM role."""
    return WalmartUser(
        id="user-003",
        email="pm@walmart.com",
        display_name="Test PM",
        roles=[Role.PM]
    )


@pytest.fixture
def admin_user():
    """User with admin role."""
    return WalmartUser(
        id="user-004",
        email="admin@walmart.com",
        display_name="Test Admin",
        roles=[Role.ADMIN]
    )


# =============================================================================
# SITE LIFECYCLE TESTS
# =============================================================================

class TestSiteLifecycle:
    """Tests for site type transitions."""
    
    def test_create_site_default_type(self, lifecycle_store, sample_project_id):
        """New sites default to DESIGN type."""
        payload = SiteCreate(
            project_id=sample_project_id,
            site_number="1234",
            name="Test Store"
        )
        site = lifecycle_store.create_site(payload, user="test@walmart.com")
        
        assert site.site_type == SiteType.DESIGN
        assert site.site_number == "1234"
        assert site.name == "Test Store"
    
    def test_create_sandbox_site(self, lifecycle_store, sample_project_id):
        """Can create sandbox sites directly."""
        payload = SiteCreate(
            project_id=sample_project_id,
            site_number="SB-TEST",
            name="Sandbox Test",
            site_type=SiteType.SANDBOX
        )
        site = lifecycle_store.create_site(payload, user="test@walmart.com")
        
        assert site.site_type == SiteType.SANDBOX
    
    def test_site_transition_design_to_installation(self, lifecycle_store, sample_project_id):
        """Design sites can transition to installation."""
        payload = SiteCreate(
            project_id=sample_project_id,
            site_number="1234",
            name="Test Store"
        )
        site = lifecycle_store.create_site(payload, user="test@walmart.com")
        
        site = lifecycle_store.transition_site(
            str(site.id),
            SiteType.INSTALLATION,
            user="pm@walmart.com",
            reason="Installation vendor assigned"
        )
        
        assert site.site_type == SiteType.INSTALLATION
        assert len(site.type_history) == 1
        assert site.type_history[0].from_status == "design"
        assert site.type_history[0].to_status == "installation"
    
    def test_site_transition_installation_to_live(self, lifecycle_store, sample_project_id):
        """Installation sites can go live."""
        payload = SiteCreate(
            project_id=sample_project_id,
            site_number="1234",
            name="Test Store"
        )
        site = lifecycle_store.create_site(payload)
        site = lifecycle_store.transition_site(str(site.id), SiteType.INSTALLATION, "pm")
        site = lifecycle_store.transition_site(str(site.id), SiteType.LIVE, "pm")
        
        assert site.site_type == SiteType.LIVE
        assert len(site.type_history) == 2
    
    def test_invalid_site_transition(self, lifecycle_store, sample_project_id):
        """Cannot skip lifecycle phases."""
        payload = SiteCreate(
            project_id=sample_project_id,
            site_number="1234",
            name="Test Store"
        )
        site = lifecycle_store.create_site(payload)
        
        # Cannot go directly from DESIGN to LIVE
        with pytest.raises(ValueError) as exc_info:
            lifecycle_store.transition_site(str(site.id), SiteType.LIVE, "user")
        
        assert "Cannot transition" in str(exc_info.value)
    
    def test_sandbox_can_transition_to_design(self, lifecycle_store, sample_project_id):
        """Sandbox sites can be promoted to design."""
        payload = SiteCreate(
            project_id=sample_project_id,
            site_number="SB-1234",
            name="Prototype",
            site_type=SiteType.SANDBOX
        )
        site = lifecycle_store.create_site(payload)
        site = lifecycle_store.transition_site(str(site.id), SiteType.DESIGN, "pm")
        
        assert site.site_type == SiteType.DESIGN


# =============================================================================
# DESIGN WORKFLOW TESTS
# =============================================================================

class TestDesignWorkflow:
    """Tests for design status transitions."""
    
    def test_create_design_draft_status(self, lifecycle_store, sample_project_id):
        """New designs start in DRAFT status."""
        site_payload = SiteCreate(
            project_id=sample_project_id,
            site_number="1234",
            name="Test Store"
        )
        site = lifecycle_store.create_site(site_payload)
        
        design_payload = DesignCreate(
            project_id=sample_project_id,
            site_id=site.id,
            name="CCTV Design v1",
            design_type=DesignType.CCTV
        )
        design = lifecycle_store.create_design(design_payload, user="designer@walmart.com")
        
        assert design.status == DesignStatus.DRAFT
        assert design.design_type == DesignType.CCTV
        assert design.created_by == "designer@walmart.com"
    
    def test_full_design_approval_workflow(self, lifecycle_store, sample_project_id):
        """Test complete approval workflow: draft -> submitted -> review -> approved."""
        # Setup
        site = lifecycle_store.create_site(SiteCreate(
            project_id=sample_project_id,
            site_number="1234",
            name="Test"
        ))
        design = lifecycle_store.create_design(DesignCreate(
            project_id=sample_project_id,
            site_id=site.id,
            name="Test Design",
            design_type=DesignType.CCTV
        ))
        
        # Designer submits
        design = lifecycle_store.transition_design(
            str(design.id), 
            DesignStatus.SUBMITTED,
            user="designer@walmart.com"
        )
        assert design.status == DesignStatus.SUBMITTED
        assert design.submitted_at is not None
        
        # Reviewer reviews
        design = lifecycle_store.transition_design(
            str(design.id),
            DesignStatus.IN_REVIEW,
            user="reviewer@walmart.com"
        )
        assert design.status == DesignStatus.IN_REVIEW
        
        # Reviewer approves
        design = lifecycle_store.transition_design(
            str(design.id),
            DesignStatus.APPROVED,
            user="reviewer@walmart.com"
        )
        assert design.status == DesignStatus.APPROVED
        assert design.approved_at is not None
    
    def test_design_revision_workflow(self, lifecycle_store, sample_project_id):
        """Test revision request workflow."""
        site = lifecycle_store.create_site(SiteCreate(
            project_id=sample_project_id,
            site_number="1234",
            name="Test"
        ))
        design = lifecycle_store.create_design(DesignCreate(
            project_id=sample_project_id,
            site_id=site.id,
            name="Test Design",
            design_type=DesignType.FIRE_ALARM
        ))
        
        # Submit
        design = lifecycle_store.transition_design(str(design.id), DesignStatus.SUBMITTED, "designer")
        
        # Request revision
        design = lifecycle_store.transition_design(
            str(design.id),
            DesignStatus.REVISION_REQUIRED,
            user="reviewer@walmart.com",
            reason="Missing smoke detectors in back room"
        )
        assert design.status == DesignStatus.REVISION_REQUIRED
        
        # Resubmit
        design = lifecycle_store.transition_design(str(design.id), DesignStatus.SUBMITTED, "designer")
        assert design.status == DesignStatus.SUBMITTED
    
    def test_installation_workflow(self, lifecycle_store, sample_project_id):
        """Test installation workflow: approved -> in_progress -> complete -> commissioned."""
        site = lifecycle_store.create_site(SiteCreate(
            project_id=sample_project_id,
            site_number="1234",
            name="Test"
        ))
        design = lifecycle_store.create_design(DesignCreate(
            project_id=sample_project_id,
            site_id=site.id,
            name="Test Design",
            design_type=DesignType.INTEGRATED
        ))
        
        # Get to approved
        lifecycle_store.transition_design(str(design.id), DesignStatus.SUBMITTED, "designer")
        lifecycle_store.transition_design(str(design.id), DesignStatus.IN_REVIEW, "reviewer")
        lifecycle_store.transition_design(str(design.id), DesignStatus.APPROVED, "reviewer")
        
        # Installation starts
        design = lifecycle_store.transition_design(
            str(design.id),
            DesignStatus.IN_PROGRESS,
            user="installer@walmart.com"
        )
        assert design.status == DesignStatus.IN_PROGRESS
        
        # Installation complete
        design = lifecycle_store.transition_design(str(design.id), DesignStatus.COMPLETE, "installer")
        assert design.status == DesignStatus.COMPLETE
        
        # Commissioning
        design = lifecycle_store.transition_design(str(design.id), DesignStatus.COMMISSIONED, "pm")
        assert design.status == DesignStatus.COMMISSIONED
        
        # Go live
        design = lifecycle_store.transition_design(str(design.id), DesignStatus.LIVE, "pm")
        assert design.status == DesignStatus.LIVE
        assert design.completed_at is not None
    
    def test_invalid_status_transition(self, lifecycle_store, sample_project_id):
        """Cannot skip workflow steps."""
        site = lifecycle_store.create_site(SiteCreate(
            project_id=sample_project_id,
            site_number="1234",
            name="Test"
        ))
        design = lifecycle_store.create_design(DesignCreate(
            project_id=sample_project_id,
            site_id=site.id,
            name="Test Design",
            design_type=DesignType.CCTV
        ))
        
        # Cannot go directly from DRAFT to APPROVED
        with pytest.raises(ValueError) as exc_info:
            lifecycle_store.transition_design(str(design.id), DesignStatus.APPROVED, "user")
        
        assert "Cannot transition" in str(exc_info.value)


# =============================================================================
# PERMISSION TESTS
# =============================================================================

class TestPermissions:
    """Tests for role-based permissions."""
    
    def test_designer_permissions(self, designer_user):
        """Designers can create and edit designs."""
        assert designer_user.has_permission(Permission.DESIGN_CREATE)
        assert designer_user.has_permission(Permission.DESIGN_EDIT)
        assert designer_user.has_permission(Permission.DESIGN_SUBMIT)
        assert not designer_user.has_permission(Permission.DESIGN_APPROVE)
        assert not designer_user.has_permission(Permission.ADMIN_USERS)
    
    def test_reviewer_permissions(self, reviewer_user):
        """Reviewers can approve/reject but not create."""
        assert reviewer_user.has_permission(Permission.DESIGN_VIEW)
        assert reviewer_user.has_permission(Permission.DESIGN_REVIEW)
        assert reviewer_user.has_permission(Permission.DESIGN_APPROVE)
        assert reviewer_user.has_permission(Permission.DESIGN_REJECT)
        assert not reviewer_user.has_permission(Permission.DESIGN_CREATE)
    
    def test_pm_permissions(self, pm_user):
        """PMs have broad access."""
        assert pm_user.has_permission(Permission.SITE_CREATE)
        assert pm_user.has_permission(Permission.SITE_TRANSITION)
        assert pm_user.has_permission(Permission.DESIGN_CREATE)
        assert pm_user.has_permission(Permission.DESIGN_APPROVE)
        assert pm_user.has_permission(Permission.SANDBOX_TEMPLATE)
        assert not pm_user.has_permission(Permission.ADMIN_USERS)
    
    def test_admin_has_all_permissions(self, admin_user):
        """Admins have all permissions."""
        for permission in Permission:
            assert admin_user.has_permission(permission)
    
    def test_role_check(self, designer_user, pm_user):
        """Role checks work correctly."""
        assert designer_user.has_role(Role.DESIGNER)
        assert not designer_user.has_role(Role.PM)
        assert pm_user.has_role(Role.PM)
        assert not pm_user.is_admin


# =============================================================================
# SANDBOX TESTS
# =============================================================================

class TestSandbox:
    """Tests for sandbox functionality."""
    
    def test_clone_site_to_sandbox(self, lifecycle_store, sample_project_id):
        """Can clone a site to sandbox."""
        # Create source site with designs
        site = lifecycle_store.create_site(SiteCreate(
            project_id=sample_project_id,
            site_number="1234",
            name="Production Store"
        ))
        design1 = lifecycle_store.create_design(DesignCreate(
            project_id=sample_project_id,
            site_id=site.id,
            name="CCTV Design",
            design_type=DesignType.CCTV
        ))
        design2 = lifecycle_store.create_design(DesignCreate(
            project_id=sample_project_id,
            site_id=site.id,
            name="Fire Alarm Design",
            design_type=DesignType.FIRE_ALARM
        ))
        
        # Clone to sandbox
        result = lifecycle_store.create_sandbox(
            str(site.id),
            "Test Clone",
            user="designer@walmart.com",
            expires_days=7
        )
        
        assert result["sandbox_site"].site_type == SiteType.SANDBOX
        assert result["sandbox_site"].site_number == f"SB-{site.site_number}"
        assert len(result["cloned_designs"]) == 2
        
        # Verify cloned designs are in DRAFT
        for design_id in result["cloned_designs"]:
            design = lifecycle_store.get_design(design_id)
            assert design.status == DesignStatus.DRAFT
            assert "[SANDBOX]" in design.name


# =============================================================================
# AUDIT TRAIL TESTS
# =============================================================================

class TestAuditTrail:
    """Tests for event logging."""
    
    def test_events_logged_on_create(self, lifecycle_store, sample_project_id):
        """Creating entities logs events."""
        site = lifecycle_store.create_site(SiteCreate(
            project_id=sample_project_id,
            site_number="1234",
            name="Test"
        ), user="test@walmart.com")
        
        events = lifecycle_store.get_events(entity_id=str(site.id))
        assert len(events) == 1
        assert events[0].action == "create"
        assert events[0].actor == "test@walmart.com"
    
    def test_events_logged_on_transition(self, lifecycle_store, sample_project_id):
        """Transitions log events with details."""
        site = lifecycle_store.create_site(SiteCreate(
            project_id=sample_project_id,
            site_number="1234",
            name="Test"
        ))
        lifecycle_store.transition_site(
            str(site.id),
            SiteType.INSTALLATION,
            user="pm@walmart.com",
            reason="Vendor ready"
        )
        
        events = lifecycle_store.get_events(entity_id=str(site.id))
        assert len(events) == 2
        
        transition_event = events[0]  # Most recent first
        assert transition_event.action == "transition"
        assert transition_event.changes["from"] == "design"
        assert transition_event.changes["to"] == "installation"
        assert transition_event.changes["reason"] == "Vendor ready"


# =============================================================================
# STATISTICS TESTS
# =============================================================================

class TestStatistics:
    """Tests for dashboard statistics."""
    
    def test_get_stats(self, lifecycle_store, sample_project_id):
        """Stats aggregation works correctly."""
        # Create mix of sites and designs
        for i in range(3):
            site = lifecycle_store.create_site(SiteCreate(
                project_id=sample_project_id,
                site_number=f"100{i}",
                name=f"Store {i}"
            ))
            lifecycle_store.create_design(DesignCreate(
                project_id=sample_project_id,
                site_id=site.id,
                name=f"Design {i}",
                design_type=DesignType.CCTV
            ))
        
        # Add a sandbox
        lifecycle_store.create_site(SiteCreate(
            project_id=sample_project_id,
            site_number="SB-001",
            name="Sandbox",
            site_type=SiteType.SANDBOX
        ))
        
        stats = lifecycle_store.get_stats()
        
        assert stats["sites_by_type"]["design"] == 3
        assert stats["sites_by_type"]["sandbox"] == 1
        assert stats["designs_by_status"]["draft"] == 3


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
