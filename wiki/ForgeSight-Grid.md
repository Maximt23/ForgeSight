# 🗺️ ForgeSight Grid

> **GIS/Coordinates/Zoning Engine**

Spatial intelligence for security design with coordinate transformation, zone management, and device matching.

---

## Overview

ForgeSight Grid is the spatial engine that powers coordinate transformation and zone management across the ForgeSight platform.

---

## Features

### 🔄 Coordinate Transformation

Transform coordinates between any source system and SiteOwl format.

```python
from forgesight.grid import CoordinateTransformer, Bounds, ScaleMode

# Define source bounds
bounds = Bounds(min_x=0, min_y=0, max_x=1000, max_y=500)

# Create transformer
transformer = CoordinateTransformer(
    mode=ScaleMode.FIT_CONTAIN,
    flip_y=True  # CAD Y-up to Web Y-down
)
transformer.set_bounds(bounds)

# Transform point
result = transformer.transform(500, 250)
print(f"SiteOwl: ({result.site_x}, {result.site_y})")

# Get transformation matrix
matrix = transformer.get_transform_matrix()
# [[0.8, 0, 100], [0, -0.8, 900], [0, 0, 1]]
```

### 🗺️ Zone Management

Define and manage zones within floor plans.

```python
from forgesight.grid import Zone, ZoneManager

manager = ZoneManager(floor_plan)

# Create zones
manager.add_zone(Zone(
    name="Grocery",
    type="retail",
    polygon=[(0, 0), (100, 0), (100, 50), (0, 50)]
))

manager.add_zone(Zone(
    name="Pharmacy",
    type="restricted",
    polygon=[(100, 0), (150, 0), (150, 30), (100, 30)]
))

# Check device zone
zone = manager.get_zone_at(x=45.2, y=32.1)
print(f"Device is in: {zone.name}")
```

### 🎯 Device Matching

Match devices from multiple sources (CAD, VR, manual).

```python
from forgesight.grid import DeviceMatcher, MatchConfig

matcher = DeviceMatcher(config=MatchConfig(
    tolerance=0.05,        # 5% of floor diagonal
    min_confidence=0.7,
    use_attributes=True
))

# Match CAD devices to VR survey
result = matcher.match(cad_devices, vr_devices)

print(f"Matched: {len(result.matched)}")
print(f"Unmatched CAD: {len(result.unmatched_source)}")
print(f"Unmatched VR: {len(result.unmatched_target)}")

for pair in result.matched:
    print(f"  {pair.source.name} → {pair.target.name}")
    print(f"    Distance: {pair.distance:.2f}")
    print(f"    Confidence: {pair.confidence:.0%}")
```

### 📐 Geofencing

Define boundaries and check device compliance.

```python
from forgesight.grid import Geofence

fence = Geofence(floor_plan)

# Check if device is within bounds
if fence.is_inside(x=45.2, y=32.1):
    print("Device is within floor plan")
else:
    print("WARNING: Device outside boundaries!")

# Get distance to boundary
distance = fence.distance_to_edge(x=45.2, y=32.1)
print(f"Distance to edge: {distance} units")
```

---

## Scale Modes

| Mode | Description |
|:-----|:------------|
| `FIT_WIDTH` | Scale to match width, center vertically |
| `FIT_HEIGHT` | Scale to match height, center horizontally |
| `FIT_CONTAIN` | Fit within bounds without cropping (default) |
| `FIT_COVER` | Fill bounds, may crop edges |
| `STRETCH` | Stretch to fill (distorts aspect ratio) |

---

## Coordinate Systems

### SiteOwl Format

```
┌────────────────────────────────┐
│  Artboard: 1000 × 1000        │
│  ┌──────────────────────────┐ │
│  │                          │ │
│  │  Floorplan: 800 × 800    │ │
│  │  (centered)              │ │
│  │                          │ │
│  └──────────────────────────┘ │
│         100px margin          │
└────────────────────────────────┘

Output: artboard / 10 = 0-100 range
```

### Transformation Matrix

```
┌         ┐   ┌                    ┐   ┌   ┐
│ art_x   │   │ scale_x  0   tx   │   │ x │
│ art_y   │ = │ 0  scale_y   ty   │ × │ y │
│ 1       │   │ 0    0       1    │   │ 1 │
└         ┘   └                    ┘   └   ┘
```

---

## API Endpoints

### Transform Coordinates

```http
POST /api/v1/grid/transform
Content-Type: application/json

{
  "bounds": {
    "min_x": 0, "min_y": 0,
    "max_x": 1000, "max_y": 500
  },
  "points": [
    {"x": 500, "y": 250},
    {"x": 100, "y": 100}
  ],
  "mode": "FIT_CONTAIN",
  "flip_y": true
}
```

### Match Devices

```http
POST /api/v1/grid/match
Content-Type: application/json

{
  "source_devices": [...],
  "target_devices": [...],
  "tolerance": 0.05
}
```

### Get Zone

```http
GET /api/v1/grid/zones/{floor_id}/at?x=45.2&y=32.1
```

---

## Cross-Platform Support

ForgeSight Grid is implemented in both Python and C# for cross-platform use:

| Platform | File | Use Case |
|:---------|:-----|:---------|
| Python | `shared/transform/transform_core.py` | Backend, CLI |
| C# | `shared/transform/TransformCore.cs` | Unity, VIVE XR |

Both implementations use identical math for consistency.

---

## Related

- [ForgeSight CAD](ForgeSight-CAD.md) — Device extraction
- [ForgeSight Field](ForgeSight-Field.md) — VR coordinates
- [Device Matching Algorithm](../shared/matching/README.md) — Details
