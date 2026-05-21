# 🌐 The CadOwl Ecosystem

CadOwl is one piece of a larger Walmart security infrastructure platform.
This document explains how everything fits together.

---

## The Three Sibling Projects

### 1. 🦉 CadOwl (this repo)
**Role**: Core platform — API, persistence, domain model, import/export

**Owns**:
- The canonical device/project/site database
- All mutating API endpoints
- Event ledger (audit trail)
- Import pipelines (DXF, CSV, PDF)
- Export pipelines (SiteOwl CSV, GeoJSON, PDF reports)
- Schema validation
- Idempotency + rollback

**Does NOT own**:
- ML models or auto-design logic (→ MAXILLM)
- Field capture UX (→ VIVE-SiteOwl-XR)
- Live network/camera telemetry (→ MAXILLM integration layer)

---

### 2. 🧠 MAXILLM
**Role**: Intelligence + integration bridge layer

**Owns**:
- ML auto-design (pattern learning from CadOwl git history)
- GIS module (OpenStreetMap, building footprints, GPS mapping)
- External integrations:
  - Doris (store metadata)
  - Saone (camera health + streams)
  - SA Grafana (switch + port + PoE)
  - Axis Site Designer (camera FOV)
- Master Bridge (correlates everything into one infrastructure view)
- Multi-puppy coordination (file-locked task claiming)
- Auto-git commit system

**Talks to CadOwl via**: REST API + shared workspace

**Where it lives**: Co-located in `C:\MAXILLM\src\` (will eventually merge
into `CadOwl/packages/` as the platform matures)

---

### 3. 🪟 VIVE-SiteOwl-XR
**Role**: Field capture + design validation UX

**Owns**:
- Unity XR application (HTC VIVE / Quest)
- Headset-based device walk-through
- Photo capture + GPS tagging
- Real-time design overlay on physical building
- Field-vs-design diff visualization

**Talks to CadOwl via**: Schema-validated CSV import + REST API

**Repo**: https://github.com/Maximt23/VIVE-SiteOwl-XR-project

---

## How Data Flows

### Forward Pipeline (Design → Install)
```
Designer
   │
   ▼
[AutoCAD] ──DWG──► [DXF Converter] ──► [CadOwl Import API]
                                              │
                                              ▼
                                   ┌──── ImportBatch ────┐
                                   │  schema validate    │
                                   │  idempotency check  │
                                   │  event ledger entry │
                                   └─────────┬───────────┘
                                             ▼
                                    [Device/Project store]
                                             │
                          ┌──────────────────┼──────────────────┐
                          ▼                  ▼                  ▼
                  [MAXILLM GIS]     [MAXILLM ML]      [SiteOwl Export]
                  (add GPS coords)   (suggest fixes)   (legacy compat)
                          │                  │                  │
                          └──────────────────┼──────────────────┘
                                             ▼
                                    [Field Instn```

### Reverse Pipeline (Field → Design Truth)
```
Installer with VIVE headset
   │
   ▼
[VIVE-SiteOwl-XR] ──Survey CSV──► [CadOwl Field Import API]
                                              │
                                              ▼
                                   ┌── Validation + Diff ──┐
                                   │ match field ↔ design  │
                                   │ photo evidence link   │
                                   │ GPS accuracy check    │
                                   └─────────┬─────────────┘
                                             ▼
                                    [Merged Device store]
                                             │
                                             ▼
                                    [MAXILLM Master Bridge]
                                             │
                          ┌──────────────────┼──────────────────┐
                          ▼                  ▼                  ▼
                       [Doris]            [Saone]           [Grafana]
                    (store info)      (camera health)    (switch port)
                          │                  │                  │
                          └──────────────────┼──────────────────┘
                                             ▼
                                  [Live Operational Dashboard]
                                  "Camera X offline → port Y down"
```

---

## Why Three Projects Instead of One

| Concern | Lives In | Reason |
|---------|----------|--------|
| **API + canonical data** | CadOwl | Strict change control, audit, compliance |
| **ML + integrations** | MAXILLM | Faster iteration, less governance overhead |
| **Field UX** | VIVE-SiteOwl-XR | Different runtime (Unity/C#), different team |

This separation lets each project move at its own velocity. CadOwl is the
stable spine; MAXILLM is the moving brain; VIVE-XR is the hands and eyes.

Eventually MAXILLM's integration packages will migrate into
`CadOwl/packages/integrations/*` once they're stable.

---

## Coordination Between Agents

This entire ecosystem is built by a mix of human developers and AI coding
agents (Code Puppies). Coordination happens via:

- `relayops/tasks/` — task definitions, one per scoped unit of work
- `relayops/outbox/` — async messages between agents
- `relayops/state/registry.md` — who's working on what
- `relayops/state/conflicts.md` — collision warnings

Each puppy:
1. Claims a task atomically via `src/core/puppy_coordinator.py`
2. Works only inside its claimed scope
3. Auto-commits via `src/core/auto_git.py`
4. Releases the task when done

Result: hundreds of puppies can work the same monorepo without stepping
on each other.

---

## External Walmart Systems

CadOwl integrates with (but never owns) these systems:

| System | Owned By | What We Use |
|--------|----------|-------------|
| **Doris** | Walmart Store Data | Read-only store metadata |
| **Saone** | Walmart Connectivity | Read-only camera health |
| **SA Grafana** | Walmart NetOps | Read-only switch metrics |
| **AI Innovation Lab** | Walmart ML Platform | Future hosting target |
| **Element GenAI** | Walmart ML Platform | LLM calls (when needed) |
| **BigQuery** | Walmart Data Platform | Read-only analytics queries |

We are **consumers** of these systems, never sources of truth.

---

## Out-of-Scope (On Purpose)

CadOwl will **NOT**:
- Scrape competitor data (against Walmart policy)
- Host customer videos (storage liability)
- Replace SCCD / ServiceNow ticketing
- Be a CMMS or asset management replacement
- Host PII or HIPAA data
- Run anywhere except internal Walmart infrastructure

---

## Future Vision

By Phase 6 (Production GA):
- **CadOwl** is the system of record for all Walmart security device design
- **MAXILLM** packages are folded into `CadOwl/packages/` as stable engines
- **VIVE-XR** is one of N field clients (mobile, web, AR all use same API)
- **Live dashboard** shows every store's security health in real time
- **Auto-design** generates first-draft layouts in seconds, not days
- **Auto-diagnosis** tells techs why a camera is down before they get on site

That's the dream. We're building toward it one auditable commit at a time.

---

🐶 *Made with care by humans and a pack of loyal Code Puppies.*
