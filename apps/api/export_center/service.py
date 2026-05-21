from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from .metadata import metadata_search, metadata_snapshot
from .schemas import ExportHistoryRecord, ExportRequest, ExportResult, ExportType, MetadataSearchRequest
from .writers import (
    build_manifest,
    cad_drawings,
    device_geojson_rows,
    siteowl_rows,
    write_csv,
    write_json,
    write_pdf,
    write_xlsx,
    write_zip,
)


class ExportRepository:
    @staticmethod
    def _path() -> Path:
        from .. import store as store_module

        path = store_module.STORE.base_dir / "export_metadata.json"
        if not path.exists():
            path.write_text("[]", encoding="utf-8")
        return path

    def load(self) -> list[dict]:
        import json

        return json.loads(self._path().read_text(encoding="utf-8"))

    def save(self, records: list[dict]) -> None:
        import json

        self._path().write_text(json.dumps(records, indent=2), encoding="utf-8")

    def append(self, record: ExportHistoryRecord) -> None:
        items = self.load()
        items.append(record.model_dump(mode="json"))
        self.save(items)

    def get(self, export_id: str) -> dict | None:
        return next((x for x in self.load() if x.get("export_id") == export_id), None)

    def list(self, limit: int = 50) -> list[dict]:
        rows = sorted(self.load(), key=lambda x: x.get("created_at", ""), reverse=True)
        return rows[:limit]


class ExportService:
    SUPPORTED_FORMATS: dict[ExportType, set[str]] = {
        "project-package": {"zip", "json", "csv", "xlsx", "geojson", "dxf", "svg", "png", "pdf"},
        "siteowl": {"csv", "xlsx", "json"},
        "gis": {"geojson", "json", "zip"},
        "cad": {"dxf", "svg", "png", "pdf", "zip"},
        "qa-package": {"zip", "json", "xlsx", "pdf"},
        "executive-report": {"pdf", "json"},
    }

    def __init__(self) -> None:
        self.repo = ExportRepository()
        self.output_root = Path("C:/MAXILLM/cadowl/Output/exports")
        self.output_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _store():
        from .. import store as store_module

        return store_module.STORE

    def _project_payload(self, project_id: UUID) -> dict:
        project = self._store().projects.get(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found")

        sites = [x for x in self._store().sites.values() if x.project_id == project_id]
        site_numbers = {x.site_number for x in sites}
        floor_ids = {f.id for f in self._store().floors.values() if f.site_id in {s.id for s in sites}}

        devices = [x for x in self._store().devices.values() if x.project_id == project_id]
        zones = [x for x in self._store().zones.values() if x.project_id == project_id]
        cables = [x for x in self._store().cables.values() if x.project_id == project_id]
        maps = [x for x in self._store().maps.values() if x.floor_id in floor_ids]
        batches = [x for x in self._store().import_batches.values()]
        events = [e for e in self._store().events if str(e.entity_id) in {str(project_id)} | {str(d.id) for d in devices}]

        site_number = sorted(site_numbers)[0] if site_numbers else project.code
        return {
            "project": project,
            "site_number": site_number,
            "sites": sites,
            "floors": [x for x in self._store().floors.values() if x.id in floor_ids],
            "maps": maps,
            "devices": devices,
            "zones": zones,
            "cables": cables,
            "import_batches": batches,
            "events": events,
        }

    def metadata_snapshot(self, project_id: UUID) -> dict:
        payload = self._project_payload(project_id)
        return metadata_snapshot(payload, self.repo.load())

    def search_metadata(self, request: MetadataSearchRequest) -> list[dict]:
        return metadata_search(self._store(), self.metadata_snapshot, request)

    def _ensure_supported(self, export_type: ExportType, formats: list[str]) -> None:
        allowed = self.SUPPORTED_FORMATS[export_type]
        bad = [x for x in formats if x not in allowed]
        if bad:
            raise ValueError(f"Unsupported format(s) for {export_type}: {bad}. Allowed: {sorted(allowed)}")

    @staticmethod
    def _risk_gate(request: ExportRequest, metadata: dict) -> str | None:
        criticals = [x for x in metadata.get("validation_metadata", []) if x.get("severity") == "critical"]
        if criticals and not request.override_risk:
            return "Critical validation findings present. Re-run with override_risk=true and override_reason."
        if criticals and request.override_risk and not request.override_reason:
            return "override_reason is required when override_risk=true"
        return None

    def create_export(self, export_type: ExportType, request: ExportRequest) -> ExportResult:
        self._ensure_supported(export_type, request.formats)
        metadata = self.metadata_snapshot(request.project_id)
        risk = self._risk_gate(request, metadata)
        if risk:
            return ExportResult(
                export_id=str(uuid4()),
                export_type=export_type,
                created_at=datetime.now(UTC),
                output_files=[],
                manifest_path="",
                blocked=True,
                block_reason=risk,
            )

        export_id = f"exp_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
        out_dir = self.output_root / export_id
        out_dir.mkdir(parents=True, exist_ok=True)
        files_written: list[str] = []

        device_rows = metadata.get("device_metadata", [])
        cable_rows = metadata.get("cable_metadata", [])

        core_files = {
            "project_metadata.json": metadata.get("project_metadata", {}),
            "device_metadata.json": device_rows,
            "zone_metadata.json": metadata.get("zone_metadata", []),
            "cable_metadata.json": cable_rows,
            "validation_report.json": metadata.get("validation_metadata", []),
            "ai_review_report.json": metadata.get("ai_metadata", []),
            "revision_history.json": metadata.get("revision_metadata", []),
        }
        for name, payload in core_files.items():
            write_json(out_dir / name, payload)
            files_written.append(name)

        if "csv" in request.formats or export_type in {"project-package", "qa-package"}:
            write_csv(out_dir / "device_schedule.csv", device_rows)
            write_csv(out_dir / "cable_schedule.csv", cable_rows)
            write_csv(out_dir / "validation_report.csv", metadata.get("validation_metadata", []))
            files_written.extend(["device_schedule.csv", "cable_schedule.csv", "validation_report.csv"])

        if "xlsx" in request.formats:
            write_xlsx(
                out_dir / "schedules.xlsx",
                {"Devices": device_rows, "Cables": cable_rows, "Validation": metadata.get("validation_metadata", [])},
            )
            files_written.append("schedules.xlsx")

        if "geojson" in request.formats or export_type in {"project-package", "gis"}:
            write_json(out_dir / "coordinates.geojson", device_geojson_rows(device_rows))
            files_written.append("coordinates.geojson")

        if export_type in {"siteowl", "project-package"}:
            rows = siteowl_rows(device_rows, metadata["project_metadata"]["site_number"])
            write_csv(out_dir / "siteowl_import.csv", rows)
            files_written.append("siteowl_import.csv")

        if export_type in {"cad", "project-package"} or any(x in request.formats for x in ["svg", "png", "pdf", "dxf"]):
            files_written.extend([Path(x).name for x in cad_drawings(out_dir, device_rows)])

        if export_type in {"executive-report", "project-package", "qa-package"} or "pdf" in request.formats:
            summary_lines = [
                f"Project: {metadata['project_metadata']['project_name']}",
                f"Site: {metadata['project_metadata']['site_number']}",
                f"Devices: {len(device_rows)}",
                f"Zones: {len(metadata.get('zone_metadata', []))}",
                f"Cables: {len(cable_rows)}",
                f"Validation issues: {len(metadata.get('validation_metadata', []))}",
            ]
            write_pdf(out_dir / "executive_report.pdf", "CadOwl Executive Report", summary_lines)
            files_written.append("executive_report.pdf")

        manifest = build_manifest(export_id, export_type, request, metadata, files_written)
        write_json(out_dir / "manifest.json", manifest)
        files_written.append("manifest.json")

        package_path = None
        if "zip" in request.formats or export_type in {"project-package", "qa-package", "gis"}:
            package_path = write_zip(self.output_root / f"{export_id}.zip", out_dir, files_written)

        self.repo.append(
            ExportHistoryRecord(
                export_id=export_id,
                project_id=str(request.project_id),
                site_number=metadata["project_metadata"]["site_number"],
                export_type=export_type,
                export_mode=request.export_mode,
                created_by=request.created_by,
                created_at=datetime.now(UTC),
                files_included=files_written,
                record_counts=manifest["record_counts"],
                validation_score=manifest["validation_score"],
                coordinate_confidence=manifest["coordinate_confidence"],
                rollback_available=manifest["rollback_available"],
                metadata={"formats": request.formats, "package_path": package_path, "output_dir": str(out_dir)},
            )
        )

        return ExportResult(
            export_id=export_id,
            export_type=export_type,
            created_at=datetime.now(UTC),
            output_files=[str(out_dir / x) for x in files_written],
            manifest_path=str(out_dir / "manifest.json"),
            package_path=package_path,
        )


EXPORT_SERVICE = ExportService()
