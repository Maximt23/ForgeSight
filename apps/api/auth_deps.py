"""
Auth dependency helpers — reusable Depends() factories.

Centralizes auth wiring so routes can declare permissions via a clean,
DRY syntax:

    @app.post(
        "/sites",
        dependencies=[Depends(perm(Permission.SITE_CREATE))],
    )
    def create_site(...): ...

This pattern avoids changing every route's function signature when adding
auth — the dependency runs first, raises 401/403 if unauthorized, then
hands off to the route handler.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

from typing import Callable

from fastapi import Depends

from .auth import (
    AuthConfig,
    Permission,
    Role,
    WalmartUser,
    get_current_user,
    require_any_role,
    require_permission,
    require_role,
)

__all__ = [
    "AuthConfig",
    "Permission",
    "Role",
    "WalmartUser",
    "auth_required",
    "perm",
    "role",
    "any_role",
]


# ─── Aliases that read nicely in route decorators ──────────────────────


def perm(permission: Permission) -> Callable:
    """Shorthand for `require_permission(...)` used in `dependencies=[]`."""
    return require_permission(permission)


def role(r: Role) -> Callable:
    """Shorthand for `require_role(...)` used in `dependencies=[]`."""
    return require_role(r)


def any_role(*roles: Role) -> Callable:
    """Shorthand for `require_any_role(...)` used in `dependencies=[]`."""
    return require_any_role(*roles)


def auth_required() -> Callable:
    """Just require authentication, no specific permission. Returns the user.

    Useful for routes that need to know WHO is making the call (for audit
    logging) but don't care about specific permissions.
    """
    return get_current_user


# ─── Module-level user context injection ───────────────────────────────


async def set_user_context(user: WalmartUser = Depends(get_current_user)) -> WalmartUser:
    """Dependency that captures the current user in request-scoped logging context.

    Add to a router as a baseline dependency to attach user_id to every log
    line for the duration of the request.
    """
    from .middleware import user_id_ctx

    user_id_ctx.set(user.employee_id or user.email or user.id)
    return user
