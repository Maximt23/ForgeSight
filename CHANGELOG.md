# Changelog

All notable changes to CadOwl will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added — Documentation Pass (2026-05-21)
- Flagship `README.md` rewrite with full ecosystem overview
- `docs/ECOSYSTEM.md` documenting CadOwl + MAXILLM + VIVE-SiteOwl-XR
- `docs/INTEGRATIONS.md` covering Doris, Saone, Grafana, Axis, OSM
- `CONTRIBUTING.md` with human + AI agent workflow rules
- `SECURITY.md` with vulnerability reporting + sensitive data policy
- `CODE_OF_CONDUCT.md`
- `CHANGELOG.md` (this file)
- Enhanced `.gitignore` for ML artifacts, IDE files, secret patterns
- Coordination message system for multi-puppy development

### Added — Intelligence Layer (MAXILLM sibling project)
- ML auto-design module (pattern learning from git history)
- GIS integration (OpenStreetMap geocoding + building footprints)
- Axis Site Designer JSON importer with coverage calculations
- Doris store metadata integration with local caching
- Saone live camera health + stream URLs
- SA Grafana switch + port + PoE monitoring
- Device-Saone bridge for auto-registration
- Master Infrastructure Bridge correlating all integrations
- Multi-puppy coordination system (file-locked task claiming)
- Auto-git commit system with smart messages

### Added — Lifecycle (from sibling puppies)
- Site & design lifecycle management (commit `0aa787e`)
- Perfect-mode phase 2 test coverage for schema, idempotency,
  snapshots, rollback (commit `14d711b`)
- Device matching module VIVE-004 (commit `430ff39`)
- Shared cross-platform transform core, Python + C# (commit `4df0be2`)

### Added — Phase 1 Foundation
- API skeleton with FastAPI under `apps/api/`
- JSON document storage under `data/jsondb/`
- Append-only event ledger (`event_ledger.jsonl`)
- Snapshot compaction and rollback endpoints
- Idempotency-key enforcement for import batch writes
- Integration tests for contracts, persistence, rollback
- GitHub repo governance (CODEOWNERS, issue templates, PR template, CI)

---

## [0.2.0] — 2025-XX-XX (Pre-Phase 1)

### Added
- Improved device detection patterns: 30+ Bosch/Axis/Walmart camera
  patterns; 50+ architecture blocks excluded
- Modern CadOwl web GUI with dashboard and module scaffolding
- Modular core library (CadOwl v2.0) with improved coordinate mapping,
  device detection, and CLI

### Fixed
- Input/output paths now match actual OneDrive folder structure
- Unicode encoding issue in `dwg_converter`

---

## [0.1.0] — 2024-XX-XX (Initial Utility)

### Added
- DWG → DXF conversion via AutoCAD LISP (`DWG2DXF.lsp`)
- DXF → SiteOwl CSV conversion (`cad2siteowl.py`)
- Coordinate normalization to 0–100 SiteOwl space
- Layer-based device categorization (FA, CCTV, Intrusion)
- Batch processing scripts (`Process-FA.bat`, `Process-CCTV.bat`)
- Watcher mode for hot-folder processing
- Basic test harness (`test_cadowl.py`)

---

## Versioning Guide

- **Major** (X.0.0) — Breaking API changes, schema migrations, or removal
  of supported workflows
- **Minor** (0.X.0) — New features that maintain backward compatibility
- **Patch** (0.0.X) — Bug fixes, doc updates, internal refactors

Pre-1.0: minor versions may include breaking changes; we'll call them out
clearly in this changelog.

---

## How to Update This Changelog

When merging a PR, add an entry under `[Unreleased]` in the appropriate
section:

- `Added` — new features
- `Changed` — changes to existing functionality
- `Deprecated` — soon-to-be-removed features
- `Removed` — features removed this release
- `Fixed` — bug fixes
- `Security` — security-related changes (link to advisory if any)

Example:
```markdown
### Added
- New `/api/v1/exports/pdf` endpoint for PDF-format export (#142)
```

On release tagging, move `[Unreleased]` content to a new version section
with the release date.

---

🐶 *Keep history honest. Future you will thank present you.*
