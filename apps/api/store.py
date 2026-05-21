import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional, Type
from uuid import UUID, uuid4

from pydantic import BaseModel

from .schemas import (
    Cable,
    Device,
    Event,
    Floor,
    ImportBatch,
    MapModel,
    Project,
    Site,
    Zone,
)


class JsonStore:
    """JSON-backed repository with schema checks, event ledger, snapshots, and rollback."""

    SNAPSHOT_EVERY_EVENTS = 10

    FILE_MAP = {
        "projects": ("projects.json", Project),
        "sites": ("sites.json", Site),
        "floors": ("floors.json", Floor),
        "maps": ("maps.json", MapModel),
        "devices": ("devices.json", Device),
        "zones": ("zones.json", Zone),
        "cables": ("cables.json", Cable),
        "import_batches": ("import_batches.json", ImportBatch),
        "events": ("events.json", Event),
    }

    def __init__(self, base_dir: Path, schema_dir: Path) -> None:
        self.base_dir = base_dir
        self.schema_dir = schema_dir
        self._lock = RLock()

        self.projects: Dict[UUID, Project] = {}
        self.sites: Dict[UUID, Site] = {}
        self.floors: Dict[UUID, Floor] = {}
        self.maps: Dict[UUID, MapModel] = {}
        self.devices: Dict[UUID, Device] = {}
        self.zones: Dict[UUID, Zone] = {}
        self.cables: Dict[UUID, Cable] = {}
        self.import_batches: Dict[UUID, ImportBatch] = {}
        self.events: list[Event] = []

        self.idempotency_index: Dict[str, dict[str, Any]] = {}

        self._ensure_storage()
        self._load_all()

    @property
    def ledger_path(self) -> Path:
        return self.base_dir / "event_ledger.jsonl"

    @property
    def snapshots_path(self) -> Path:
        return self.base_dir / "snapshots.json"

    @property
    def idempotency_path(self) -> Path:
        return self.base_dir / "idempotency_keys.json"

    def _ensure_storage(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        for file_name, _ in self.FILE_MAP.values():
            file_path = self.base_dir / file_name
            if not file_path.exists():
                file_path.write_text("[]", encoding="utf-8")

        if not self.ledger_path.exists():
            self.ledger_path.write_text("", encoding="utf-8")
        if not self.snapshots_path.exists():
            self.snapshots_path.write_text("[]", encoding="utf-8")
        if not self.idempotency_path.exists():
            self.idempotency_path.write_text("{}", encoding="utf-8")

    def _read_json(self, file_path: Path, default: Any):
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            file_path.write_text(json.dumps(default, indent=2), encoding="utf-8")
            return default

    def _write_json(self, file_path: Path, payload: Any) -> None:
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _read_json_array(self, key: str) -> list:
        file_name, _ = self.FILE_MAP[key]
        file_path = self.base_dir / file_name
        payload = self._read_json(file_path, [])
        return payload if isinstance(payload, list) else []

    def _write_json_array(self, key: str, records: list) -> None:
        file_name, _ = self.FILE_MAP[key]
        self._write_json(self.base_dir / file_name, records)

    def _deserialize_map(self, key: str, model_cls: Type[BaseModel]) -> Dict[UUID, BaseModel]:
        rows = self._read_json_array(key)
        mapped: Dict[UUID, BaseModel] = {}
        for row in rows:
            parsed = model_cls.model_validate(row)
            mapped[parsed.id] = parsed
        return mapped

    def _load_all(self) -> None:
        with self._lock:
            self.projects = self._deserialize_map("projects", Project)
            self.sites = self._deserialize_map("sites", Site)
            self.floors = self._deserialize_map("floors", Floor)
            self.maps = self._deserialize_map("maps", MapModel)
            self.devices = self._deserialize_map("devices", Device)
            self.zones = self._deserialize_map("zones", Zone)
            self.cables = self._deserialize_map("cables", Cable)
            self.import_batches = self._deserialize_map("import_batches", ImportBatch)
            self.events = [Event.model_validate(x) for x in self._read_json_array("events")]
            self.idempotency_index = self._read_json(self.idempotency_path, {})

    def _validate_json_schema(self, entity_type: str, payload: dict[str, Any]) -> None:
        schema_path = self.schema_dir / f"{entity_type}.api.schema.json"
        if not schema_path.exists():
            return

        schema = self._read_json(schema_path, {})
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for field in required:
            if field not in payload:
                raise ValueError(f"Schema validation failed: missing required field '{field}'")

        for field, rules in properties.items():
            if field not in payload:
                continue
            value = payload[field]
            rule_type = rules.get("type")
            if rule_type == "string" and not isinstance(value, str):
                raise ValueError(f"Schema validation failed: field '{field}' must be string")
            if rule_type == "integer" and not isinstance(value, int):
                raise ValueError(f"Schema validation failed: field '{field}' must be integer")
            if rule_type == "number" and not isinstance(value, (int, float)):
                raise ValueError(f"Schema validation failed: field '{field}' must be number")
            if rule_type == "object" and not isinstance(value, dict):
                raise ValueError(f"Schema validation failed: field '{field}' must be object")
            if rule_type == "array" and not isinstance(value, list):
                raise ValueError(f"Schema validation failed: field '{field}' must be array")

            min_len = rules.get("minLength")
            if min_len is not None and isinstance(value, str) and len(value.strip()) < min_len:
                raise ValueError(f"Schema validation failed: field '{field}' length must be >= {min_len}")

    def _stamp(self, model: BaseModel) -> BaseModel:
        if hasattr(model, "updated_at"):
            model.updated_at = datetime.utcnow()
        return model

    def _persist_entities(self, key: str, entities: Dict[UUID, BaseModel]) -> None:
        rows = [x.model_dump(mode="json") for x in entities.values()]
        self._write_json_array(key, rows)

    def _persist_events(self) -> None:
        self._write_json_array("events", [x.model_dump(mode="json") for x in self.events])

    def _append_ledger(self, event: Event) -> None:
        with self.ledger_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(event.model_dump(mode="json")) + "\n")

    def _state_hash(self) -> str:
        combined = {
            "projects": [x.model_dump(mode="json") for x in self.projects.values()],
            "sites": [x.model_dump(mode="json") for x in self.sites.values()],
            "floors": [x.model_dump(mode="json") for x in self.floors.values()],
            "maps": [x.model_dump(mode="json") for x in self.maps.values()],
            "devices": [x.model_dump(mode="json") for x in self.devices.values()],
            "zones": [x.model_dump(mode="json") for x in self.zones.values()],
            "cables": [x.model_dump(mode="json") for x in self.cables.values()],
            "import_batches": [x.model_dump(mode="json") for x in self.import_batches.values()],
        }
        text = json.dumps(combined, sort_keys=True)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _snapshot(self, reason: str) -> dict[str, Any]:
        snapshots = self._read_json(self.snapshots_path, [])
        latest_event_id = str(self.events[-1].id) if self.events else None
        snapshot = {
            "snapshot_id": str(uuid4()),
            "created_at": datetime.utcnow().isoformat(),
            "reason": reason,
            "latest_event_id": latest_event_id,
            "state_hash": self._state_hash(),
            "state": {
                "projects": [x.model_dump(mode="json") for x in self.projects.values()],
                "sites": [x.model_dump(mode="json") for x in self.sites.values()],
                "floors": [x.model_dump(mode="json") for x in self.floors.values()],
                "maps": [x.model_dump(mode="json") for x in self.maps.values()],
                "devices": [x.model_dump(mode="json") for x in self.devices.values()],
                "zones": [x.model_dump(mode="json") for x in self.zones.values()],
                "cables": [x.model_dump(mode="json") for x in self.cables.values()],
                "import_batches": [x.model_dump(mode="json") for x in self.import_batches.values()],
            },
        }
        snapshots.append(snapshot)
        self._write_json(self.snapshots_path, snapshots)
        return snapshot

    def _event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: UUID,
        actor: str = "system",
        metadata: Optional[dict[str, Any]] = None,
    ) -> Event:
        event = Event(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            metadata=metadata or {},
        )
        self.events.append(event)
        self._persist_events()
        self._append_ledger(event)

        if len(self.events) % self.SNAPSHOT_EVERY_EVENTS == 0:
            self._snapshot("auto-compaction")

        return event

    def _save(self, key: str, entity_map: Dict[UUID, BaseModel], model: BaseModel, entity_type: str):
        with self._lock:
            row = model.model_dump(mode="json")
            self._validate_json_schema(entity_type, row)
            entity_map[model.id] = self._stamp(model)
            self._persist_entities(key, entity_map)
            self._event("created", entity_type, model.id)
            return model

    def add_project(self, project: Project):
        return self._save("projects", self.projects, project, "project")

    def add_site(self, site: Site):
        return self._save("sites", self.sites, site, "site")

    def add_floor(self, floor: Floor):
        return self._save("floors", self.floors, floor, "floor")

    def add_map(self, map_model: MapModel):
        return self._save("maps", self.maps, map_model, "map")

    def add_device(self, device: Device):
        return self._save("devices", self.devices, device, "device")

    def add_zone(self, zone: Zone):
        return self._save("zones", self.zones, zone, "zone")

    def add_cable(self, cable: Cable):
        return self._save("cables", self.cables, cable, "cable")

    def add_import_batch(self, batch: ImportBatch):
        return self._save("import_batches", self.import_batches, batch, "import_batch")

    def idempotent_execute(
        self,
        key: str,
        operation: str,
        request_payload: dict[str, Any],
        result_factory,
    ) -> dict[str, Any]:
        payload_hash = hashlib.sha256(json.dumps(request_payload, sort_keys=True).encode("utf-8")).hexdigest()
        composite_key = f"{operation}:{key}"

        existing = self.idempotency_index.get(composite_key)
        if existing:
            if existing.get("payload_hash") != payload_hash:
                raise ValueError("Idempotency key reuse with different payload is forbidden")
            return existing["response"]

        result = result_factory()
        self.idempotency_index[composite_key] = {
            "payload_hash": payload_hash,
            "response": result,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._write_json(self.idempotency_path, self.idempotency_index)
        return result

    def rollback_to_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        snapshots = self._read_json(self.snapshots_path, [])
        target = next((s for s in snapshots if s.get("snapshot_id") == snapshot_id), None)
        if not target:
            raise ValueError(f"Snapshot '{snapshot_id}' not found")

        state = target["state"]
        self.projects = {Project.model_validate(x).id: Project.model_validate(x) for x in state["projects"]}
        self.sites = {Site.model_validate(x).id: Site.model_validate(x) for x in state["sites"]}
        self.floors = {Floor.model_validate(x).id: Floor.model_validate(x) for x in state["floors"]}
        self.maps = {MapModel.model_validate(x).id: MapModel.model_validate(x) for x in state["maps"]}
        self.devices = {Device.model_validate(x).id: Device.model_validate(x) for x in state["devices"]}
        self.zones = {Zone.model_validate(x).id: Zone.model_validate(x) for x in state["zones"]}
        self.cables = {Cable.model_validate(x).id: Cable.model_validate(x) for x in state["cables"]}
        self.import_batches = {
            ImportBatch.model_validate(x).id: ImportBatch.model_validate(x) for x in state["import_batches"]
        }

        self._persist_entities("projects", self.projects)
        self._persist_entities("sites", self.sites)
        self._persist_entities("floors", self.floors)
        self._persist_entities("maps", self.maps)
        self._persist_entities("devices", self.devices)
        self._persist_entities("zones", self.zones)
        self._persist_entities("cables", self.cables)
        self._persist_entities("import_batches", self.import_batches)

        rollback_id = uuid4()
        self._event(
            "rollback",
            "system",
            rollback_id,
            metadata={"snapshot_id": snapshot_id, "restored_event_id": target.get("latest_event_id")},
        )

        return {
            "restored_snapshot_id": snapshot_id,
            "restored_event_id": target.get("latest_event_id"),
            "restored_at": datetime.utcnow().isoformat(),
        }

    def list_snapshots(self) -> list[dict[str, Any]]:
        return self._read_json(self.snapshots_path, [])


def _resolve_jsondb_dir() -> Path:
    env_path = os.getenv("CADOWL_JSONDB_DIR")
    if env_path:
        return Path(env_path)
    return Path("C:/MAXILLM/cadowl/data/jsondb")


def _resolve_schema_dir() -> Path:
    env_path = os.getenv("CADOWL_SCHEMA_DIR")
    if env_path:
        return Path(env_path)
    return Path("C:/MAXILLM/cadowl/apps/api/schemas_json")


STORE = JsonStore(_resolve_jsondb_dir(), _resolve_schema_dir())
