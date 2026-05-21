# 🦉 CadOwl — Enterprise Security Design Platform

> **A modular, API-first platform that converts CAD designs into intelligent,
> auditable security infrastructure data — with live network/camera health
> correlation, GIS georeferencing, and ML-assisted auto-design.**

[![Status](https://img.shields.io/badge/status-active%20development-brightgreen)]()
[![Phase](https://img.shields.io/badge/phase-1.x%20foundation-blue)]()
[![License](https://img.shields.io/badge/license-internal%20Walmart-orange)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)]()

---

## 📚 Table of Contents

1. [What is CadOwl?](#-what-is-cadowl)
2. [Why It Exists](#-why-it-exists)
3. [The Ecosystem](#-the-ecosystem)
4. [Quick Start](#-quick-start)
5. [Architecture](#-architecture)
6. [Integrations](#-integrations)
7. [Repository Layout](#-repository-layout)
8. [Roadmap](#-roadmap)
9. [Contributing](#-contributing)
10. [Support](#-support)

---

## 🎯 What is CadOwl?

CadOwl is the **enterprise design operating system** for Walmart's physical
security infrastructure — Fire Alarm, CCTV, Intrusion, and Access Control.

It takes:
- 🏗️ CAD drawings (DWG/DXF)
- 📋 Field surveys (CSV from VIVE-XR)
- 📐 Floorplan PDFs
- 🛰️ GIS data (GeoJSON, ArcGIS)
- 🎥 Axis Site Designer projects

...and turns them into:
- ✅ Validated, georeferenced device databases
- 📊 Live infrastructure dashboards
- 🧠 ML-generated design suggestions
- 🔌 SiteOwl-compatible exports
- 🔍 Auto-diagnosed network/camera issues

**It is the replacement for fragile SiteOwl-only workflows.**

---

## 💡 Why It Exists

| Problem (Before CadOwl) | Solution (With CadOwl) |
|-------------------------|------------------------|
| CAD drawings exported to SiteOwl by hand | Automated DXF → SiteOwl pipeline |
| No version control, designs get lost | Git-backed, event-sourced, fully auditable |
| Camera offline? Open 4 different tools | Master Bridge correlates Saone + Grafana automatically |
| Field crew can't validate design vs. install | VIVE-SiteOwl-XR closes the loop |
| No GPS for devices | GIS module auto-georeferences from building footprint |
| Designers reinvent the same layouts | ML Auto-Design learns from history |
| No store metadata | Doris integration auto-populates everything |

---

## 🌐 The Ecosystem

CadOwl is one of three sibling projects that work together:

```
┌──────────────────────────────────────────────────────────────────┐
│                       Walmart Security                           │
│                    Design + Field Ecosystem                      │
└──────────────────────────────────────────────────────────────────┘

┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐
│   CadOwl     │   │   MAXILLM    │   │  VIVE-SiteOwl-XR         │
│  (this repo) │◄──┤ (intelligent │──►│  (Unity XR field tool)   │
│              │   │  data layer) │   │                          │
│  CAD parser  │   │  ML / GIS    │   │  Headset-based survey    │
│  API + DB    │   │  Bridges     │   │  Photo + GPS capture     │
│  Lifecycle   │   │  Auto-design │   │  Design validation       │
└──────────────┘   └──────────────┘   └──────────────────────────┘
        │                  │                       │
        └──────────────────┼───────────────────────┘
                           ▼
                ┌────────────────────┐
                │ Live Infrastructure│
                │   Doris / Saone /  │
                │  Grafana / Axis    │
                └────────────────────┘
```

| Project | Purpose | Repo |
|---------|---------|------|
| **CadOwl** | Core API, lifecycle, persistence, import/export | [gecgithub01.walmart.com/vn59j7j/CadOwl](https://gecgithub01.walmart.com/vn59j7j/CadOwl) |
| **MAXILLM** | ML auto-design, GIS, integrations bridge layer | (sibling — co-located in workspace) |
| **VIVE-SiteOwl-XR** | Unity XR app for field validation + survey | [github.com/Maximt23/VIVE-SiteOwl-XR-project](https://github.com/Maximt23/VIVE-SiteOwl-XR-project) |

See [ECOSYSTEM.md](docs/ECOSYSTEM.md) for full architecture diagrams.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Git
- Walmart VPN or Eagle WiFi (for internal services)

### Install
```bash
git clone https://gecgithub01.walmart.com/vn59j7j/CadOwl.git
cd CadOwl
uv venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # macOS/Linux
uv pip install -r requirements.txt \
  --index-url https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple \
  --allow-insecure-host pypi.ci.artifacts.walmart.com
```

### Run the API
```bash
python -m uvicorn apps.api.main:app --reload --port 9010
```

Open the interactive docs:
- 📖 http://localhost:9010/docs (Swagger)
- 📕 http://localhost:9010/redoc (ReDoc)

### Run a CAD conversion (legacy utility)
```bash
python cad2siteowl.py "Input/FA/your_store.dxf"
```

Output appears in `Output/FA/{STORE}_SiteOwl_Export.csv` — already in
SiteOwl coordinate space (0–100 range, top-left origin).

### Run an Axis ASDPX → SiteOwl CSV conversion (backend utility, no UI)
```bash
python scripts/import/convert_asdpx_to_siteowl_csv.py \
  "data/sample-imports/siteowl_workflow_v2/Sample_2996.asdpx" \
  -o "Output/Sample_2996_siteowl.csv"
```

### Run tests
```bash
python -m pytest tests/integration/test_phase1_api.py tests/integration/test_axis_asdpx_adapter.py -q
```

---

## 🏗️ Architecture

CadOwl is an **API-first modular monorepo** with strict safety controls:

```
apps/api/        ← FastAPI gateway + domain services
apps/worker/     ← Async jobs (import/validate/export/AI review)
apps/web/        ← Future UX shell (Phase 2)
apps/mobile/     ← Future mobile shell (Phase 3)
packages/        ← Reusable domain engines (import, gis, cable, ai)
data/jsondb/     ← JSON document storage (Phase 1) → Postgres (Phase 1.1)
data/schemas/    ← JSON Schema definitions for all aggregates
docs/            ← Architecture, specs, lifecycle
tests/           ← Integration + unit tests
infra/           ← Docker, CI, deployment
scripts/         ← One-off operational scripts
```

### Domain Aggregates
- **Project** — site / floor / map containment
- **Device / Cable** — physical infrastructure
- **Zone / Coordinate** — spatial decomposition
- **ImportBatch** — every import with full validation artifacts
- **Event** — append-only audit ledger of every mutation

### Safety Controls (Non-Negotiable)
- 🔒 **Idempotency keys** required for all bulk/import endpoints
- 📜 **Event ledger** records every write (immutable, append-only)
- ↩️ **Soft delete + rollback points** for every destructive op
- 🧪 **Schema validation** runs on all writes
- 🤖 **AI mutations** behind explicit approval workflow

Read more: [docs/architecture.md](docs/architecture.md)

---

## 🔌 Integrations

CadOwl talks to a constellation of Walmart and external systems:

| System | Purpose | Module |
|--------|---------|--------|
| 🏪 **Doris** | Store metadata, GPS, types, regions | `packages/integrations/doris` |
| 🎥 **Saone** | Live camera health, stream URLs, alerts | `packages/integrations/saone` |
| 📊 **SA Grafana** | Switch + port + PoE monitoring | `packages/integrations/grafana` |
| 🎬 **Axis Site Designer** | Camera FOV, model specs, layouts | `packages/integrations/axis` |
| 🗺️ **OpenStreetMap** | Geocoding, building footprints | `packages/gis/osm` |
| 📐 **AutoCAD** | DXF parsing, layer extraction | `packages/cad/dxf` |
| 📑 **SiteOwl** | Legacy export compatibility | `packages/exports/siteowl` |
| 🪟 **VIVE-XR** | Field survey ingestion | `packages/integrations/vive` |

All integration details in [INTEGRATIONS.md](INTEGRATIONS.md).

---

## 📁 Repository Layout

```
CadOwl/
├── .github/                  # CI, issue templates, CODEOWNERS
│   ├── workflows/ci.yml      # GitHub Actions
│   └── ISSUE_TEMPLATE/       # Bug + feature templates
├── apps/
│   ├── api/                  # FastAPI service (Phase 1)
│   ├── worker/               # Async jobs
│   ├── web/                  # Future React UI
│   └── mobile/               # Future mobile app
├── packages/                 # Domain engines (planned migration)
│   ├── import/
│   ├── validation/
│   ├── gis/
│   ├── cable/
│   └── ai/
├── data/
│   ├── jsondb/               # Phase 1 JSON document store
│   ├── schemas/              # JSON Schema definitions
│   └── fixtures/             # Test fixtures
├── docs/                     # Architecture + specs
├── tests/
│   ├── integration/
│   └── unit/
├── scripts/                  # Operational scripts
├── infra/                    # Docker, Terraform, deploy
├── Input/                    # CAD input (gitignored)
├── Output/                   # Conversion output (gitignored)
├── *.lsp                     # AutoCAD LISP utilities
├── cad2siteowl.py            # Legacy converter (root)
└── README.md
```

---

## 🛣️ Roadmap

See [ROADMAP.md](ROADMAP.md) for the full plan. High-level phases:

| Phase | Status | Focus |
|-------|--------|-------|
| **0 — Foundation** | ✅ Complete | Architecture docs, repo scaffold |
| **1 — API Skeleton** | ✅ Complete | JSON store, events, idempotency, rollback |
| **1.1 — Persistence** | 🟡 Active | Swap JSON store → Postgres/PostGIS |
| **2 — Web Shell** | 🟡 Active | React UI, batch upload, live dashboards |
| **3 — Intelligence** | 🟡 Active | ML auto-design, pattern learning |
| **4 — Infrastructure Brain** | ✅ Prototype | Master bridge (Saone + Grafana + Doris) |
| **5 — Mobile / Field** | ⚪ Planned | iOS/Android, VIVE XR integration |
| **6 — Production GA** | ⚪ Planned | Hardening, SLOs, observability |

---

## 🤝 Contributing

We're an internal Walmart project, but contributions welcome from anyone with
repo access. Quick rules:

1. **Read [CONTRIBUTING.md](CONTRIBUTING.md)** before opening a PR
2. **Never force-push** to `main`
3. **All mutating endpoints must emit events** — no silent writes
4. **Tests are mandatory** for new functionality
5. **Follow [SECURITY.md](SECURITY.md)** for anything touching customer data
6. **No PII or scraped competitor data** ever gets committed

### Multi-Agent Development
This repo is built by both humans and AI coding agents (Code Puppies). Agents
coordinate via the `relayops/` directory in the sibling MAXILLM workspace.

If you're a puppy reading this:
- Claim tasks via `relayops/tasks/`
- Drop messages in `relayops/outbox/`
- Watch `relayops/state/conflicts.md` for collision warnings
- Auto-commit using `src/core/auto_git.py`

---

## 🛡️ Security

- 🔐 Never commit API keys, tokens, or `.env` files
- 🔐 Never commit PII, SSN, HIPAA, PCI, or scraped competitor data
- 🔐 Never commit customer photos or store videos
- 🔐 Report security issues via [SECURITY.md](SECURITY.md) — do **not** open
  a public issue

---

## 📞 Support

| Need | Where to Go |
|------|-------------|
| 🐛 Bug | Open a [bug report](https://gecgithub01.walmart.com/vn59j7j/CadOwl/issues/new?template=bug_report.yml) |
| 💡 Feature | Open a [feature request](https://gecgithub01.walmart.com/vn59j7j/CadOwl/issues/new?template=feature_request.yml) |
| 🔒 Security | See [SECURITY.md](SECURITY.md) |
| 💬 General | Slack: `#mint-support` |
| 🎓 Walmart Code Puppy | [puppy.walmart.com](https://puppy.walmart.com) |

---

## 📜 License

Internal Walmart project. See [LICENSE](LICENSE) for details.

---

> **Built by Maxim Tsitolovsky** with the help of a pack of loyal Code Puppies 🐶  
> *Replacing fragile point tools with auditable, intelligent automation.*
