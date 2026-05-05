# 🦉 CadOwl

**AutoLISP tools for exporting CAD device coordinates to SiteOwl format.**

Convert CCTV camera and device block insertion points from AutoCAD drawings into SiteOwl-compatible CSV coordinates.

---

## 📁 Scripts

| Script | Mode | Description |
|--------|------|-------------|
| `CAD2SITEOWL_AUTO.lsp` | **Automated** | Zero-touch batch processing. Auto-detects boundaries and devices. |
| `CAD2SITEOWL_MANUAL.lsp` | **Manual** | Interactive mode - prompts you to select boundary and devices. |
| `DWG_Analyzer.lsp` | **Diagnostic** | Analyzes a DWG and dumps layer/block structure to a text file. |

---

## 🚀 Quick Start

### Option 1: Automated (Recommended)

1. **Configure folders** (edit lines 22-23 in `CAD2SITEOWL_AUTO.lsp`):
   ```lisp
   (setq *SO_INPUT_FOLDER*  "C:\\path\\to\\Input")
   (setq *SO_OUTPUT_FOLDER* "C:\\path\\to\\Output")
   ```

2. **Load the script** in AutoCAD:
   ```
   (load "C:/path/to/CAD2SITEOWL_AUTO.lsp")
   ```

3. **Run commands:**
   - `CAD2SO` — Process the currently open drawing
   - `CAD2SOBATCH` — Batch process all DWGs in Input folder

### Option 2: Manual (Interactive)

1. Open your DWG in AutoCAD
2. Load the script:
   ```
   (load "C:/path/to/CAD2SITEOWL_MANUAL.lsp")
   ```
3. Run `CAD2SITEOWL`
4. Select your print boundary when prompted
5. Select device blocks when prompted
6. Choose CSV save location

---

## ⚙️ Configuration (Auto Mode)

Edit the config section at the top of `CAD2SITEOWL_AUTO.lsp`:

### Boundary Detection
```lisp
;; Method: "LAYER", "BLOCK", "LARGEST_POLY", or "DRAWING_EXTENTS"
(setq *SO_BOUNDARY_METHOD* "LARGEST_POLY")

;; If using LAYER method:
(setq *SO_BOUNDARY_LAYERS* "A-ANNO-TTLB*,*BOUNDARY*,*BORDER*")

;; If using BLOCK method:
(setq *SO_BOUNDARY_BLOCKS* "TITLEBLOCK*,BORDER*")
```

### Device Detection
```lisp
;; Layer patterns (wildcards OK)
(setq *SO_DEVICE_LAYERS* "S-CCTV*,*CCTV*,*CAMERA*,*SECURITY*")

;; Block name patterns (wildcards OK)
(setq *SO_DEVICE_BLOCKS* "CAM*,CAMERA*,DOME*,PTZ*,BULLET*")
```

### SiteOwl Coordinate Math
```lisp
(setq *SO_ARTBOARD_SIZE* 1000.0)  ; SiteOwl artboard size
(setq *SO_OBJECT_WIDTH*  800.0)   ; Floorplan scaled to this width
(setq *SO_SCALE_MODE*    "WIDTH") ; "WIDTH" or "FIT"
```

---

## 🧮 Coordinate Transformation

The scripts convert CAD insertion points to SiteOwl coordinates using this logic:

1. **Scale**: Boundary is scaled to fit 800 units wide on a 1000×1000 artboard
2. **Center**: Scaled boundary is centered on the artboard
3. **Flip Y**: CAD Y-up becomes SiteOwl Y-down (origin top-left)
4. **Divide by 10**: Final coordinates are 0-100 range

```
SiteOwl X = (CAD_X - MinX) × scale ÷ 10 + offset
SiteOwl Y = (MaxY - CAD_Y) × scale ÷ 10 + offset
```

---

## 📊 Output CSV Format

Exports 56-column SiteOwl-compatible CSV with headers:

- Project ID, Plan ID, Device ID, Name, Coordinates, etc.
- Auto-populates: Name, Abbreviated Names, Description, Coordinates
- Store number extracted from filename (3-4 digit patterns)

---

## 🔍 Analyzing Unknown DWGs

Run the diagnostic script to understand a DWG's structure:

```
(load "C:/path/to/DWG_Analyzer.lsp")
ANALYZEDWG
```

This creates a text file with:
- All layer names (with on/off/frozen/locked status)
- All block definitions
- Block inserts with layers and attributes
- Layers matching boundary keywords
- Layers matching device keywords
- Largest closed polylines (potential boundaries)

---

## 🛡️ Safety Features

- **Non-destructive**: Never modifies or saves source DWG files
- **Fallback chain**: If primary boundary detection fails, tries alternatives
- **Error handling**: Graceful recovery with logging
- **Logging**: Full processing log saved to Output folder

---

## 📋 Requirements

- AutoCAD 2018+ (or compatible)
- Visual LISP extensions (`vl-load-com`)

---

## 🐕 Support

Questions? Issues? Reach out or open an issue!

---

*Made with 🐶 by Code Puppy*
