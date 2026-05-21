# 🏗️ Architecture Overview

CadOwl is built as a modular, API-first platform for enterprise security design management.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTS                                        │
├──────────────────┬──────────────────┬──────────────────┬───────────────────┤
│   Web Dashboard  │   CLI Tools      │   VIVE XR        │   Integrations    │
│   (HTMX/Tailwind)│   (Python)       │   (Unity/C#)     │   (REST API)      │
└────────┬─────────┴────────┬─────────┴────────┬─────────┴─────────┬─────────┘
         │                  │                  │                   │
         └──────────────────┴──────────────────┴───────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY                                        │
│                     (FastAPI + Walmart SSO)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  /auth/*          │  /api/v1/sites/*    │  /api/v1/designs/*               │
│  /api/v1/health   │  /api/v1/devices/*  │  /api/v1/sandbox/*               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Lifecycle     │    │   CAD Processing    │    │   Device Matching   │
│   Service       │    │   Service           │    │   Service           │
│                 │    │                     │    │                     │
│ - Sites         │    │ - DXF/DWG Import    │    │ - Proximity Match   │
│ - Designs       │    │ - Coordinate Trans  │    │ - Attribute Match   │
│ - Workflows     │    │ - Device Detection  │    │ - Merge Strategy    │
└────────┬────────┘    └──────────┬──────────┘    └──────────┬──────────┘
         │                        │                          │
         └────────────────────────┴──────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                         │
├───────────────────┬───────────────────┬───────────────────┬─────────────────┤
│   JSON Store      │   Event Log       │   File Storage    │   Cache         │
│   (Phase 1)       │   (JSONL)         │   (Local/S3)      │   (Redis)       │
├───────────────────┴───────────────────┴───────────────────┴─────────────────┤
│                    PostgreSQL + PostGIS (Phase 2)                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
CadOwl/
├── apps/                       # Application layer
│   └── api/                    # REST API
│       ├── main.py             # FastAPI app entry
│       ├── auth.py             # Walmart SSO
│       ├── lifecycle.py        # Enums & models
│       ├── lifecycle_routes.py # REST endpoints
│       ├── lifecycle_store.py  # Persistence
│       ├── schemas.py          # Pydantic models
│       └── store.py            # JSON store
│
├── cadowl/                     # Core library
│   ├── core/
│   │   ├── detector.py         # Device detection
│   │   ├── mapper.py           # Coordinate mapping
│   │   └── exporter.py         # SiteOwl export
│   └── cli.py                  # CLI commands
│
├── shared/                     # Cross-platform code
│   ├── transform/              # Coordinate transformation
│   │   ├── transform_core.py   # Python impl
│   │   └── TransformCore.cs    # C# impl (Unity)
│   ├── matching/               # Device matching
│   │   ├── device_matcher.py
│   │   └── merge_strategy.py
│   └── schema/                 # JSON schemas
│
├── app/                        # Web dashboard
│   └── templates/
│       └── dashboard.html
│
├── data/                       # Data storage
│   ├── lifecycle/              # Sites, designs, events
│   └── jsondb/                 # Entity storage
│
├── tests/                      # Test suite
│   └── integration/
│
├── wiki/                       # Documentation
│
└── docs/                       # Additional docs
```

---

## Core Components

### 1. API Gateway (`apps/api/`)

The FastAPI-based REST API handles all external requests.

**Key Files**:
- `main.py` — App initialization, route registration
- `auth.py` — Walmart SSO with Azure AD
- `lifecycle_routes.py` — Site/design CRUD endpoints

**Technologies**:
- FastAPI 0.100+
- Pydantic v2 for validation
- python-jose for JWT

### 2. Lifecycle Service

Manages the state machine for sites and designs.

**Capabilities**:
- Status transitions with validation
- Audit trail logging
- Permission enforcement

### 3. CAD Processing (`cadowl/core/`)

Extracts device data from CAD files.

**Pipeline**:
```
DXF/DWG → Parse → Detect Devices → Transform Coords → Export
```

**Key Files**:
- `detector.py` — Pattern matching for devices
- `mapper.py` — Coordinate transformation
- `exporter.py` — SiteOwl CSV format

### 4. Device Matching (`shared/matching/`)

Correlates devices from multiple sources.

**Algorithm**:
1. Transform all coords to SiteOwl space
2. Build spatial index (KD-tree)
3. Score matches by distance + attributes
4. Resolve conflicts (Hungarian algorithm)
5. Merge with audit trail

### 5. Coordinate Transform (`shared/transform/`)

Cross-platform coordinate transformation.

**Implementations**:
- Python (`transform_core.py`)
- C# (`TransformCore.cs`)

Both use identical math for consistency.

---

## Data Flow

### CAD Import Flow

```
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐
│ DXF/DWG │───►│ Parser   │───►│ Detector │───►│ Mapper   │───►│ Export  │
│ File    │    │ (ezdxf)  │    │ (regex)  │    │ (affine) │    │ (CSV)   │
└─────────┘    └──────────┘    └──────────┘    └──────────┘    └─────────┘
```

### Design Approval Flow

```
Designer          Reviewer           PM              Installer
    │                 │               │                  │
    │─── Submit ─────►│               │                  │
    │                 │── Review ────►│                  │
    │◄── Revision ────│               │                  │
    │─── Resubmit ───►│               │                  │
    │                 │── Approve ───►│                  │
    │                 │               │── Assign ───────►│
    │                 │               │                  │── Install ──►
    │                 │               │◄── Complete ─────│
    │                 │               │── Go Live ──────►│
```

---

## Security Model

### Authentication

- **Walmart SSO** via Microsoft Entra ID (Azure AD)
- **JWT tokens** with RS256 signing
- **Role-based access** with granular permissions

### Authorization Levels

| Role | Create | Edit | Approve | Admin |
|:-----|:------:|:----:|:-------:|:-----:|
| Viewer | ❌ | ❌ | ❌ | ❌ |
| Designer | ✅ | ✅ | ❌ | ❌ |
| Reviewer | ❌ | ❌ | ✅ | ❌ |
| PM | ✅ | ✅ | ✅ | ❌ |
| Admin | ✅ | ✅ | ✅ | ✅ |

---

## Related

- [API Reference](Dev-API-Reference.md)
- [Authentication](Dev-Authentication.md)
- [Database Schema](Dev-Database-Schema.md)
