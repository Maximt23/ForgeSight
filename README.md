# 🦉 CadOwl

**Convert CAD device coordinates to SiteOwl CSV format.**

Extract block insertion points (cameras, fire alarm devices, sensors) from AutoCAD drawings and export them as SiteOwl-compatible coordinates.

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://gecgithub01.walmart.com/vn59j7j/CadOwl.git
cd CadOwl
```

### 2. Run setup

```bash
SETUP.bat
```

This creates `Input/` and `Output/` folders and installs Python dependencies.

### 3. Convert your drawings

**Step A: DWG → DXF (in AutoCAD)**

1. Put your `.dwg` files in the `Input/` folder
2. Open AutoCAD (any drawing)
3. Run:
   ```lisp
   (load "C:/path/to/CadOwl/DWG2DXF.lsp")
   DWG2DXFBATCH
   ```

**Step B: DXF → CSV (Python)**

```bash
RUN_CONVERTER.bat
```

CSV files appear in `Output/` folder! 🎉

---

## 📁 Folder Structure

```
CadOwl/
├── Input/              ← Put DWG files here, DXF files saved here
├── Output/             ← CSV exports appear here
├── DWG2DXF.lsp         ← AutoCAD script (DWG → DXF)
├── cad2siteowl.py      ← Python script (DXF → CSV)
├── DWG_Analyzer.lsp    ← Diagnostic tool
├── SETUP.bat           ← One-time setup
└── RUN_CONVERTER.bat   ← Run the Python converter
```

---

## ⚙️ How It Works

### Two-Step Process

1. **AutoCAD** converts DWG to DXF (simple save-as operation)
2. **Python** reads DXF and extracts coordinates (reliable, debuggable)

### Why two steps?

- DWG is a proprietary binary format - only AutoCAD can read it
- DXF is an open text format - Python handles it easily
- If something breaks, you know exactly which step failed

### Coordinate Transformation

Converts CAD insertion points to SiteOwl's 0-100 coordinate system:

```
SiteOwl artboard: 1000 x 1000
Floorplan scaled to: 800 units wide (centered)
Final coordinates: divided by 10 → 0-100 range
Y-axis flipped: CAD Y-up → SiteOwl Y-down
```

---

## 🔧 Device Detection

The script auto-detects devices based on layer and block patterns:

### Supported Systems

| System | Layer Patterns | Block Patterns |
|--------|----------------|----------------|
| Fire Alarm | `*NOTIFICATION*`, `*E-ALARM*`, `*EFP*` | `SCR`, `PC2R`, `P2RK`, `D4120` |
| CCTV | `*CCTV*`, `*CAMERA*`, `*VIDEO*` | `CAM*`, `DOME*`, `PTZ*`, `BULLET*` |
| Intrusion | `*INTRUSION*`, `*BURG*`, `*SECURITY*` | - |

### Auto-Detected Device Types

- Horn/Strobe, Weatherproof Horn/Strobe
- Smoke Detector, Pull Station
- Supervisory Device, Waterflow Switch
- Fixed Camera, Dome Camera, PTZ Camera

---

## 🔍 Analyzing Unknown Drawings

If your drawings use different naming conventions, run the analyzer:

```lisp
(load "C:/path/to/CadOwl/DWG_Analyzer.lsp")
ANALYZEDWG
```

This creates a text file showing all layers, blocks, and their patterns. Use this to customize the detection patterns in `cad2siteowl.py`.

---

## 📋 CSV Output Format

Exports 56-column SiteOwl-compatible CSV with:

- Device Name (from attributes or block name)
- System Type (Fire Alarm, Video Surveillance, etc.)
- Device Type (Horn/Strobe, Fixed Camera, etc.)
- Coordinates in `(X, Y)` format
- Store number (extracted from filename)
- Layer and block info in Description

---

## 🛠️ Requirements

- **AutoCAD** 2018+ (for DWG → DXF conversion)
- **Python** 3.9+ with `uv` package manager
- **ezdxf** library (auto-installed by SETUP.bat)

---

## 📝 Commands Reference

### AutoCAD Commands

| Command | Description |
|---------|-------------|
| `DWG2DXF` | Convert current drawing to DXF |
| `DWG2DXFBATCH` | Convert all DWGs in Input folder |
| `ANALYZEDWG` | Dump layer/block info for debugging |

### Batch Files

| File | Description |
|------|-------------|
| `SETUP.bat` | One-time setup (creates folders, installs deps) |
| `RUN_CONVERTER.bat` | Run the Python DXF→CSV converter |

---

## 🐛 Troubleshooting

**"No DXF files found"**
- Run `DWG2DXFBATCH` in AutoCAD first

**"No devices found"**
- Your layer/block names might be different
- Run `ANALYZEDWG` and check the patterns
- Edit `cad2siteowl.py` to add your patterns

**"Module not found: ezdxf"**
- Run `SETUP.bat` again

**AutoCAD script won't load**
- Use forward slashes in the path: `C:/path/to/file.lsp`
- Or escape backslashes: `C:\\path\\to\\file.lsp`

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

Made with 🐶 by Code Puppy
