# Cable Model Spec

## Core Entities
- Cable
- Connection
- CablePath
- Rack/MDF/IDF
- NetworkSwitch

## Cable Fields (Core)
- `cable_id`, `project_id`, `site_number`, `floor_id`
- `source_device_id`, `destination_device_id`
- `source_port`, `destination_port`
- `cable_type`, `estimated_length`, `measured_length`
- `route_geometry`, `status`, `validation_status`

## Required Validations
- Max run length by cable type
- Orphan and disconnected device detection
- Duplicate connection detection
- Missing port capacity detection

## Outputs
- Cable schedule
- Topology graph payload
- Validation warnings/errors
