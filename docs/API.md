# 📡 ForgeSight API Reference

> Complete REST API surface — auto-validated by `scripts/audit` against the
> running FastAPI app. Any drift between this file and reality will trigger
> a failing audit check on the next commit.

**Base URL** (local dev): `http://localhost:9010`
**Base URL** (prod): set by Kubernetes ingress

**Authentication**: Bearer token via `Authorization: Bearer <jwt>` header.
Set `CADOWL_DEV_MODE=true` for development bypass with a mock user.

**Permission model**: every route declares a required `Permission` enum
value via `dependencies=[Depends(perm(...))]`. See `apps/api/auth.py` for
the full role → permission mapping.

---

## 🩺 Health & Observability

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/health` | none | Liveness probe — returns `{"status":"ok"}` |
| GET | `/metrics` | none | Prometheus metrics scrape endpoint |

---

## 📁 Core Resources (v1)

### Projects
| Method | Path | Permission | Body | Returns |
|--------|------|------------|------|---------|
| GET | `/api/v1/projects` | `PROJECT_VIEW` | — | `list[Project]` |
| POST | `/api/v1/projects` | `PROJECT_CREATE` | `ProjectCreate` | `Project` |

### Sites (basic CRUD)
| Method | Path | Permission | Body | Returns |
|--------|------|------------|------|---------|
| GET | `/api/v1/sites` | `SITE_VIEW` | — | `list[Site]` |
| POST | `/api/v1/sites` | `SITE_CREATE` | `SiteCreate` | `Site` |

For extended site lifecycle (status transitions, history, type changes),
see [Lifecycle / Sites](#lifecycle--sites) below.

### Floors
| Method | Path | Permission | Body | Returns |
|--------|------|------------|------|---------|
| GET | `/api/v1/floors` | `FLOOR_VIEW` | — | `list[Floor]` |
| POST | `/api/v1/floors` | `FLOOR_CREATE` | `FloorCreate` | `Floor` |

### Maps
| Method | Path | Permission | Body | Returns |
|--------|------|------------|------|---------|
| GET | `/api/v1/maps` | `MAP_VIEW` | — | `list[MapModel]` |
| POST | `/api/v1/maps` | `MAP_CREATE` | `MapCreate` | `MapModel` |

### Devices
| Method | Path | Permission | Body | Returns |
|--------|------|------------|------|---------|
| GET | `/api/v1/devices` | `DEVICE_VIEW` | — | `list[Device]` |
| POST | `/api/v1/devices` | `DEVICE_CREATE` | `DeviceCreate` | `Device` |

### Zones
| Method | Path | Permission | Body | Returns |
|--------|------|------------|------|---------|
| GET | `/api/v1/zones` | `ZONE_VIEW` | — | `list[Zone]` |
| POST | `/api/v1/zones` | `ZONE_CREATE` | `ZoneCreate` | `Zone` |

### Cables
| Method | Path | Permission | Body | Returns |
|--------|------|------------|------|---------|
| GET | `/api/v1/cables` | `CABLE_VIEW` | — | `list[Cable]` |
| POST | `/api/v1/cables` | `CABLE_CREATE` | `CableCreate` | `Cable` |

---

## 📥 Imports

| Method | Path | Permission | Body | Returns |
|--------|------|------------|------|---------|
| GET | `/api/v1/import/batches` | `IMPORT_VIEW` | — | `list[ImportBatch]` |
| POST | `/api/v1/import/batch` | `IMPORT_CREATE` | `ImportBatchCreate` | `ImportBatch` |
| POST | `/api/v1/import/{batch_id}/commit` | `IMPORT_COMMIT` | `ImportBatchCommitRequest` | `ImportBatchCommitResponse` |
| POST | `/api/v1/import/asdpx/preview` | `IMPORT_VIEW` | `AsdpxPreviewRequest` | `AsdpxPreviewResponse` |
| POST | `/api/v1/import/asdpx/batch` | `IMPORT_CREATE` | `AsdpxBatchStageRequest` | `AsdpxBatchStageResponse` |

ASDPX = Axis SiteOwl Design Package eXchange — the CSV format used by
Axis Communications + SiteOwl. Preview is non-destructive; batch stages
the data into the import queue.

---

## 📊 Events & Revisions

| Method | Path | Permission | Returns |
|--------|------|------------|---------|
| GET | `/api/v1/events` | `EVENT_VIEW` | `list[Event]` |
| GET | `/api/v1/revisions/snapshots` | `REVISION_VIEW` | snapshot list |
| POST | `/api/v1/revisions/rollback` | `REVISION_ROLLBACK` | rollback result |

Events are the append-only audit ledger. Revisions allow point-in-time
rollback to any prior snapshot.

---

## ✅ Design Validation

| Method | Path | Permission | Body | Returns |
|--------|------|------------|------|---------|
| POST | `/api/v1/validation/run` | `DESIGN_VIEW` | `ValidationRunRequest` | `ValidationSummary` |
| POST | `/api/v1/validation/autofix/preview` | `DESIGN_EDIT` | `ValidationRunRequest` | `ValidationAutoFixPreview` |

`/run` computes design findings and scores across devices, cables, and zones.
`/autofix/preview` returns a safe-fix candidate list for findings marked
`autofix_eligible` by the validation engine.

---

## 🔄 Lifecycle

The lifecycle subsystem adds workflow state, type transitions, and
sandboxing on top of the basic CRUD resources.

### Lifecycle / Sites
| Method | Path | Permission | Purpose |
|--------|------|------------|---------|
| GET | `/api/v1/lifecycle/sites` | `SITE_VIEW` | List with filters |
| POST | `/api/v1/lifecycle/sites` | `SITE_CREATE` | Create with type + extended attrs |
| GET | `/api/v1/lifecycle/sites/by-type` | `SITE_VIEW` | Sites grouped by type |
| GET | `/api/v1/lifecycle/sites/{site_id}` | `SITE_VIEW` | Single site with history |
| PATCH | `/api/v1/lifecycle/sites/{site_id}/type` | `SITE_TRANSITION` | Change site type (records history) |

### Lifecycle / Designs
| Method | Path | Permission | Purpose |
|--------|------|------------|---------|
| GET | `/api/v1/lifecycle/designs` | `DESIGN_VIEW` | List with filters |
| POST | `/api/v1/lifecycle/designs` | `DESIGN_CREATE` | Create new design |
| GET | `/api/v1/lifecycle/designs/by-status` | `DESIGN_VIEW` | Designs grouped by status |
| GET | `/api/v1/lifecycle/designs/{design_id}` | `DESIGN_VIEW` | Single design |
| GET | `/api/v1/lifecycle/designs/{design_id}/allowed-transitions` | `DESIGN_VIEW` | Valid next states |
| PATCH | `/api/v1/lifecycle/designs/{design_id}/status` | `DESIGN_EDIT` | Transition status |
| PATCH | `/api/v1/lifecycle/designs/{design_id}/assign` | `DESIGN_EDIT` | Change owner |
| PATCH | `/api/v1/lifecycle/designs/{design_id}/vendor` | `DESIGN_EDIT` | Update vendor info |

### Lifecycle / Sandbox
| Method | Path | Permission | Purpose |
|--------|------|------------|---------|
| POST | `/api/v1/lifecycle/sandbox/clone/{source_site_id}` | `SANDBOX_CREATE` | Clone a site into a sandbox |
| POST | `/api/v1/lifecycle/sandbox/template` | `SANDBOX_TEMPLATE` | Save current as template |
| GET | `/api/v1/lifecycle/sandbox/templates` | `DESIGN_VIEW` | List available templates |

### Lifecycle / Dashboard
| Method | Path | Permission | Returns |
|--------|------|------------|---------|
| GET | `/api/v1/lifecycle/dashboard/stats` | `SITE_VIEW` | `DashboardStats` (counts by status/type) |

---

## 🏗️ Infrastructure (Camera Network)

| Method | Path | Permission | Purpose |
|--------|------|------------|---------|
| GET | `/api/v1/infrastructure/health/{store_number}` | `SITE_VIEW` | Camera fleet health summary |
| GET | `/api/v1/infrastructure/network/{store_number}` | `SITE_VIEW` | Network topology |
| GET | `/api/v1/infrastructure/diagnose/{store_number}/{camera_ip}` | `SITE_VIEW` | Single-camera diagnostic |
| POST | `/api/v1/infrastructure/dashboard/{store_number}` | `SITE_VIEW` | Generate dashboard payload |

---

## 🧠 MAXILLM (Continuous Learning)

| Method | Path | Permission | Purpose |
|--------|------|------------|---------|
| POST | `/api/v1/maxillm/predict` | `DEVICE_VIEW` | Run inference on a design |
| POST | `/api/v1/maxillm/train` | `DESIGN_EDIT` | Submit feedback for the training ledger |
| GET | `/api/v1/maxillm/stats` | `DEVICE_VIEW` | Model + training stats |

The training ledger is persisted to `data/maxillm_training/training_ledger.jsonl`.

---

## 📦 Export Center

The Export Center produces deliverables in multiple formats (CSV, GIS,
PDF reports, full project packages). All export endpoints live under
`/api/exports/*` (note: **no** `/v1/` prefix — Export Center is v2 surface).

### Export Operations
| Method | Path | Permission | Purpose |
|--------|------|------------|---------|
| POST | `/api/exports/cad` | `EXPORT_CREATE` | Export to CAD (DXF) format |
| POST | `/api/exports/siteowl` | `EXPORT_CREATE` | Export to SiteOwl CSV |
| POST | `/api/exports/gis` | `EXPORT_CREATE` | Export to GeoJSON/Shapefile |
| POST | `/api/exports/project-package` | `EXPORT_CREATE` | Full project ZIP (all formats) |
| POST | `/api/exports/qa-package` | `EXPORT_CREATE` | QA-ready package with checksums |
| POST | `/api/exports/executive-report` | `EXPORT_CREATE` | Executive PDF summary |
| GET | `/api/exports/history` | `EXPORT_VIEW` | Recent export history |

### Export Metadata
| Method | Path | Permission | Purpose |
|--------|------|------------|---------|
| GET | `/api/exports/{export_id}/metadata` | `EXPORT_VIEW` | Single export metadata |
| GET | `/api/imports/{import_id}/metadata` | `IMPORT_VIEW` | Single import metadata |
| GET | `/api/projects/{project_id}/metadata` | `PROJECT_VIEW` | Project metadata roll-up |
| GET | `/api/devices/{device_id}/metadata` | `DEVICE_VIEW` | Device metadata |
| GET | `/api/cables/{cable_id}/metadata` | `CABLE_VIEW` | Cable metadata |
| GET | `/api/zones/{zone_id}/metadata` | `ZONE_VIEW` | Zone metadata |
| POST | `/api/metadata/search` | `EXPORT_VIEW` | Cross-entity metadata search |

---

## 🔑 Permission → Role Matrix

See `apps/api/auth.py` `Role` enum for the full table. Quick reference:

| Role | What they can do |
|------|------------------|
| `viewer` | All `*_VIEW` permissions |
| `editor` | viewer + all `*_EDIT` + `*_CREATE` permissions |
| `admin` | editor + lifecycle transitions + sandbox + revisions |
| `auditor` | viewer + event view + revision view |

---

## 🧪 Testing the API

```bash
# Dev mode — no auth required
export CADOWL_DEV_MODE=true
uvicorn apps.api.main:app --reload --port 9010

# Hit the interactive docs
open http://localhost:9010/docs

# Or curl
curl http://localhost:9010/api/v1/health
curl http://localhost:9010/api/v1/projects

# Production mode — JWT required
export CADOWL_DEV_MODE=false
curl -H "Authorization: Bearer $TOKEN" http://localhost:9010/api/v1/projects
```

---

## 🤖 Auto-Verification

This file is verified by the audit system on every commit:

```bash
python -m scripts.audit --check endpoints
```

If a route is added without a doc entry here, the audit warns.
If a route is documented here but doesn't exist, the audit fails.

To suppress a known-pending endpoint, add it to
`scripts/audit/suppressions.json` with a ticket and expiry date.
