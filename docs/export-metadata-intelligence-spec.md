# Export + Metadata Intelligence (Phase Foundation)

## What is implemented now
CadOwl now includes an API-level **Export Center foundation** and metadata search layer.

### API Endpoints
- `GET /api/projects/{id}/metadata`
- `GET /api/devices/{id}/metadata`
- `GET /api/zones/{id}/metadata`
- `GET /api/cables/{id}/metadata`
- `GET /api/imports/{id}/metadata`
- `GET /api/exports/{id}/metadata`
- `POST /api/metadata/search`
- `POST /api/exports/project-package`
- `POST /api/exports/siteowl`
- `POST /api/exports/gis`
- `POST /api/exports/cad`
- `POST /api/exports/qa-package`
- `POST /api/exports/executive-report`

### Export outputs currently produced
- JSON metadata files
- CSV schedules (device/cable/validation)
- XLSX schedules
- GeoJSON coordinate export
- SiteOwl-compatible CSV
- CAD assets: SVG, PNG, DXF, PDF (basic plotting)
- Executive PDF summary
- ZIP package with `manifest.json`

## Manifest guarantee
Every package includes `manifest.json` with:
- export_id
- project_id/site_number
- export_type
- created_at/by
- app/schema version
- files included
- record_counts
- validation_score
- coordinate_confidence
- rollback_available

## Metadata categories generated
- project_metadata
- file_metadata
- import_metadata
- device_metadata
- coordinate_metadata
- zone_metadata
- cable_metadata
- validation_metadata
- ai_metadata
- revision_metadata
- export_metadata

## Risk gate
Exports are blocked when critical validation findings exist, unless:
- `override_risk=true`
- `override_reason` provided

## Current intentional gaps
- No UI Export Center yet (API-first completion)
- AI suggestion metadata currently structural (no model inference history persisted yet)
- Revit/BIM and DWG exports are placeholders for next implementation pass
