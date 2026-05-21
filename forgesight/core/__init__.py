"""
ForgeSight Core - API/Data Platform

REST API, authentication, and data persistence.

Usage:
    from forgesight.core import create_app, get_current_user
    from forgesight.core.auth import require_role, Role
    
    app = create_app()
    
    @app.get("/protected")
    async def protected(user = Depends(get_current_user)):
        return {"hello": user.display_name}
"""

from apps.api.auth import (
    get_current_user,
    require_role,
    require_permission,
    require_any_role,
    WalmartUser,
    Role,
    Permission,
    ROLE_PERMISSIONS,
    AuthConfig,
    auth_router,
)

from apps.api.lifecycle import (
    Design,
    DesignCreate,
    DesignStatus,
    DesignType,
    SiteExtended,
    SiteCreate,
    SiteType,
    SandboxConfig,
    Priority,
    VendorStatus,
    StatusChange,
    DESIGN_STATUS_TRANSITIONS,
    SITE_TYPE_TRANSITIONS,
)

from apps.api.lifecycle_store import (
    LifecycleStore,
    LifecycleEvent,
    lifecycle_store,
)


def create_app():
    """Create the ForgeSight Core FastAPI application."""
    from fastapi import FastAPI
    from apps.api.main import app as legacy_app
    from apps.api.lifecycle_routes import router as lifecycle_router
    
    app = FastAPI(
        title="ForgeSight Core",
        description="Enterprise Security Design Intelligence Platform",
        version="0.1.0"
    )
    
    # Mount routers
    app.include_router(auth_router)
    app.include_router(lifecycle_router)
    
    return app


__all__ = [
    # App factory
    "create_app",
    
    # Auth
    "get_current_user",
    "require_role",
    "require_permission",
    "require_any_role",
    "WalmartUser",
    "Role",
    "Permission",
    "ROLE_PERMISSIONS",
    "AuthConfig",
    "auth_router",
    
    # Lifecycle
    "Design",
    "DesignCreate",
    "DesignStatus",
    "DesignType",
    "SiteExtended",
    "SiteCreate",
    "SiteType",
    "SandboxConfig",
    "Priority",
    "VendorStatus",
    "StatusChange",
    "DESIGN_STATUS_TRANSITIONS",
    "SITE_TYPE_TRANSITIONS",
    
    # Store
    "LifecycleStore",
    "LifecycleEvent",
    "lifecycle_store",
]
