# 🔐 Authentication Guide

CadOwl uses Walmart's Single Sign-On (SSO) via Microsoft Entra ID (Azure AD) for authentication.

---

## Overview

```
┌──────────┐     ┌─────────────────┐     ┌─────────────┐
│  User    │────►│  CadOwl Login   │────►│  Azure AD   │
│          │     │  /auth/login    │     │  SSO        │
└──────────┘     └─────────────────┘     └──────┬──────┘
                                                │
                        ┌───────────────────────┘
                        │
                        ▼
                 ┌─────────────┐
                 │  JWT Token  │
                 │  (Bearer)   │
                 └──────┬──────┘
                        │
                        ▼
                 ┌─────────────┐
                 │  CadOwl API │
                 │  Protected  │
                 └─────────────┘
```

---

## Configuration

### Environment Variables

```bash
# .env file
WALMART_TENANT_ID=3cbcc3d3-094d-4006-9849-0d11d61f484d
WALMART_CLIENT_ID=cadowl-app
WALMART_CLIENT_SECRET=<your-secret>
WALMART_REDIRECT_URI=http://localhost:9010/auth/callback

# Development mode (bypasses SSO for local testing)
CADOWL_DEV_MODE=true
CADOWL_DEV_USER=your.name@walmart.com
```

### Azure AD App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App Registrations**
3. Create new registration:
   - Name: `CadOwl`
   - Redirect URI: `http://localhost:9010/auth/callback`
4. Note the **Application (client) ID**
5. Create a client secret under **Certificates & secrets**

---

## Authentication Flow

### 1. Initiate Login

```bash
GET /auth/login

# Response:
{
  "login_url": "https://login.microsoftonline.com/..."
}
```

Redirect user to `login_url`.

### 2. Handle Callback

After Azure AD authentication, user is redirected to:

```
/auth/callback?code=<authorization_code>
```

CadOwl exchanges the code for tokens:

```bash
GET /auth/callback?code=abc123

# Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

### 3. Use Token

Include token in all API requests:

```bash
curl -X GET http://localhost:9010/api/v1/sites \
  -H "Authorization: Bearer eyJ..."
```

---

## Roles & Permissions

### Roles

| Role | Description |
|:-----|:------------|
| `viewer` | Read-only access to all resources |
| `designer` | Create and edit designs |
| `reviewer` | Review and approve/reject designs |
| `installer` | Update installation progress |
| `pm` | Program manager, broad access |
| `admin` | Full system access |

### Permissions

```python
class Permission(str, Enum):
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
```

### Role → Permission Mapping

| Permission | Viewer | Designer | Reviewer | PM | Admin |
|:-----------|:------:|:--------:|:--------:|:--:|:-----:|
| site:view | ✅ | ✅ | ✅ | ✅ | ✅ |
| site:create | ❌ | ✅ | ❌ | ✅ | ✅ |
| design:create | ❌ | ✅ | ❌ | ✅ | ✅ |
| design:submit | ❌ | ✅ | ❌ | ✅ | ✅ |
| design:approve | ❌ | ❌ | ✅ | ✅ | ✅ |
| admin:users | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Protecting Routes

### Require Authentication

```python
from apps.api.auth import get_current_user, WalmartUser

@app.get("/api/v1/protected")
async def protected_route(user: WalmartUser = Depends(get_current_user)):
    return {"message": f"Hello {user.display_name}!"}
```

### Require Specific Role

```python
from apps.api.auth import require_role, Role

@app.post("/api/v1/designs/{id}/approve")
async def approve_design(
    id: UUID,
    user: WalmartUser = Depends(require_role(Role.REVIEWER))
):
    # Only reviewers and admins can access
    return {"approved": True}
```

### Require Specific Permission

```python
from apps.api.auth import require_permission, Permission

@app.delete("/api/v1/sites/{id}")
async def delete_site(
    id: UUID,
    user: WalmartUser = Depends(require_permission(Permission.SITE_DELETE))
):
    # Only users with site:delete permission
    return {"deleted": True}
```

### Require Any of Multiple Roles

```python
from apps.api.auth import require_any_role

@app.patch("/api/v1/designs/{id}/status")
async def change_status(
    id: UUID,
    user: WalmartUser = Depends(require_any_role(Role.PM, Role.REVIEWER))
):
    # PMs or Reviewers can change status
    return {"status": "changed"}
```

---

## Development Mode

For local development without SSO:

```bash
# .env
CADOWL_DEV_MODE=true
CADOWL_DEV_USER=dev.user@walmart.com
```

In dev mode:
- No Azure AD authentication required
- All requests authenticated as dev user
- Dev user has `admin` role (full access)

⚠️ **Never enable dev mode in production!**

---

## API Endpoints

### Login

```
GET /auth/login
```

Returns URL to redirect user for SSO login.

### Callback

```
GET /auth/callback?code=<code>
```

Exchanges authorization code for tokens.

### Current User

```
GET /auth/me
Authorization: Bearer <token>
```

Returns current user info and permissions.

### Check Permission

```
GET /auth/check-permission/{permission}
Authorization: Bearer <token>
```

Check if current user has a specific permission.

---

## Troubleshooting

### "Invalid token" Error

- Token may be expired (default: 1 hour)
- Check that `WALMART_CLIENT_ID` matches Azure AD
- Verify token was issued for correct audience

### "Permission denied" Error

- User doesn't have required role
- Check role assignments in Azure AD
- Admin can override via `ADMIN` role

### SSO Not Working

- Verify VPN/Eagle WiFi connection
- Check Azure AD app registration
- Verify redirect URI matches exactly

---

## Related

- [Architecture](Dev-Architecture.md)
- [API Reference](Dev-API-Reference.md)
- [Quick Start](Quick-Start.md)
