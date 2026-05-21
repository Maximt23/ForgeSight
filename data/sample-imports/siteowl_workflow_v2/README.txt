================================================================================
  SITEOwl WORKFLOW TOOL - ASDPX to CSV Converter with Floorplan Editor
================================================================================

📧 SHAREABLE PACKAGE
   This folder contains everything needed to run the SiteOwl workflow tool.
   No installation required - just double-click the HTML file!

--------------------------------------------------------------------------------
🚀 QUICK START
--------------------------------------------------------------------------------

1. Double-click "SiteOwl_Workflow.html" to open in any web browser
   (Chrome, Firefox, Edge, Safari all supported)

2. STEP 1 - IMPORT:
   • Drag & drop your .asdpx file (from Axis SiteDesigner)
   • Or click to browse and select the file
   • The tool auto-converts to SiteOwl CSV format

3. STEP 2 - PREVIEW:
   • Review all 56 columns of data
   • Verify GPS coordinates appear in Field Notes column
   • Check Device/Task Types are SiteOwl-approved
   • Scroll horizontally ↔ to see all fields

4. STEP 3 - FLOORPLAN EDITOR:
   • Drag devices to reposition them
   • Toggle coverage cones on/off
   • Toggle floorplan image on/off  
   • View pricing estimates
   • Delete unwanted devices (auto-scales floorplan!)

5. EXPORT:
   • Click "Download CSV" to save your SiteOwl import file
   • Or "Export CSV" from the floorplan editor

--------------------------------------------------------------------------------
📋 FILE FORMATS
--------------------------------------------------------------------------------

INPUT:  .asdpx files (Axis SiteDesigner export)
OUTPUT: .csv files (SiteOwl standard format, 56 columns)

The CSV includes:
- Project/Plan IDs (blank for manual entry)
- Device IDs (New0001, New0002, etc.)
- Camera model names & part numbers
- System Type: Video Surveillance
- Device/Task Type: Dome Camera, Bullet Camera, PTZ Camera, etc.
- Coverage: Direction (0-360°), Angle, Range
- Height in feet
- GPS coordinates in Field Notes column
- Coordinates: (XX.XX, YY.YY) format for SiteOwl
- Pricing data (if available in ASDPX)

--------------------------------------------------------------------------------
🎯 FEATURES
--------------------------------------------------------------------------------

✓ Single-file HTML (no installation, no internet needed)
✓ 80% Width Rule: Floorplan scales to 80% of artboard width
✓ Auto-converts GPS → pixels → feet → display coordinates
✓ SiteOwl-approved Device/Task Types:
  • Dome Camera, Bullet Camera, PTZ Camera
  • Panoramic Camera, Fisheye Camera
  • Network Switch, Camera Accessory
  • General Video Surveillance (for audio/intercoms)
✓ Field Notes column includes GPS coordinates (lat, lng)
✓ Pricing panel with unit costs and totals
✓ Coverage cone visualization
✓ Draggable device editing
✓ Real-time CSV export

--------------------------------------------------------------------------------
📁 INCLUDED FILES
--------------------------------------------------------------------------------

SiteOwl_Workflow.html    - Main application (self-contained)
README.txt               - This file

--------------------------------------------------------------------------------
🔧 TROUBLESHOOTING
--------------------------------------------------------------------------------

Issue: "No floorPlan found in file"
→ Your ASDPX export must include the floorplan image. Re-export from 
   SiteDesigner with floorplan visible.

Issue: "No valid devices found"
→ Check that your ASDPX has installation points with valid GPS coordinates.

Issue: Coordinates look wrong
→ Verify the building dimensions shown in Step 2 match your actual building.

Issue: Browser won't open file
→ Right-click HTML → Open With → Choose Chrome/Firefox/Edge

--------------------------------------------------------------------------------
📊 SUPPORTED AXIS DEVICES
--------------------------------------------------------------------------------

Cameras:
• M3077-PLVE (Fisheye)
• M3088-V (Dome)
• P1488-LE, P1518-LE (Bullet)
• P3288-LV (Dome)
• P3738-PLE, P4708-PLVE (Panoramic)
• P5655-E (PTZ)
• Q3839-PVE, Q4809-PVE (Panoramic)
• Q9307-LV (Dome)

Forensic Analytics:
• FA51-B, FA54 Main Units
• FA1105 Sensor Unit

Audio:
• C1720 Speaker

Network:
• D8248 PoE++ Switch
• D8308 Fiber Switch

Access Control:
• I8307-VE Intercom

--------------------------------------------------------------------------------
💡 TIPS
--------------------------------------------------------------------------------

• The tool works 100% offline - no internet connection needed
• All processing happens in your browser (data stays private)
• Use Chrome or Edge for best performance with large files
• The floorplan editor uses a 100x100 unit viewBox
• Coordinates auto-format to (00.00, 00.00) for SiteOwl compatibility

--------------------------------------------------------------------------------
📞 SUPPORT
--------------------------------------------------------------------------------

This is a standalone HTML tool created for SiteOwl workflow automation.
For issues or feature requests, contact the tool author.

Version: 1.0 (May 2025)
Requirements: Modern web browser (Chrome 80+, Firefox 75+, Edge 80+)

================================================================================
                     Happy SiteOwl importing! 🦉📹
================================================================================
