# 📐 ForgeSight CAD

> **CAD/DXF/PDF Design Engine**

Transform CAD drawings into actionable security designs with intelligent device detection and coordinate mapping.

---

## Overview

ForgeSight CAD is the design extraction engine that powers the ForgeSight platform. It takes raw CAD files (DXF, DWG, PDF) and extracts:

- Device locations and types
- Floor plan geometry
- Zone boundaries
- Cable pathways

---

## Features

### 🎯 Intelligent Device Detection

Pattern-based recognition for 100+ device types:

| Category | Devices |
|:---------|:--------|
| **CCTV** | Dome, PTZ, Bullet, Panoramic, Fisheye |
| **Fire Alarm** | Smoke, Heat, Duct, Pull Station, Horn/Strobe |
| **Intrusion** | Motion, Door Contact, Glass Break, Panic |
| **Access Control** | Card Reader, Keypad, Door Controller |

### 🗺️ Coordinate Transformation

Automatic mapping from CAD coordinates to SiteOwl format:

```python
from forgesight.cad import CoordinateTransformer

transformer = CoordinateTransformer(mode="FIT_CONTAIN")
transformer.set_bounds(cad_bounds)

result = transformer.transform(x=500, y=250)
print(f"SiteOwl: ({result.site_x}, {result.site_y})")
```

### 📊 Multi-Format Support

| Format | Support | Notes |
|:-------|:--------|:------|
| DXF | ✅ Full | All versions |
| DWG | ✅ Convert | Via ODA converter |
| PDF | 🟡 Beta | Raster & vector |

---

## Quick Start

### Command Line

```bash
# Convert DXF to SiteOwl CSV
forgesight cad convert drawing.dxf -o devices.csv --store 1234

# Analyze without converting
forgesight cad detect drawing.dxf --report

# Batch process directory
forgesight cad batch ./drawings/ -o ./output/
```

### Python API

```python
from forgesight.cad import DXFParser, DeviceDetector, SiteOwlExporter

# Parse DXF
parser = DXFParser("store_1234.dxf")
entities = parser.extract_blocks()

# Detect devices
detector = DeviceDetector()
devices = detector.detect(entities)

# Export
exporter = SiteOwlExporter(store_number="1234")
exporter.export(devices, "output.csv")

print(f"Detected {len(devices)} devices")
```

---

## Device Patterns

### Adding Custom Patterns

Edit `forgesight/cad/patterns.py`:

```python
BLOCK_PATTERNS = [
    # Existing patterns...
    
    # Add your custom patterns
    DevicePattern(
        pattern=r"(?i)^MY_COMPANY_CAM.*",
        system_type=SystemType.VIDEO_SURVEILLANCE,
        device_type=DeviceType.DOME_CAMERA,
        confidence=1.0,
        description="My Company dome cameras"
    ),
]
```

### Pattern Syntax

| Pattern | Matches |
|:--------|:--------|
| `(?i)` | Case insensitive |
| `^CAM_` | Starts with "CAM_" |
| `.*DOME.*` | Contains "DOME" |
| `_\d+$` | Ends with numbers |

---

## Coordinate Systems

### CAD Space
- Origin: Varies by drawing
- Units: Feet, inches, or millimeters
- Y-axis: Up (standard CAD)

### SiteOwl Space
- Artboard: 1000 × 1000 units
- Content: 800 × 800 centered
- Output: 0-100 range (artboard / 10)
- Y-axis: Down (web convention)

### Transformation Pipeline

```
CAD Coords → Normalize → Scale → Flip Y → Divide by 10 → SiteOwl
```

---

## Configuration

### Environment Variables

```bash
# Detection confidence threshold
FORGESIGHT_CAD_MIN_CONFIDENCE=0.7

# Default coordinate mode
FORGESIGHT_CAD_SCALE_MODE=FIT_CONTAIN

# Output format
FORGESIGHT_CAD_OUTPUT_FORMAT=siteowl
```

---

## Troubleshooting

### Devices Not Detected

1. Check block/layer naming conventions
2. Run with `--report` to see unmatched blocks
3. Add custom patterns for your devices

### Coordinates Wrong

1. Verify CAD drawing units
2. Check if Y-flip is needed
3. Use calibration points

### Large Files Slow

1. Use `--filter-layers` to limit scope
2. Enable caching with `--cache`
3. Process in batches

---

## Related

- [ForgeSight Grid](ForgeSight-Grid.md) — Coordinate engine
- [ForgeSight Vision](ForgeSight-Vision.md) — Coverage analysis
- [API Reference](Dev-API-Reference.md) — REST endpoints
