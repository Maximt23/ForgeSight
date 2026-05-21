# API Spec (Phase 1 Foundation)

Base path: `/api/v1`

## Health
- `GET /health` -> service status

## Projects
- `POST /projects`
- `GET /projects`

## Sites
- `POST /sites`
- `GET /sites?project_id=`

## Floors
- `POST /floors`
- `GET /floors?site_id=`

## Maps
- `POST /maps`
- `GET /maps?floor_id=`

## Devices
- `POST /devices`
- `GET /devices?project_id=&site_number=`

## Zones
- `POST /zones`
- `GET /zones?project_id=&floor_id=`

## Cables
- `POST /cables`
- `GET /cables?project_id=&site_number=`

## Events
- `GET /events`

## Contract Rules
- UUID primary IDs
- RFC3339 timestamps
- All mutating endpoints append event log records
- Validation errors return structured field errors

## Near-Term Additions
- `POST /import/batch`
- `POST /import/{batch_id}/commit`
- `POST /import/{batch_id}/rollback`
- `POST /devices/bulk`
- `DELETE /devices/bulk`
