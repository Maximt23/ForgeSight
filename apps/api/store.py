import json
import os
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Dict, List, Type
from uuid import UUID

from pydantic import BaseModel

from .schemas import Cable, Device, Event, Floor, MapModel, Project, Site, Zone


class JsonStore:
    """JSON-backed repository with append-only audit events."""

    FILE_MAP = {
        "projects": ("projects.json", Project),
        "sites": ("sites.json", Site),
        "floors": ("floors.json", Floor),
        "maps": ("maps.json", MapModel),
        "devices": ("devices.json", Device),
        "zones": ("zones.json", Zone),
        "cables": ("cables.json", Cable),
        "events": ("events.json", Event),
    }

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self._lock = RLock()

        self.projects: Dict[UUID, Project] = {}
        self.sites: Dict[UUID, Site] = {}
        self.floors: Dict[UUID, Floor] = {}
        self.maps: Dict[UUID, MapModel] = {}
        self.devices: Dict[UUID, Device] = {}
        self.zones: Dict[UUID, Zone] = {}
        self.cables: Dict[UUID, Cable] = {}
        self.events: List[Event] = []

        self._ensure_storage()
        self._load_all()

    def _ensure_storage(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        for file_name, _ in self.FILE_MAP.values():
            file_path = self.base_dir / file_name
            if not file_path.exists():
                file_path.write_text("[]", encoding="utf-8")

    def _read_json_array(self, key: str) -> list:
        file_name, _ = self.FILE_MAP[key]
        file_path = self.base_dir / file_name
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return payload
            return []
        except json.JSONDecodeError:
            # No fake success: reset corrupt file to empty list and continue safely.
            file_path.write_text("[]", encoding="utf-8")
            return []

    def _write_json_array(self, key: str, records: list) -> None:
        file_name, _ = self.FILE_MAP[key]
        file_path = self.base_dir / file_name
        file_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

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
            self.events = [Event.model_validate(x) for x in self._read_json_array("events")]

    def _stamp(self, model: BaseModel) -> BaseModel:
        if hasattr(model, "updated_at"):
            model.updated_at = datetime.utcnow()
        return model

    def _persist_entities(self, key: str, entities: Dict[UUID, BaseModel]) -> None:
        rows = [x.model_dump(mode="json") for x in entities.values()]
        self._write_json_array(key, rows)

    def _persist_events(self) -> None:
        self._write_json_array("events", [x.model_dump(mode="json") for x in self.events])

    def _event(self, event_type: str, entity_type: str, entity_id: UUID, actor: str = "system") -> Event:
        event = Event(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
        )
        self.events.append(event)
        self._persist_events()
        return event

    def _save(self, key: str, entity_map: Dict[UUID, BaseModel], model: BaseModel, entity_type: str):
        with self._lock:
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


def _resolve_jsondb_dir() -> Path:
    env_path = os.getenv("CADOWL_JSONDB_DIR")
    if env_path:
        return Path(env_path)
    return Path("C:/MAXILLM/cadowl/data/jsondb")


STORE = JsonStore(_resolve_jsondb_dir())
