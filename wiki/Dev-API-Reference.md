# 📡 API Reference

Complete REST API documentation for CadOwl.

---

## Base URL

```
Development: http://localhost:9010
Production:  https://cadowl.walmart.com
```

## Authentication

All endpoints (except `/auth/*` and `/api/v1/health`) require authentication.

```bash
Authorization: Bearer <jwt_token>
```

---

## Health & Status

### Health Check

```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "ok",
  "service": "cadowl-api",
  "phase": "phase1-json-store",
  "tracked_entities": {
    "projects": 5,
    "sites": 42,
    "floors": 86,
    "devices": 1247
  }
}
```

---

## Sites

### Create Site

```http
POST /api/v1/sites
Content-Type: application/json

{
  "project_id": "uuid",
  "site_number": "1234",
  "name": "Store 1234 - Bentonville",
  "site_type": "design",
  "address": "123 Main St",
  "city": "Bentonville",
  "state": "AR",
  "zip_code": "72712"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "site_number": "1234",
  "name": "Store 1234 - Bentonville",
  "site_type": "design",
  "created_at": "2026-05-21T10:00:00Z",
  ...
}
```

### List Sites

```http
GET /api/v1/sites?project_id=uuid&site_type=design&search=bentonville
```

**Query Parameters:**
| Parameter | Type | Description |
|:----------|:-----|:------------|
| project_id | uuid | Filter by project |
| site_type | string | Filter by type (sandbox, design, installation, live, archived) |
| search | string | Search name/number |

### Get Site

```http
GET /api/v1/sites/{site_id}
```

### Change Site Type

```http
PATCH /api/v1/sites/{site_id}/type
Content-Type: application/json

{
  "new_type": "installation",
  "changed_by": "pm@walmart.com",
  "reason": "Vendor assigned, ready for installation"
}
```

### Get Sites by Type

```http
GET /api/v1/sites/by-type?project_id=uuid
```

**Response:**
```json
{
  "sandbox": 3,
  "design": 12,
  "installation": 5,
  "live": 42,
  "archived": 8
}
```

---

## Designs

### Create Design

```http
POST /api/v1/designs
Content-Type: application/json

{
  "project_id": "uuid",
  "site_id": "uuid",
  "name": "CCTV Upgrade Phase 1",
  "design_type": "cctv",
  "priority": "high",
  "description": "Add 15 cameras to grocery section"
}
```

### List Designs

```http
GET /api/v1/designs?site_id=uuid&status=in_review&assigned_to=user@walmart.com
```

**Query Parameters:**
| Parameter | Type | Description |
|:----------|:-----|:------------|
| project_id | uuid | Filter by project |
| site_id | uuid | Filter by site |
| design_type | string | cctv, fire_alarm, intrusion, etc. |
| status | string | draft, submitted, in_review, approved, etc. |
| assigned_to | string | Filter by assignee email |
| overdue_only | boolean | Only show overdue designs |

### Get Design

```http
GET /api/v1/designs/{design_id}
```

### Change Design Status

```http
PATCH /api/v1/designs/{design_id}/status
Content-Type: application/json

{
  "new_status": "approved",
  "changed_by": "pm@walmart.com",
  "reason": "Meets all requirements"
}
```

### Get Allowed Transitions

```http
GET /api/v1/designs/{design_id}/allowed-transitions
```

**Response:**
```json
{
  "current_status": "in_review",
  "allowed_transitions": ["approved", "rejected", "revision_required"]
}
```

### Assign Design

```http
PATCH /api/v1/designs/{design_id}/assign
Content-Type: application/json

{
  "assigned_to": "designer@walmart.com"
}
```

### Assign Vendor

```http
PATCH /api/v1/designs/{design_id}/vendor
Content-Type: application/json

{
  "vendor_id": "uuid",
  "vendor_status": "assigned"
}
```

---

## Sandbox

### Clone Site to Sandbox

```http
POST /api/v1/sandbox/clone/{source_site_id}
Content-Type: application/json

{
  "sandbox_name": "Test New Layout",
  "expires_days": 30
}
```

**Response:**
```json
{
  "sandbox_site": { ... },
  "config": { ... },
  "cloned_designs": ["uuid1", "uuid2"]
}
```

### Create Template

```http
POST /api/v1/sandbox/template
Content-Type: application/json

{
  "site_id": "uuid",
  "template_name": "Standard Supercenter Layout"
}
```

### List Templates

```http
GET /api/v1/sandbox/templates
```

---

## Dashboard

### Get Dashboard Stats

```http
GET /api/v1/dashboard/stats?project_id=uuid
```

**Response:**
```json
{
  "sites_by_type": {
    "sandbox": 3,
    "design": 12,
    "installation": 5,
    "live": 42,
    "archived": 8
  },
  "designs_by_status": {
    "draft": 15,
    "submitted": 8,
    "in_review": 4,
    "approved": 10,
    "in_progress": 6,
    "complete": 3,
    "live": 25
  },
  "overdue_designs": 2,
  "pending_reviews": 12,
  "active_installations": 6
}
```

---

## Devices

### Create Device

```http
POST /api/v1/devices
Content-Type: application/json

{
  "project_id": "uuid",
  "site_number": "1234",
  "floor_id": "uuid",
  "device_type": "dome_camera",
  "name": "CAM_ENTRANCE_01",
  "local_x": 45.2,
  "local_y": 32.1
}
```

### List Devices

```http
GET /api/v1/devices?site_number=1234&device_type=dome_camera
```

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Cannot transition from draft to approved. Allowed: ['submitted']"
}
```

### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden

```json
{
  "detail": "Role 'reviewer' required"
}
```

### 404 Not Found

```json
{
  "detail": "Site not found"
}
```

---

## Related

- [Authentication](Dev-Authentication.md)
- [Architecture](Dev-Architecture.md)
- [Quick Start](Quick-Start.md)
