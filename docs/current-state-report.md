# CadOwl Current-State Report

Date: 2026-05-21
Owner: code-puppy-acba90

## Executive Summary
CadOwl currently exists as a **DXF-to-SiteOwl CSV converter toolchain** with useful CAD detection logic, coordinate mapping, and export support. It is not yet an API-first enterprise platform.

## Observed Stack
- Python scripts + package (`cadowl/`)
- FastAPI dependency present, but enterprise API domain model is not implemented
- Core parsing/detection focused on CAD blocks and SiteOwl CSV output
- Local batch scripts (`.bat`, `.lsp`) for AutoCAD workflows

## Existing Functional Assets
1. Device detection engine (`cadowl/core/detector.py`)
2. Coordinate mapping engine (`cadowl/core/mapper.py`)
3. SiteOwl CSV exporter (`cadowl/core/exporter.py`)
4. CLI entry points and utility scripts
5. Basic test script (`test_cadowl.py`) covering converter pipeline paths

## Current Repo Shape (High Level)
- Strong legacy conversion utility footprint
- Missing standardized monorepo module structure for API/worker/platform layers
- Missing formal product/architecture specs for enterprise rollout

## Gap Assessment Against Master Directive
### Present
- CAD/DXF parsing foundations
- Coordinate transform foundations
- SiteOwl export concept

### Missing / Partial
- Normalized enterprise data model and migrations
- API-first service boundaries and endpoint contracts
- Batch import center with quarantine + rollback workflow
- Batch delete/re-upload diff engine
- Full audit/event backbone
- Validation/self-healing policy engine
- GIS calibration and confidence model with PostGIS plan
- Cable topology domain implementation
- DORIS intelligence module specification and API shape
- MAXILLM tool-calling governance layer and approval gates
- Formal agent operating model in-repo

## Immediate Risks
1. Architecture drift if ad-hoc feature coding continues.
2. Legacy script coupling blocks scale and multi-team development.
3. Missing shared contracts causes incompatible implementations.
4. No canonical event model increases audit/compliance risk.

## Recommended Next Action
- Lock architecture + contracts first (Phase 0 complete in docs)
- Build Phase 1 API skeleton (done in this change set)
- Enforce migration/test gates before feature expansion
