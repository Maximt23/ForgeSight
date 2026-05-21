# 👁️ ForgeSight Vision

> **Camera/FOV Coverage Engine**

Optimize camera placement with intelligent field-of-view analysis and coverage mapping.

---

## Overview

ForgeSight Vision analyzes camera coverage to ensure complete surveillance with minimal blind spots. It provides:

- Field-of-view calculations
- Coverage heat maps
- Blind spot detection
- Optimal placement recommendations

---

## Features

### 📐 FOV Calculation

```python
from forgesight.vision import Camera, FOVCalculator

camera = Camera(
    type="dome",
    lens_mm=2.8,
    sensor_size="1/2.8",
    resolution=(1920, 1080),
    mount_height_ft=12
)

fov = FOVCalculator.compute(camera)
print(f"Horizontal FOV: {fov.h_degrees}°")
print(f"Vertical FOV: {fov.v_degrees}°")
print(f"Coverage at floor: {fov.floor_coverage_sqft} sq ft")
```

### 🗺️ Coverage Heat Map

```python
from forgesight.vision import CoverageAnalyzer

analyzer = CoverageAnalyzer(floor_plan)
analyzer.add_cameras(cameras)

heatmap = analyzer.generate_heatmap()
heatmap.save("coverage.png")

stats = analyzer.get_statistics()
print(f"Total coverage: {stats.coverage_percent}%")
print(f"Blind spots: {stats.blind_spot_count}")
```

### 🔍 Blind Spot Detection

```python
blind_spots = analyzer.find_blind_spots(min_area_sqft=50)

for spot in blind_spots:
    print(f"Blind spot at ({spot.x}, {spot.y})")
    print(f"  Area: {spot.area_sqft} sq ft")
    print(f"  Priority: {spot.priority}")
```

### 💡 Placement Recommendations

```python
from forgesight.vision import PlacementOptimizer

optimizer = PlacementOptimizer(
    floor_plan=floor_plan,
    existing_cameras=cameras,
    budget_cameras=5,
    min_coverage=95
)

recommendations = optimizer.optimize()

for rec in recommendations:
    print(f"Add {rec.camera_type} at ({rec.x}, {rec.y})")
    print(f"  Improves coverage by {rec.coverage_gain}%")
```

---

## Camera Models

### Supported Types

| Type | FOV Range | Best For |
|:-----|:----------|:---------|
| Dome | 90°-180° | Indoor, ceiling mount |
| PTZ | 60°-360° | Large areas, tracking |
| Bullet | 70°-110° | Outdoor, directional |
| Fisheye | 180°-360° | Wide coverage |
| Panoramic | 180°-360° | Hallways, aisles |

### Camera Database

```python
from forgesight.vision import CameraDatabase

# Get Bosch cameras
bosch_cams = CameraDatabase.query(manufacturer="Bosch")

# Get by model
cam = CameraDatabase.get("Bosch_Flexidome_5000i")
print(f"Lens: {cam.lens_mm}mm")
print(f"Sensor: {cam.sensor_size}")
```

---

## Visualization

### 3D View

```python
from forgesight.vision import Visualizer3D

viz = Visualizer3D(floor_plan)
viz.add_cameras(cameras, show_fov=True)
viz.add_coverage_overlay(heatmap)
viz.render("output.html")  # Interactive HTML
```

### Export Formats

| Format | Use Case |
|:-------|:---------|
| PNG | Reports, documentation |
| SVG | Scalable graphics |
| HTML | Interactive viewing |
| GeoJSON | GIS integration |

---

## API Endpoints

### Analyze Coverage

```http
POST /api/v1/vision/analyze
Content-Type: application/json

{
  "floor_plan_id": "uuid",
  "cameras": [
    {
      "type": "dome",
      "x": 45.2,
      "y": 32.1,
      "model": "Bosch_Flexidome_5000i"
    }
  ]
}
```

### Get Recommendations

```http
POST /api/v1/vision/recommend
Content-Type: application/json

{
  "floor_plan_id": "uuid",
  "existing_cameras": [...],
  "target_coverage": 95,
  "max_cameras": 10
}
```

---

## Integration

### With ForgeSight CAD

```python
# Import cameras from CAD
from forgesight.cad import DXFParser
from forgesight.vision import CoverageAnalyzer

parser = DXFParser("store.dxf")
cameras = parser.extract_cameras()

analyzer = CoverageAnalyzer(floor_plan)
analyzer.add_cameras(cameras)
```

### With ForgeSight AutoDesign

```python
# AI-powered optimization
from forgesight.autodesign import DesignAdvisor

advisor = DesignAdvisor()
suggestions = advisor.optimize_coverage(
    floor_plan=floor_plan,
    cameras=cameras,
    constraints={"budget": 50000}
)
```

---

## Related

- [ForgeSight CAD](ForgeSight-CAD.md) — Device extraction
- [ForgeSight Grid](ForgeSight-Grid.md) — Coordinate mapping
- [ForgeSight AutoDesign](ForgeSight-AutoDesign.md) — ML optimization
