"""
External system integrations for CadOwl.

Each subpackage wraps one external system with a clean Python API:
- doris: Walmart store metadata
- saone: Live camera health monitoring
- grafana: Network switch + port + PoE telemetry (SA Grafana)
- axis: Axis Site Designer project importer
- gis: GPS / OpenStreetMap / building footprints
- master: Bridge that correlates all of the above

These were originally prototyped in the MAXILLM sibling project and migrated
here for repository-of-record durability.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
See AUTHORS.md for attribution.
"""

__all__ = [
    "doris",
    "saone",
    "grafana",
    "axis",
    "gis",
    "master",
]
