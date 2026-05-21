# 🔌 Integrations Reference

CadOwl integrates with several Walmart and external systems. This document
describes each one — what it does, how we use it, and what to do when it
breaks.

---

## 🏪 Doris — Store Metadata

**System URL**: Internal Walmart store database  
**Auth**: Walmart SSO + API key  
**Module**: `packages/integrations/doris` (planned) / `src/integrations/doris.py` (current)

### What We Get
- Store number → name, address, GPS, type, region, market, size

### How We Use It
```python
from src.integrations.doris import doris

store = doris.get_store('3508')
# DorisStore(name='Walmart Supercenter #3508', city='Broken Arrow', ...)

data = doris.auto_populate_store_data('3508')
# Fills in every store field on a new CadOwl project automatically
```

### Caching
Results cached locally in `.doris_cache.json` (gitignored). TTL: 24h.

### Failure Modes
| Symptom | Cause | Fix |
|---------|-------|-----|
| `Store not found` | Number wrong or store closed | Verify in Doris UI |
| `API call failed` | VPN dropped | Reconnect, retry |
| `Cache stale` | Manual override needed | Delete `.doris_cache.json` |

---

## 🎥 Saone — Live Camera Health

**System URL**: https://saone.walmart.com/insights/connectivity/connectionAvailability  
**Auth**: Walmart SSO  
**Module**: `src/integrations/saone.py`

### What We Get
- Per-camera online/offline status
- Uptime %, latency, packet loss, bandwidth
- Live HLS stream URLs (for web playback)
- Alerts + warnings

### How We Use It
```python
from src.integrations.saone import saone

# Register a camera for monitoring
saone.register_device('cam-001', '192.168.1.101', 'AXIS P3245-LV')

# Get health
health = saone.get_camera_health('192.168.1.101')
# CameraHealth(is_online=True, uptime_percentage=98.4, latency_ms=15, ...)

# Get stream URL for embedding in UI
stream_url = saone.get_stream_url_for_ui('cam-001')
# 'https://saone.walmart.com/hls/192.168.1.101/playlist.m3u8'

# Whole-store summary
summary = saone.check_connectivity('3508')
# { 'total_cameras': 127, 'online': 124, 'offline': 2, 'degraded': 1 }
```

### Real-Time Updates
Use the WebSocket endpoint at `/api/cameras/ws/health` for live push.

### Failure Modes
| Symptom | Cause | Fix |
|---------|-------|-----|
| All cameras "offline" | Saone API down | Check Saone status page |
| Stream URL 403 | Auth token expired | Re-login |
| Missing camera | Not registered | Call `register_device` |

---

## 📊 SA Grafana — Switch + Port + PoE

**System URL**: https://sagrafana.sbox.walmart.com/login  
**Auth**: Walmart SSO + Grafana API key  
**Module**: `src/integrations/grafana.py`

### What We Get
- Network switch inventory per store
- Per-port: status, speed, VLAN, PoE state, PoE watts
- Camera-to-port mapping (via MAC/IP)
- Switch health: CPU, memory, temperature, uptime

### How We Use It
```python
from src.integrations.grafana import grafana

# All switches in a store
switches = grafana.get_switches_by_store('3508')
# [NetworkSwitch(hostname='sw-3508-01', model='Cisco Catalyst 9300-48P', ...)]

# Which switch port is this camera plugged into?
port_info = grafana.find_camera_port('192.168.1.101')
# { 'switch': ..., 'port': SwitchPort(port_number=12, poe_enabled=True, ...) }

# Why is this camera offline?
diagnosis = grafana.diagnose_camera_offline('192.168.1.101')
# {
#   'severity': 'high',
#   'diagnosis': ['Switch port 12 is DOWN'],
#   'recommendations': ['Check cable connection to camera']
# }

# Whole-store network health
summary = grafana.get_network_health_summary('3508')
```

### Why It Matters
When Saone says "camera offline" the **real** question is usually:
- Is the switch up? (Grafana)
- Is the port up? (Grafana)
- Is PoE delivering power? (Grafana)
- Are there CRC errors? (Grafana)

Grafana data turns "the camera is down" into "switch sw-3508-01 port 12
shows admin-down, enable it" — which an ops person can fix in 30 seconds.

### Failure Modes
| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 Unauthorized | API key expired | Regenerate in Grafana |
| No switches returned | Prometheus query mismatch | Update query for store schema |
| Wrong port mapping | Stale ARP cache | Force refresh on switch |

---

## 🎬 Axis Site Designer — Camera Layouts

**System URL**: https://sitedesigner.axis.com  
**Auth**: Axis account  
**Module**: `src/integrations/axis_designer.py`

### What We Get
- Camera positions (x, y, z)
- Pan/tilt orientation
- Camera model + specs (FOV, resolution, max distance)
- Coverage polygons

### How We Use It
Axis Site Designer doesn't have a public API, so we import **exported JSON
files**:

```python
from src.integrations.axis_designer import axis_importer
from pathlib import Path

cameras = axis_importer.import_from_json(Path("axis_export.json"))
devices = axis_importer.convert_to_siteowl_format(cameras, store_number='3508')

# Now devices are in CadOwl coordinate space (0-100, top-left origin)
```

### Supported Camera Models
- AXIS P3245-LV (dome)
- AXIS P3245-VE (outdoor dome)
- AXIS Q6155-E (PTZ)
- AXIS P1448-LE (4K bullet)
- AXIS M3057-PLVE (fisheye)
- (extend `_load_camera_specs()` for more)

### Coverage Calculation
Each camera's coverage polygon is computed from:
- Mounting height (z)
- Pan/tilt angles
- Horizontal FOV
- Effective max distance (accounting for tilt)

---

## 🗺️ OpenStreetMap — GIS / Geocoding

**System**: Nominatim + Overpass API  
**Auth**: None (rate-limited)  
**Module**: `src/gis/integration.py`

### What We Get
- Address → GPS (Nominatim geocoding)
- GPS → building footprint polygon (Overpass)
- Satellite tile URLs

### How We Use It
```python
from src.gis.integration import gis

# Geocode address
gps = gis.geocode_address("702 N Aspen Ave, Broken Arrow, OK")
# GPSCoordinate(latitude=36.0608, longitude=-95.7969)

# Get building footprint
footprint = gis.get_building_footprint('3508', address="...")
# BuildingFootprint with polygon coordinates

# Map 0-100 device coordinates to real GPS using building footprint
enriched = gis.generate_devices_with_gps(devices, '3508')
# Each device now has latitude/longitude

# Export to GeoJSON for QGIS / ArcGIS
gis.export_to_geojson(enriched, Path("store_3508.geojson"))
```

### Rate Limits
Nominatim: 1 req/sec. Overpass: be polite. Cache aggressively.

### Failure Modes
| Symptom | Cause | Fix |
|---------|-------|-----|
| `Geocoding failed` | Address typo | Use full street address |
| `No building found` | Building not in OSM | Manually trace and submit to OSM |
| Rate limit | Too many calls | Add backoff + caching |

---

## 📐 AutoCAD — DXF Parsing

**Library**: `ezdxf`  
**Module**: `packages/cad/dxf` (planned) / `cad2siteowl.py` (legacy)

### What We Get
- All INSERT entities (block references)
- Layer names + block names
- Insertion points

### How We Use It
Source DWG files go through a 2-step pipeline:
1. **DWG → DXF** via AutoCAD's `DWG2DXFBATCH` LISP macro
2. **DXF → CSV** via `cad2siteowl.py`

Output: SiteOwl-compatible CSV with coordinates pre-scaled to 0–100.

---

## 📑 SiteOwl — Legacy Export

**Module**: `packages/exports/siteowl` (planned)

### What We Export
- 56-column SiteOwl import format
- Coordinates in 0–100 range, top-left origin
- GPS in Barcode field (per SiteOwl convention)

### Status
SiteOwl is being phased out. Export remains for backward compatibility
until all consumers migrate to the CadOwl API directly.

---

## 🪟 VIVE-SiteOwl-XR — Field Survey Ingestion

**Repo**: https://github.com/Maximt23/VIVE-SiteOwl-XR-project  
**Module**: `packages/integrations/vive` (planned)

### What We Ingest
- Field survey CSV from headset
- Device photos
- GPS coordinates captured in headset
- Validation results (matches design vs. found in field)

### Schema
See `data/schemas/field-survey.schema.json` and `docs/vive-integration.md`.

---

## 🧠 Master Bridge — All Of The Above

The **Master Infrastructure Bridge** (`src/integrations/master_bridge.py`)
combines all integrations into a single coherent view:

```python
from src.integrations.master_bridge import master

infrastructure = master.build_full_infrastructure_view('3508', devices)
# {
#   'store': { ... Doris data ... },
#   'cameras': [ ... with Saone health + Grafana port mapping ... ],
#   'network': { ... Grafana switch summary ... },
#   'diagnosis': {
#     'critical': [...],
#     'high': [
#       { 'device': 'cam-045', 'issue': 'Switch port DOWN',
#         'recommendation': 'Enable port 12 on sw-3508-01' }
#     ],
#     'medium': [...],
#     'low': [...]
#   }
# }
```

This is the **killer feature** — one call gives you the complete operational
picture of a store with auto-diagnosis.

---

## Adding a New Integration

1. Create `packages/integrations/<name>/` (or `src/integrations/<name>.py` for now)
2. Define a dataclass for the external system's records
3. Implement a class with cache + retry + auth
4. Add a docs section here
5. Add tests under `tests/integration/<name>/`
6. Update `master_bridge.py` if it should feed the master view
7. Update `ECOSYSTEM.md` integration table

---

🐶 *Each integration earns its keep by saving a human at least 5 minutes.*
