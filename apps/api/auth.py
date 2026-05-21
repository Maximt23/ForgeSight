"""
Walmart SSO Authentication Module

Integrates with Walmart's Microsoft Entra ID (Azure AD) for Single Sign-On.
Uses OIDC/OAuth2 for authentication and JWT validation.

Configuration:
    Set these environment variables:
    - WALMART_TENANT_ID: Azure AD tenant ID
    - WALMART_CLIENT_ID: Application client ID
    - WALMART_CLIENT_SECRET: Application client secret (for backend)
    - WALMART_REDIRECT_URI: OAuth redirect URI

Usage:
    from apps.api.auth import get_current_user, require_role
    
    @app.get("/protected")
    async def protected_route(user: WalmartUser = Depends(get_current_user)):
        return {"message": f"Hello {user.display_name}"}
    
    @app.get("/admin-only")
    async def admin_route(user: WalmartUser = Depends(require_role("admin"))):
        return {"message": "Admin access granted"}
"""

import os
import json
import time
import httpx
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError


# =============================================================================
# CONFIGURATION
# =============================================================================

class AuthConfig:
    """Authentication configuration from environment."""
    
    # Walmart Azure AD settings
    TENANT_ID = os.getenv("WALMART_TENANT_ID", "3cbcc3d3-094d-4006-9849-0d11d61f484d")
    CLIENT_ID = os.getenv("WALMART_CLIENT_ID", "cadowl-app")
    CLIENT_SECRET = os.getenv("WALMART_CLIENT_SECRET", "")
    REDIRECT_URI = os.getenv("WALMART_REDIRECT_URI", "http://localhost:8000/auth/callback")
    
    # Microsoft Entra ID endpoints
    AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
    AUTHORIZE_URL = f"{AUTHORITY}/oauth2/v2.0/authorize"
    TOKEN_URL = f"{AUTHORITY}/oauth2/v2.0/token"
    JWKS_URL = f"{AUTHORITY}/discovery/v2.0/keys"
    USERINFO_URL = "https://graph.microsoft.com/v1.0/me"
    
    # JWT validation
    ALGORITHMS = ["RS256"]
    AUDIENCE = CLIENT_ID
    ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
    
    # Session settings
    SESSION_EXPIRE_MINUTES = 480  # 8 hours
    REFRESH_BEFORE_EXPIRE_MINUTES = 30
    
    # Development mode (skip SSO for local testing)
    DEV_MODE = os.getenv("CADOWL_DEV_MODE", "false").lower() == "true"
    DEV_USER = os.getenv("CADOWL_DEV_USER", "dev.user@walmart.com")


# =============================================================================
# ENUMS & MODELS
# =============================================================================

class Role(str, Enum):
    """User roles for authorization."""
    VIEWER = "viewer"           # Read-only access
    DESIGNER = "designer"       # Create/edit designs
    REVIEWER = "reviewer"       # Approve/reject designs
    INSTALLER = "installer"     # Update installation status
    PM = "pm"                   # Program manager - full access
    ADMIN = "admin"             # System administrator


class Permission(str, Enum):
    """Granular permissions."""
    # Sites
    SITE_VIEW = "site:view"
    SITE_CREATE = "site:create"
    SITE_EDIT = "site:edit"
    SITE_DELETE = "site:delete"
    SITE_TRANSITION = "site:transition"
    
    # Designs
    DESIGN_VIEW = "design:view"
    DESIGN_CREATE = "design:create"
    DESIGN_EDIT = "design:edit"
    DESIGN_DELETE = "design:delete"
    DESIGN_SUBMIT = "design:submit"
    DESIGN_REVIEW = "design:review"
    DESIGN_APPROVE = "design:approve"
    DESIGN_REJECT = "design:reject"
    
    # Sandbox
    SANDBOX_CREATE = "sandbox:create"
    SANDBOX_TEMPLATE = "sandbox:template"
    
    # Admin
    ADMIN_USERS = "admin:users"
    ADMIN_SETTINGS = "admin:settings"


# Role -> Permissions mapping
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.VIEWER: [
        Permission.SITE_VIEW,
        Permission.DESIGN_VIEW,
    ],
    Role.DESIGNER: [
        Permission.SITE_VIEW,
        Permission.SITE_CREATE,
        Permission.DESIGN_VIEW,
        Permission.DESIGN_CREATE,
        Permission.DESIGN_EDIT,
        Permission.DESIGN_SUBMIT,
        Permission.SANDBOX_CREATE,
    ],
    Role.REVIEWER: [
        Permission.SITE_VIEW,
        Permission.DESIGN_VIEW,
        Permission.DESIGN_REVIEW,
        Permission.DESIGN_APPROVE,
        Permission.DESIGN_REJECT,
    ],
    Role.INSTALLER: [
        Permission.SITE_VIEW,
        Permission.DESIGN_VIEW,
        Permission.DESIGN_EDIT,  # Limited to installation fields
    ],
    Role.PM: [
        Permission.SITE_VIEW,
        Permission.SITE_CREATE,
        Permission.SITE_EDIT,
        Permission.SITE_TRANSITION,
        Permission.DESIGN_VIEW,
        Permission.DESIGN_CREATE,
        Permission.DESIGN_EDIT,
        Permission.DESIGN_DELETE,
        Permission.DESIGN_SUBMIT,
        Permission.DESIGN_REVIEW,
        Permission.DESIGN_APPROVE,
        Permission.DESIGN_REJECT,
        Permission.SANDBOX_CREATE,
        Permission.SANDBOX_TEMPLATE,
    ],
    Role.ADMIN: list(Permission),  # All permissions
}


class WalmartUser(BaseModel):
    """Authenticated Walmart user."""
    id: str                           # Azure AD object ID
    email: str                        # user@walmart.com
    display_name: str                 # Full name
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    employee_id: Optional[str] = None  # WIN ID (e.g., vn59j7j)
    
    # Authorization
    roles: List[Role] = field(default_factory=lambda: [Role.VIEWER])
    permissions: List[Permission] = field(default_factory=list)
    
    # Session
    token_expires_at: Optional[datetime] = None
    
    @property
    def is_admin(self) -> bool:
        return Role.ADMIN in self.roles
    
    @property
    def is_pm(self) -> bool:
        return Role.PM in self.roles or self.is_admin
    
    def has_role(self, role: Role) -> bool:
        return role in self.roles or self.is_admin
    
    def has_permission(self, permission: Permission) -> bool:
        if self.is_admin:
            return True
        return permission in self.permissions or any(
            permission in ROLE_PERMISSIONS.get(role, [])
            for role in self.roles
        )
    
    def get_all_permissions(self) -> List[Permission]:
        """Get all permissions from roles."""
        perms = set(self.permissions)
        for role in self.roles:
            perms.update(ROLE_PERMISSIONS.get(role, []))
        return list(perms)


class TokenData(BaseModel):
    """Decoded JWT token data."""
    sub: str                    # Subject (user ID)
    email: Optional[str] = None
    name: Optional[str] = None
    preferred_username: Optional[str] = None
    oid: Optional[str] = None   # Azure AD object ID
    tid: Optional[str] = None   # Tenant ID
    exp: Optional[int] = None   # Expiration timestamp
    roles: List[str] = []       # Azure AD app roles


# =============================================================================
# AUTH SERVICES
# =============================================================================

class JWKSCache:
    """Cache for Azure AD public keys."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._keys: Dict[str, Any] = {}
        self._fetched_at: Optional[float] = None
    
    async def get_keys(self) -> Dict[str, Any]:
        """Get JWKS, fetching if needed."""
        now = time.time()
        if self._fetched_at is None or (now - self._fetched_at) > self.ttl_seconds:
            await self._fetch_keys()
        return self._keys
    
    async def _fetch_keys(self):
        """Fetch JWKS from Azure AD."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(AuthConfig.JWKS_URL)
                response.raise_for_status()
                jwks = response.json()
                self._keys = {key["kid"]: key for key in jwks.get("keys", [])}
                self._fetched_at = time.time()
        except Exception as e:
            if not self._keys:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Failed to fetch JWKS: {str(e)}"
                )


# Global JWKS cache
_jwks_cache = JWKSCache()

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


async def validate_token(token: str) -> TokenData:
    """Validate JWT token from Azure AD."""
    try:
        # Get the key ID from token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise JWTError("No key ID in token header")
        
        # Get public key from JWKS
        keys = await _jwks_cache.get_keys()
        if kid not in keys:
            # Refresh cache and try again
            await _jwks_cache._fetch_keys()
            keys = await _jwks_cache.get_keys()
        
        if kid not in keys:
            raise JWTError(f"Key ID {kid} not found in JWKS")
        
        # Decode and validate token
        payload = jwt.decode(
            token,
            keys[kid],
            algorithms=AuthConfig.ALGORITHMS,
            audience=AuthConfig.AUDIENCE,
            issuer=AuthConfig.ISSUER
        )
        
        return TokenData(
            sub=payload.get("sub"),
            email=payload.get("email") or payload.get("preferred_username"),
            name=payload.get("name"),
            preferred_username=payload.get("preferred_username"),
            oid=payload.get("oid"),
            tid=payload.get("tid"),
            exp=payload.get("exp"),
            roles=payload.get("roles", [])
        )
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


def _get_dev_user() -> WalmartUser:
    """Get development user for local testing."""
    return WalmartUser(
        id="dev-user-001",
        email=AuthConfig.DEV_USER,
        display_name="Development User",
        first_name="Dev",
        last_name="User",
        employee_id="devuser",
        roles=[Role.ADMIN],  # Full access in dev mode
        permissions=list(Permission)
    )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> WalmartUser:
    """
    Get the current authenticated user from the request.
    
    In DEV_MODE, returns a mock user for local testing.
    In production, validates the Azure AD JWT token.
    """
    # Development mode bypass
    if AuthConfig.DEV_MODE:
        return _get_dev_user()
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Validate token
    token_data = await validate_token(credentials.credentials)
    
    # Map Azure AD roles to app roles
    roles = []
    for azure_role in token_data.roles:
        try:
            roles.append(Role(azure_role.lower()))
        except ValueError:
            pass  # Unknown role, ignore
    
    if not roles:
        roles = [Role.VIEWER]  # Default role
    
    # Build user object
    user = WalmartUser(
        id=token_data.oid or token_data.sub,
        email=token_data.email or "",
        display_name=token_data.name or token_data.email or "Unknown",
        roles=roles
    )
    
    return user


def require_role(role: Role) -> Callable:
    """Dependency that requires a specific role."""
    async def role_checker(user: WalmartUser = Depends(get_current_user)) -> WalmartUser:
        if not user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role.value}' required"
            )
        return user
    return role_checker


def require_permission(permission: Permission) -> Callable:
    """Dependency that requires a specific permission."""
    async def permission_checker(user: WalmartUser = Depends(get_current_user)) -> WalmartUser:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission.value}' required"
            )
        return user
    return permission_checker


def require_any_role(*roles: Role) -> Callable:
    """Dependency that requires any of the specified roles."""
    async def role_checker(user: WalmartUser = Depends(get_current_user)) -> WalmartUser:
        if not any(user.has_role(role) for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {[r.value for r in roles]}"
            )
        return user
    return role_checker


# =============================================================================
# AUTH ROUTES
# =============================================================================

from fastapi import APIRouter

auth_router = APIRouter(prefix="/auth", tags=["authentication"])


@auth_router.get("/login")
async def login():
    """Redirect to Walmart SSO login."""
    if AuthConfig.DEV_MODE:
        return {"message": "DEV_MODE enabled, no SSO required", "user": _get_dev_user().model_dump()}
    
    # Build OAuth2 authorization URL
    params = {
        "client_id": AuthConfig.CLIENT_ID,
        "response_type": "code",
        "redirect_uri": AuthConfig.REDIRECT_URI,
        "scope": "openid profile email",
        "response_mode": "query"
    }
    
    url = f"{AuthConfig.AUTHORIZE_URL}?" + "&".join(f"{k}={v}" for k, v in params.items())
    
    return {"login_url": url}


@auth_router.get("/callback")
async def auth_callback(code: str):
    """Handle OAuth2 callback from Azure AD."""
    if AuthConfig.DEV_MODE:
        return {"access_token": "dev-token", "user": _get_dev_user().model_dump()}
    
    # Exchange code for token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            AuthConfig.TOKEN_URL,
            data={
                "client_id": AuthConfig.CLIENT_ID,
                "client_secret": AuthConfig.CLIENT_SECRET,
                "code": code,
                "redirect_uri": AuthConfig.REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to exchange code for token"
            )
        
        tokens = response.json()
        
        return {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "expires_in": tokens.get("expires_in"),
            "token_type": tokens.get("token_type", "Bearer")
        }


@auth_router.get("/me")
async def get_me(user: WalmartUser = Depends(get_current_user)):
    """Get current user info."""
    return {
        "user": user.model_dump(),
        "permissions": [p.value for p in user.get_all_permissions()]
    }


@auth_router.get("/check-permission/{permission}")
async def check_permission(permission: str, user: WalmartUser = Depends(get_current_user)):
    """Check if current user has a permission."""
    try:
        perm = Permission(permission)
        return {"permission": permission, "allowed": user.has_permission(perm)}
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown permission: {permission}")
