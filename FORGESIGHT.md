# 🔮 ForgeSight AI

> **Enterprise Security Design Intelligence Platform**

---

## Product Suite

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FORGESIGHT AI                                      │
│                    Enterprise Security Design Platform                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ ForgeSight  │  │ ForgeSight  │  │ ForgeSight  │  │ ForgeSight  │        │
│  │    CAD      │  │   Field     │  │   Vision    │  │    Grid     │        │
│  │             │  │             │  │             │  │             │        │
│  │ CAD/DXF/PDF │  │ Mobile Site │  │ Camera/FOV  │  │ GIS/Coords  │        │
│  │ Design      │  │ Survey App  │  │ Coverage    │  │ Zoning      │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │                │
│         └────────────────┴────────────────┴────────────────┘                │
│                                   │                                          │
│                                   ▼                                          │
│                        ┌─────────────────────┐                              │
│                        │   ForgeSight Core   │                              │
│                        │   API/Data Platform │                              │
│                        └──────────┬──────────┘                              │
│                                   │                                          │
│                                   ▼                                          │
│                      ┌─────────────────────────┐                            │
│                      │  ForgeSight AutoDesign  │                            │
│                      │  ML Design Intelligence │                            │
│                      └─────────────────────────┘                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Products

### 🔮 ForgeSight AI
**The Platform**

The unified enterprise security design intelligence platform that brings together all ForgeSight products into a cohesive ecosystem.

- Unified dashboard
- Cross-product workflows
- Enterprise SSO (Walmart)
- Audit & compliance

---

### 📐 ForgeSight CAD
**CAD/DXF/PDF Design Engine**

Transform CAD drawings into actionable security designs.

**Capabilities:**
- DXF/DWG import & parsing
- PDF floor plan extraction
- Device pattern recognition
- Coordinate transformation
- SiteOwl export

**Tech:** Python, ezdxf, PyMuPDF

---

### 📱 ForgeSight Field
**Mobile Site Survey App**

Capture real-world conditions with mobile and VR tools.

**Capabilities:**
- VIVE XR integration
- Photo documentation
- GPS/indoor positioning
- Offline-first PWA
- Real-time sync

**Tech:** Unity (VR), React Native (Mobile), PWA

---

### 👁️ ForgeSight Vision
**Camera/FOV Coverage Engine**

Optimize camera placement and coverage analysis.

**Capabilities:**
- Field-of-view calculation
- Coverage heat maps
- Blind spot detection
- Camera recommendation
- 3D visualization

**Tech:** Python, NumPy, Three.js

---

### 🗺️ ForgeSight Grid
**GIS/Coordinates/Zoning Engine**

Spatial intelligence for security design.

**Capabilities:**
- Coordinate transformation
- Zone management
- Geofencing
- Device matching
- Spatial queries

**Tech:** Python, PostGIS, Shapely

---

### ⚡ ForgeSight Core
**API/Data Platform**

The backbone of the ForgeSight ecosystem.

**Capabilities:**
- REST/GraphQL APIs
- Real-time events
- Data persistence
- Authentication
- Audit logging

**Tech:** FastAPI, PostgreSQL, Redis

---

### 🧠 ForgeSight AutoDesign
**ML Design Recommendation Engine**

AI-powered design assistance and optimization.

**Capabilities:**
- Design recommendations
- Anomaly detection
- Cost optimization
- Compliance checking
- Natural language queries

**Tech:** Python, Element AI, Pydantic AI

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTS                                  │
├───────────┬───────────┬───────────┬───────────┬────────────────┤
│    Web    │  Mobile   │  VIVE XR  │    CLI    │  Integrations  │
│  (React)  │  (RN/PWA) │  (Unity)  │  (Python) │  (REST API)    │
└─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┴───────┬────────┘
      │           │           │           │             │
      └───────────┴───────────┴───────────┴─────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FORGESIGHT CORE                               │
│              API Gateway + Authentication                        │
└─────────────────────────────────────────────────────────────────┘
                              │
      ┌───────────┬───────────┼───────────┬───────────┐
      ▼           ▼           ▼           ▼           ▼
┌──────────┐┌──────────┐┌──────────┐┌──────────┐┌──────────┐
│ForgeSight││ForgeSight││ForgeSight││ForgeSight││ForgeSight│
│   CAD    ││  Field   ││  Vision  ││   Grid   ││AutoDesign│
└────┬─────┘└────┬─────┘└────┬─────┘└────┬─────┘└────┬─────┘
     │           │           │           │           │
     └───────────┴───────────┴───────────┴───────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                 │
│         PostgreSQL + PostGIS + Redis + Object Storage           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Links

| Product | Documentation | Status |
|:--------|:--------------|:-------|
| ForgeSight AI | [Overview](wiki/Home.md) | ✅ Active |
| ForgeSight CAD | [CAD Guide](wiki/ForgeSight-CAD.md) | ✅ Stable |
| ForgeSight Field | [Field Guide](wiki/ForgeSight-Field.md) | 🟡 Beta |
| ForgeSight Vision | [Vision Guide](wiki/ForgeSight-Vision.md) | 🟡 Beta |
| ForgeSight Grid | [Grid Guide](wiki/ForgeSight-Grid.md) | ✅ Stable |
| ForgeSight Core | [API Reference](wiki/Dev-API-Reference.md) | ✅ Stable |
| ForgeSight AutoDesign | [AutoDesign Guide](wiki/ForgeSight-AutoDesign.md) | 🔴 Alpha |

---

## Getting Started

```bash
# Clone the repository
git clone https://gecgithub01.walmart.com/vn59j7j/ForgeSight.git
cd ForgeSight

# Install dependencies
uv venv && uv pip install -r requirements.txt

# Start the platform
uv run uvicorn forgesight.core.main:app --port 9010
```

---

## License

Copyright © 2026 Walmart Inc. All rights reserved.

Internal use only. See [LICENSE](LICENSE) for details.
