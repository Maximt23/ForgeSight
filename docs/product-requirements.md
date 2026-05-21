# CadOwl / MAXILLM Product Requirements (PRD)

## Mission
Build an enterprise security design operating system that surpasses legacy tools in speed, correctness, automation, and intelligence.

## Product Boundaries
CadOwl is the design platform. MAXILLM is the intelligence/review layer. External file formats are adapters, not core data model.

## Core User Personas
1. Security Designer
2. Program Manager
3. QA Reviewer
4. Vendor Coordinator
5. Integration Engineer

## Must-Have Capabilities
- Safe batch import/delete/re-upload with preview, quarantine, rollback
- Internal normalized model independent of SiteOwl/CAD/PDF/CSV
- Design canvas-ready data services (no UI implementation in this phase)
- Zone, cable, coordinate, and validation engines
- API-first CRUD + bulk workflows
- Full event audit trail and revisioning
- AI review/suggestion with approval gates

## Non-Negotiable Product Principles
1. Truth over speed
2. No silent success on failure
3. Reversible destructive actions
4. Validation before commit
5. AI explainability + confidence
6. Auditable data lineage

## Phase 1 Acceptance (Foundation)
- CRUD API for Project/Site/Floor/Map/Device/Zone/Cable
- Event log for all writes
- OpenAPI docs available
- Tests for key CRUD and audit paths
- Versioned API prefix (`/api/v1`)
