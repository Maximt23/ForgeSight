# Axis ASDPX Adapter Spec (Backend, No UI)

## Objective
Use Axis SiteDesigner `.asdpx` exports as an import adapter for SiteOwl-compatible CSV rows.

## Inputs
- `.asdpx` JSON payload with root `children`
- `floorPlan.image.bounds` and dimensions
- `installationPoint` records with GPS
- optional `quotation.pricesByPartNumber`

## Outputs
- normalized SiteOwl rows (56-column schema)
- key fields mapped:
  - Device ID
  - Name
  - System Type
  - Device/Task Type
  - Part Number
  - Coverage Direction/Angle/Range
  - Height (ft)
  - Field Notes (GPS)
  - Coordinates `(XX.XX, YY.YY)`

## Implemented Components
- `apps/api/adapters/axis_siteowl_adapter.py`
- `POST /api/v1/import/asdpx/preview`
- `POST /api/v1/import/asdpx/batch` (staged import batch)
- `POST /api/v1/import/{batch_id}/commit` (device materialization)
- `scripts/import/convert_asdpx_to_siteowl_csv.py`

## Conversion Rules
- 80% width map rule on 100x100 artboard
- map centered in artboard
- GPS -> pixel -> feet -> SiteOwl display coordinates
- coverage direction normalized to 0..359

## Known Gaps (intentional for phase)
- no UI editor integration yet
- no persistent import-commit pipeline yet
- part-number mapping falls back to deterministic defaults when source is sparse
