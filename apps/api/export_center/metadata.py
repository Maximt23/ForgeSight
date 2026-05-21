import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4


def coord_confidence(local_x: float, local_y: float) -> float:
    if local_x < 0 or local_y < 0:
        return 0
    edge_penalty = 0
    if local_x < 1 or local_y < 1:
        edge_penalty += 8
    if local_x > 99 or local_y > 99:
        edge_penalty += 8
    return max(0.0, 100.0 - edge_penalty)


def validation_rows(payload: dict) -> list[dict]:
    rows: list[dict] = []
    for device in payload["devices"]:
        if not device.name.strip():
            rows.append(
                {
                    "validation_id": str(uuid4()),
                    "validation_run_id": datetime.now(UTC).strftime("val-%Y%m%d%H%M%S"),
                    "entity_type": "device",
                    "entity_id": str(device.id),
                    "severity": "critical",
                    "category": "required_field",
                    "field": "name",
                    "message": "Device name missing",
                    "technical_reason": "name is required",
                    "suggested_fix": "populate device name",
                    "auto_fix_available": False,
                    "confidence_score": 99,
                    "resolved_status": False,
                    "resolved_by": None,
                    "resolved_at": None,
                }
            )
        if device.local_x < 0 or device.local_y < 0:
            rows.append(
                {
                    "validation_id": str(uuid4()),
                    "validation_run_id": datetime.now(UTC).strftime("val-%Y%m%d%H%M%S"),
                    "entity_type": "device",
                    "entity_id": str(device.id),
                    "severity": "critical",
                    "category": "coordinate",
                    "field": "local_x/local_y",
                    "message": "Negative coordinates are forbidden",
                    "technical_reason": "store coordinate space starts at 0,0",
                    "suggested_fix": "clamp/import with non-negative coordinates",
                    "auto_fix_available": True,
                    "confidence_score": 99,
                    "resolved_status": False,
                    "resolved_by": None,
                    "resolved_at": None,
                }
            )
    return rows


def metadata_snapshot(project_payload: dict, export_history: list[dict]) -> dict:
    project = project_payload["project"]
    now = datetime.now(UTC).isoformat()

    project_metadata = {
        "project_id": str(project.id),
        "project_name": project.name,
        "site_number": project_payload["site_number"],
        "program_year": datetime.now(UTC).year,
        "project_type": "security_design",
        "survey_type": "mixed",
        "vendor": None,
        "designer": None,
        "reviewer": None,
        "status": "active",
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "due_date": None,
        "construction_date": None,
        "possession_date": None,
        "risk_level": "medium",
        "completion_percent": 50,
        "validation_score": 100,
        "design_confidence_score": 88,
    }

    file_metadata = [
        {
            "file_id": str(uuid4()),
            "file_name": b.source_file_name,
            "file_type": Path(b.source_file_name).suffix.lower().lstrip("."),
            "file_size": None,
            "file_hash": b.source_file_hash,
            "upload_user": "system",
            "upload_timestamp": b.created_at.isoformat(),
            "source_system": "import_batch",
            "parsing_status": "parsed",
            "parser_version": "2026.05",
            "detected_template": "unknown",
            "detected_layers": [],
            "detected_scale": None,
            "detected_units": None,
            "import_batch_id": str(b.id),
            "validation_score": 100,
        }
        for b in project_payload["import_batches"]
    ]

    import_metadata = [
        {
            "import_batch_id": str(b.id),
            "source_file_id": str(b.id),
            "imported_by": "system",
            "import_timestamp": b.created_at.isoformat(),
            "total_records": b.record_count,
            "created_records": b.record_count,
            "updated_records": 0,
            "deleted_records": 0,
            "quarantined_records": 0,
            "warning_count": 0,
            "error_count": 0,
            "import_health_score": 100,
            "rollback_id": None,
            "template_used": "unknown",
            "column_mapping_used": "default",
        }
        for b in project_payload["import_batches"]
    ]

    device_metadata = []
    for d in project_payload["devices"]:
        device_metadata.append(
            {
                "device_id": str(d.id),
                "source_device_id": str(d.id),
                "site_number": d.site_number,
                "floor_id": str(d.floor_id) if d.floor_id else None,
                "map_id": str(d.map_id) if d.map_id else None,
                "zone_id": None,
                "device_name": d.name,
                "device_type": d.device_type,
                "device_category": d.device_type,
                "doris_number": None,
                "manufacturer": None,
                "model": None,
                "part_number": None,
                "serial_number": None,
                "ip_address": None,
                "mac_address": None,
                "local_x": d.local_x,
                "local_y": d.local_y,
                "latitude": None,
                "longitude": None,
                "coordinate_confidence": coord_confidence(d.local_x, d.local_y),
                "mounting_height": None,
                "heading": None,
                "tilt": None,
                "roll": None,
                "fov_angle": None,
                "fov_distance": None,
                "coverage_polygon": None,
                "install_status": "unknown",
                "survey_status": "unknown",
                "validation_status": "valid",
                "source_file": None,
                "created_by": "system",
                "updated_by": "system",
                "last_modified_at": d.updated_at.isoformat(),
            }
        )

    coordinate_metadata = [
        {
            "coordinate_system": "siteowl_local_0_100",
            "local_x": d.local_x,
            "local_y": d.local_y,
            "local_z": 0,
            "latitude": None,
            "longitude": None,
            "elevation": None,
            "floor_level": 0,
            "map_scale": 1.0,
            "map_rotation": 0,
            "transform_matrix_id": "identity",
            "control_points_used": [],
            "gps_accuracy_score": None,
            "coordinate_confidence": coord_confidence(d.local_x, d.local_y),
            "calibration_status": "unknown",
            "conversion_method": "direct",
        }
        for d in project_payload["devices"]
    ]

    zone_metadata = [
        {
            "zone_id": str(z.id),
            "zone_name": z.zone_name,
            "zone_type": z.zone_type,
            "polygon_geometry": None,
            "floor_id": str(z.floor_id),
            "device_count": 0,
            "required_device_count": 0,
            "coverage_score": 0,
            "risk_score": 0,
            "blind_spot_count": 0,
            "cable_count": 0,
            "validation_status": "unknown",
        }
        for z in project_payload["zones"]
    ]

    cable_metadata = [
        {
            "cable_id": str(c.id),
            "source_device": str(c.source_device_id),
            "destination_device": str(c.destination_device_id),
            "cable_type": c.cable_type,
            "cable_category": c.cable_type,
            "estimated_length": None,
            "measured_length": None,
            "route_geometry": None,
            "pathway": None,
            "source_port": None,
            "destination_port": None,
            "max_length_allowed": None,
            "length_validation_status": "unknown",
            "connection_status": "unknown",
            "install_status": "unknown",
        }
        for c in project_payload["cables"]
    ]

    validation_metadata = validation_rows(project_payload)
    ai_metadata: list[dict] = []
    revision_metadata = [
        {
            "revision_id": str(e.id),
            "project_id": str(project.id),
            "changed_by": e.actor,
            "change_type": e.event_type,
            "entity_type": e.entity_type,
            "entity_id": str(e.entity_id),
            "before_value": None,
            "after_value": e.metadata,
            "reason": e.event_type,
            "source": "event_ledger",
            "timestamp": e.created_at.isoformat(),
            "rollback_available": True,
        }
        for e in project_payload["events"]
    ]

    designer_vendor_metadata = [
        {
            "designer_id": "unknown",
            "vendor_id": "unknown",
            "projects_completed": 0,
            "average_validation_score": 100,
            "average_rework_count": 0,
   "common_errors": [],
            "average_design_time": None,
            "average_review_time": None,
            "approval_rate": 100,
            "rejection_rate": 0,
            "pattern_score": 0,
        }
    ]

    export_metadata = [x for x in export_history if x.get("project_id") == str(project.id)]

    return {
        "generated_at": now,
        "project_metadata": project_metadata,
        "file_metadata": file_metadata,
        "import_metadata": import_metadata,
        "device_metadata": device_metadata,
        "coordinate_metadata": coordinate_metadata,
        "zone_metadata": zone_metadata,
        "cable_metadata": cable_metadata,
        "validation_metadata": validation_metadata,
        "ai_metadata": ai_metadata,
        "revision_metadata": revision_metadata,
        "designer_vendor_metadata": designer_vendor_metadata,
        "export_metadata": export_metadata,
    }


def metadata_search(store, metadata_builder, request) -> list[dict]:
    def matches(item: dict, field: str, op: str, value) -> bool:
        target = item.get(field)
        if op == "eq":
            return target == value
        if op == "contains":
            return str(value).lower() in str(target).lower()
        if op == "lt":
            return target is not None and target < value
        if op == "lte":
            return target is not None and target <= value
        if op == "gt":
            return target is not None and target > value
        if op == "gte":
            return target is not None and target >= value
        if op == "in":
            return target in (value or [])
        if op == "is_null":
            return target is None
        return False

    all_records: list[dict] = []
    for project_id in store.projects.keys():
        snap = metadata_builder(project_id)
        for key, value in snap.items():
            if key.endswith("_metadata"):
                if isinstance(value, dict):
                    all_records.append({"_entity_type": key.replace("_metadata", ""), **value})
                else:
                    for item in value:
                        if isinstance(item, dict):
                            all_records.append({"_entity_type": key.replace("_metadata", ""), **item})

    if request.entity_types:
        keep = set(request.entity_types)
        all_records = [x for x in all_records if x.get("_entity_type") in keep]

    for f in request.filters:
        all_records = [x for x in all_records if matches(x, f.field, f.op, f.value)]

    return all_records[: request.limit]
