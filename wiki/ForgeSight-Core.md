# ⚡ ForgeSight Core

> **API/Data Platform**

The backbone of the ForgeSight ecosystem providing REST APIs, authentication, and data persistence.

---

## Overview

ForgeSight Core is the central API platform that:

- Authenticates users via Walmart SSO
- Manages sites, designs, and devices
- Enforces workflow rules
- Provides audit logging

---

## API Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTS                                   │
│   Web Dashboard │ CLI Tools │ VIVE XR │ Mobile App │ Partners   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API GATEWAY                                   │
│              FastAPI + Walmart SSO (Azure AD)                    │
├─────────────────────────────────────────────────────────────────┤
│  /auth/*   │  /api/v1/sites/*  │  /api/v1/designs/*  │  ...    │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Lifecycle     │  │   CAD Import    │  │   Grid/Match    │
│   Service       │  │   Service       │  │   Service       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                 │
│   PostgreSQL (entities) + Redis (cache) + S3 (files)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Authentication

### Walmart SSO

ForgeSight uses Microsoft Entra ID (Azure AD) for authentication:

```python
from forgesight.core.auth import get_current_user, require_role, Role

@app.get("/api/v1/protected")
async def protected(user = Depends(get_current_user)):
    return {"hello": user.display_name}

@app.post("/api/v1/designs/{id}/approve")
async def approve(user = Depends(require_role(Role.REVIEWER))):
    # Only reviewers/admins can approve
    pass
```

### Roles

| Role | Description |
|:-----|:------------|
| `viewer` | Read-only access |
| `designer` | Create/edit designs |
| `reviewer` | Approve/reject designs |
| `installer` | Update installation progress |
| `pm` | Program manager, broad access |
| `admin` | Full system access |

### Permissions

```python
class Permission(str, Enum):
    SITE_VIEW = "site:view"
    SITE_CREATE = "site:create"
    DESIGN_APPROVE = "design:approve"
    ADMIN_USERS = "admin:users"
    # ... 20+ permissions
```

---

## Data Model

### Entity Hierarchy

```
Project
└── Site (sandbox | design | installation | live | archived)
    └── Floor
        └── Map (floor plan)
            └── Device (camera, sensor, etc.)
            └── Zone (area boundary)
            └── Cable (device connections)
    └── Design (workflow status)
```

### Key Entities

```python
class Site:
    id: UUID
    project_id: UUID
    site_number: str      # "1234"
    name: str             # "Bentonville SC"
    site_type: SiteType   # sandbox, design, installation, live
    
class Design:
    id: UUID
    site_id: UUID
    name: str
    design_type: DesignType  # cctv, fire_alarm, intrusion
    status: DesignStatus     # draft, submitted, approved, etc.
    priority: Priority       # critical, high, normal, low
```

---

## REST API

### Quick Reference

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/sites` | GET, POST | List/create sites |
| `/api/v1/sites/{id}/type` | PATCH | Change site type |
| `/api/v1/designs` | GET, POST | List/create designs |
| `/api/v1/designs/{id}/status` | PATCH | Change status |
| `/api/v1/devices` | GET, POST | List/create devices |
| `/api/v1/dashboard/stats` | GET | Dashboard metrics |

### Example Requests

```bash
# Create site
curl -X POST http://localhost:9010/api/v1/sites \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_id": "...", "site_number": "1234", "name": "Test"}'

# Change design status
curl -X PATCH http://localhost:9010/api/v1/designs/{id}/status \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"new_status": "approved", "reason": "Looks good!"}'
```

---

## Event Sourcing

All mutations are logged for audit:

```jsonl
{"id":"a1b2c3","timestamp":"2026-05-21T10:00:00Z","entity_type":"design","entity_id":"xyz","action":"transition","actor":"pm@walmart.com","changes":{"from":"draft","to":"submitted"}}
{"id":"d4e5f6","timestamp":"2026-05-21T10:05:00Z","entity_type":"design","entity_id":"xyz","action":"transition","actor":"reviewer@walmart.com","changes":{"from":"submitted","to":"approved"}}
```

### Query Events

```bash
GET /api/v1/events?entity_type=design&entity_id=xyz&limit=100
```

---

## Configuration

### Environment Variables

```bash
# API
API_PORT=9010
API_HOST=0.0.0.0

# Authentication
WALMART_TENANT_ID=3cbcc3d3-...
WALMART_CLIENT_ID=forgesight-app
FORGESIGHT_DEV_MODE=true  # Local dev only

# Database
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Storage
FORGESIGHT_DATA_DIR=./data/lifecycle
```

---

## Running Locally

```bash
# Start API server
uv run uvicorn forgesight.core.main:app --port 9010 --reload

# Run with dev mode (no SSO)
FORGESIGHT_DEV_MODE=true uv run uvicorn forgesight.core.main:app --port 9010
```

---

## Related

- [API Reference](Dev-API-Reference.md) — Full endpoint docs
- [Authentication](Dev-Authentication.md) — SSO details
- [Architecture](Dev-Architecture.md) — System design
