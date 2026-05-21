# 🦉 CadOwl Development Roadmap

## Overview

CadOwl v2.0 — Complete overhaul to improve accuracy, tooling, and reusability.

---

## 🎯 Goals

1. **Better device detection** — More patterns, smarter matching
2. **Accurate coordinate mapping** — Proper scaling, aspect ratio, floorplan alignment
3. **Robust Excel merging** — Fuzzy matching, confidence scores
4. **Modern tooling** — GUI, watcher, batch processing
5. **Shared core library** — Reusable X,Y mapping for VIVE XR

---

## 📋 Phase 1: Core Improvements (Week 1)

### 1.1 Device Detection Overhaul

- [ ] Add more device patterns from real DWG analysis
- [ ] Support attribute-based detection (not just block/layer names)
- [ ] Add confidence scoring to device matches
- [ ] Create device type classification model
- [ ] Output detection report with unmatched blocks

### 1.2 Coordinate Transformation v2

- [ ] Preserve aspect ratio properly
- [ ] Support multiple coordinate modes:
  - `FIT_WIDTH` - Scale to width, center vertically
  - `FIT_HEIGHT` - Scale to height, center horizontally
  - `FIT_CONTAIN` - Fit within bounds (no cropping)
  - `FIT_COVER` - Fill bounds (may crop)
- [ ] Add floorplan boundary detection (not just device bounds)
- [ ] Support custom origin/anchor points
- [ ] Add rotation handling

---

## 📋 Phase 2: Excel Integration (Week 1-2)

### 2.1 Smart Device Matching

- [ ] Fuzzy name matching (Levenshtein distance)
- [ ] Device type similarity scoring
- [ ] System type matching
- [ ] Position-based matching (nearest device)
- [ ] Confidence score output

### 2.2 Merge Strategies

- [ ] `EXCEL_PRIORITY` - Excel names, CAD coordinates
- [ ] `CAD_PRIORITY` - CAD data, Excel supplements
- [ ] `INTERACTIVE` - Ask for ambiguous matches
- [ ] Track merge audit trail

---

## 📋 Phase 3: Tooling & Automation (Week 2)

### 3.1 Modern GUI

- [ ] Drag-drop DWG/DXF files
- [ ] Live preview of device detection
- [ ] Interactive coordinate adjustment
- [ ] Excel file selection
- [ ] Batch processing queue
- [ ] Progress and error reporting

### 3.2 File Watcher v2

- [ ] Watch multiple folders
- [ ] Support DWG auto-conversion (ODA File Converter)
- [ ] Webhook/notification on completion
- [ ] Error recovery and retry logic

### 3.3 CLI Improvements

- [ ] `cadowl detect <file>` - Show detected devices\adowl convert <file>` - Full conversion
- [ ] `cadowl merge <cad> <excel>` - Merge with Excel
- [ ] `cadowl watch <folder>` - Start watcher
- [ ] JSON/YAML output options

---

## 📋 Phase 4: Shared Library (Week 2-3)

### 4.1 Extract Core Module

```python
from cadowl.core import CoordinateMapper, DeviceDetector, SiteOwlExporter

mapper = CoordinateMapper(mode="FIT_CONTAIN", artboard_size=1000)
devices = DeviceDetector().extract_from_dxf(doc)
mapper.transform(devices, bounds)
SiteOwlExporter().to_csv(devices, output_path)
```

### 4.2 VIVE XR Integration

- [ ] Create C# bindings or REST API
- [ ] Real-world → SiteOwl coordinate transformation
- [ ] GPS → floor plan position mapping
- [ ] Unity prefab for coordinate visualization

---

## 📋 Phase 5: Quality & Testing (Week 3)

### 5.1 Test Suite

- [ ] Unit tests for coordinate transforms
- [ ] Integration tests with sample DXF files
- [ ] Regression tests for known stores
- [ ] Visual diff testing for coordinate accuracy

### 5.2 Documentation

- [ ] API reference (Sphinx docs)
- [ ] Tutorial: Processing a new store
- [ ] Troubleshooting guide
- [ ] Pattern customization guide

---

## 🏗️ Architecture

```
cadowl/
├── core/
│   ├── __init__.py
│   ├── detector.py      # Device detection
│   ├── mapper.py        # Coordinate transformation
│   ├── merger.py        # Excel merge logic
│   └── exporter.py      # CSV/JSON output
├── parsers/
│   ├── dxf.py           # DXF parsing (ezdxf)
│   ├── dwg.py           # DWG conversion (ODA)
│   └── excel.py         # Excel parsing (openpyxl)
├── gui/
│   ├── app.py           # Main GUI (tkinter/PyQt)
│   └── preview.py       # Artboard preview
├── cli.py               # Click-based CLI
├── watcher.py           # File watcher
└── api.py               # REST API (FastAPI)
```

---

## 📊 Success Metrics

| Metric | Current | Target |
|:-------|:--------|:-------|
| Device detection rate | ~85% | 98%+ |
| Coordinate accuracy | ±5 units | ±1 unit |
| Processing time/store | ~10s | <3s |
| Unmatched devices | ~15% | <2% |

---

## 🚀 Let's Start!

Beginning with **Phase 1.2: Coordinate Transformation v2** since that's the foundation everything else builds on.