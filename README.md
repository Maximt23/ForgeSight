# 🔮 ForgeSight AI

> **Enterprise Security Design Intelligence Platform**

[![CI](https://gecgithub01.walmart.com/vn59j7j/ForgeSight/workflows/CI/badge.svg)](https://gecgithub01.walmart.com/vn59j7j/ForgeSight/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## 🚀 Product Suite

| Product | Description | Status |
|:--------|:------------|:-------|
| **ForgeSight AI** | Main platform & unified dashboard | ✅ Stable |
| **ForgeSight CAD** | CAD/DXF/PDF design engine | ✅ Stable |
| **ForgeSight Field** | Mobile/VR site survey app | 🟡 Beta |
| **ForgeSight Vision** | Camera/FOV coverage engine | 🟡 Beta |
| **ForgeSight Grid** | GIS/coordinates/zoning engine | ✅ Stable |
| **ForgeSight Core** | API/data platform | ✅ Stable |
| **ForgeSight AutoDesign** | ML recommendation engine | 🔴 Alpha |

---

## ⚡ Quick Start

```bash
# Clone repository
git clone https://gecgithub01.walmart.com/vn59j7j/ForgeSight.git
cd ForgeSight

# Create virtual environment
uv venv

# Install dependencies
uv pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Start the API server
forgesight serve --port 9010
```

Open **http://localhost:9010** to access the dashboard.

---

## 📦 Installation

### Requirements

- Python 3.11+
- Walmart VPN or Eagle WiFi

### Install from Source

```bash
git clone https://gecgithub01.walmart.com/vn59j7j/ForgeSight.git
cd ForgeSight
uv venv
uv pip install -e .
```

---

## 🔧 Usage

### CLI Commands

```bash
# Convert CAD to SiteOwl CSV
forgesight cad convert drawing.dxf -o output.csv --store 1234

# Detect devices in CAD file
forgesight cad detect drawing.dxf --report

# Transform coordinates
forgesight grid transform --bounds "0,0,1000,500" --point "500,250"

# Analyze camera coverage
forgesight vision analyze --floor-plan plan.json --cameras cams.json

# Start API server
forgesight serve --port 9010 --reload
```

### Python API

```python
from forgesight.cad import DXFParser, DeviceDetector, SiteOwlExporter
from forgesight.grid import CoordinateTransformer, Bounds

parser = DXFParser("store_1234.dxf")
entities = parser.extract_blocks()

detector = DeviceDetector()
devices = detector.detect(entities)

bounds = Bounds.from_points([(d.x, d.y) for d in devices])
transformer = CoordinateTransformer()
transformer.set_bounds(bounds)

for device in devices:
    result = transformer.transform(device.x, device.y)
    print(f"{device.name}: ({result.site_x}, {result.site_y})")

exporter = SiteOwlExporter(store_number="1234")
exporter.export(devices, "output.csv")
```

---

## 🧠 Legacy Enhanced Converter Notes

The legacy `cad2siteowl_enhanced.py` path remains supported for teams using cross-reference with FA/Intrusion Excel masters.

```bash
python cad2siteowl_enhanced.py
python cad2siteowl_enhanced.py path/to/file.dxf --memory-db cadowl_memory.db
```

It merges CAD coordinates with Excel naming/type metadata and falls back safely for unmatched rows.

---

## 📖 Documentation

Full docs in [wiki](wiki/Home.md):

- [Quick Start](wiki/Quick-Start.md)
- [ForgeSight CAD](wiki/ForgeSight-CAD.md)
- [ForgeSight Field](wiki/ForgeSight-Field.md)
- [ForgeSight Vision](wiki/ForgeSight-Vision.md)
- [ForgeSight Grid](wiki/ForgeSight-Grid.md)
- [ForgeSight Core](wiki/ForgeSight-Core.md)
- [ForgeSight AutoDesign](wiki/ForgeSight-AutoDesign.md)
- [API Reference](wiki/Dev-API-Reference.md)

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
uv run pytest
uv run ruff check .
uv run mypy forgesight/
```

---

## 📄 License

Copyright © 2026 Walmart Inc. All rights reserved.

Internal use only. See [LICENSE](LICENSE).

---

## 🆘 Support

- **Teams**: [ForgeSight Support](https://teams.microsoft.com/l/channel/19%3AGbP8DGJjrXq1sL3IlXErZc5U7hk-IEqsokmnImcKyP41%40thread.tacv2/General?groupId=51caa2b5-ff58-4dc0-9ee0-c20eea1de9f8&tenantId=3cbcc3d3-094d-4006-9849-0d11d61f484d)
- **Slack**: [#forgesight-support](https://walmart.enterprise.slack.com/archives/C094Y1D24JY)
- **Issues**: [GitHub Issues](https://gecgithub01.walmart.com/vn59j7j/ForgeSight/issues)

---

*🔮 ForgeSight AI — Forging the Future of Security Design*
