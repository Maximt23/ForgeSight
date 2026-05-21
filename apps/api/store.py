from collections import defaultdict
from datetime import datetime
from typing import Dict, List
from uuid import UUID

from .schemas import Cable, Device, Event, Floor, MapModel, Project, Site, Zone


class InMemoryStore:
    """Phase 1 contract store. Swap with DB repo in next step."""

    def __init__(self) -> None:
        self.projects: Dict[UUID, Project] = {}
        self.sites: Dict[UUID, Site] = {}
        self.floors: Dict[UUID, Floor] = {}
        self.maps: Dict[UUID, MapModel] = {}
        self.devices: Dict[UUID, Device] = {}
        self.zones: Dict[UUID, Zone] = {}
        self.cables: Dict[UUID, Cable] = {}
        self.events: List[Event] = []
        self.counters = defaultdict(int)

    def _stamp(self, model):
        model.updated_at = datetime.utcnow()
        return model

    def _event(self, event_type: str, entity_type: str, entity_id: UUID, actor: str = "system"):
        self.events.append(
            Event(
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                actor=actor,
            )
        )

    def add_project(self, project: Project):
        self.projects[project.id] = self._stamp(project)
        self._event("created", "project", project.id)
        return project

    def add_site(self, site: Site):
        self.sites[site.id] = self._stamp(site)
        self._event("created", "site", site.id)
        return site

    def add_floor(self, floor: Floor):
        self.floors[floor.id] = self._stamp(floor)
        self._event("created", "floor", floor.id)
        return floor

    def add_map(self, map_model: MapModel):
        self.maps[map_model.id] = self._stamp(map_model)
        self._event("created", "map", map_model.id)
        return map_model

    def add_device(self, device: Device):
        self.devices[device.id] = self._stamp(device)
        self._event("created", "device", device.id)
        return device

    def add_zone(self, zone: Zone):
        self.zones[zone.id] = self._stamp(zone)
        self._event("created", "zone", zone.id)
        return zone

    def add_cable(self, cable: Cable):
        self.cables[cable.id] = self._stamp(cable)
        self._event("created", "cable", cable.id)
        return cable


STORE = InMemoryStore()
