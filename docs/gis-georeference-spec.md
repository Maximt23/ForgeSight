# GIS Georeference Spec

## Coordinate Systems
- Local XY (design)
- Pixel coordinates
- SiteOwl 0-100
- CAD world coordinates
- WGS84 lat/lon

## Control Point Workflow
1. Upload map
2. Select 2-4 control points
3. Enter known lat/lon
4. Compute transform matrix
5. Convert device coordinates
6. Store confidence score

## Required Fields
- `coordinate_system_id`
- `projection`
- `transform_matrix`
- `control_points`
- `gps_accuracy_score`
- `calibration_status`

## Validation
- Reject insufficient control points
- Flag low-confidence calibration
- Preserve transform versions for rollback
