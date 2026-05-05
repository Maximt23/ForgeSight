#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cad2siteowl.py - Convert DXF block insertions to SiteOwl coordinates

Usage:
    python cad2siteowl.py                    # Process all DXF in DXF folder
    python cad2siteowl.py path/to/file.dxf   # Process single file
"""

import csv
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import ezdxf
from ezdxf.entities import Insert

# =============================================================================
# CONFIGURATION
# =============================================================================

# Folders - use parent CADtoSiteOwl folder's Input/Output
SCRIPT_DIR = Path(__file__).parent.resolve()
PARENT_DIR = SCRIPT_DIR.parent  # CADtoSiteOwl folder
DXF_FOLDER = PARENT_DIR / "Input"
OUTPUT_FOLDER = PARENT_DIR / "Output"

# SiteOwl coordinate settings
ARTBOARD_SIZE = 1000.0
OBJECT_WIDTH = 800.0
SCALE_MODE = "WIDTH"  # "WIDTH" or "FIT"

# Device detection patterns (case-insensitive)
DEVICE_LAYER_PATTERNS = [
    r"notification",
    r".*e-alarm.*",
    r".*notf.*",
    r".*cctv.*",
    r".*camera.*",
    r".*security.*",
    r".*alarm.*",
    r"efp.*",
]

DEVICE_BLOCK_PATTERNS = [
    r"^scr$",
    r"^pc2r$",
    r"^p2rk$",
    r"^d4120$",
    r"^d9412$",
    r"^d1256$",
    r"^d273$",
    r"^fmm.*",
    r"^vsr$",
    r"^pcvs$",
    r"efp.*e-.*",
    r"^a\$c.*",
    r"^wmpoint$",
    r"cam.*",
    r"camera.*",
    r"dome.*",
    r"ptz.*",
    r"bullet.*",
    r"cctv.*",
]

# Blocks to EXCLUDE (title blocks, xrefs, borders, etc.)
EXCLUDE_BLOCK_PATTERNS = [
    r"^\*u\d+$",       # Anonymous blocks
    r"^\$rma\$$",      # Reference markers
    r"^xborder.*",     # Title block borders
    r"^xfloor.*",      # Floor plan xrefs
    r"^legend.*",      # Legend blocks
    r"^title.*",       # Title blocks
    r"^shttitle.*",    # Sheet titles
    r"^stamp.*",       # Stamps
    r"^aecb_.*",       # MEP connectors
]

# Attribute tags to try for device names (in order)
NAME_TAGS = ["NAME", "DEVICE", "D", "ID", "TAG", "S", "115CD", "WP", "CAMERA", "NUMBER"]

# =============================================================================
# SITEOWL CSV HEADERS
# =============================================================================

HEADERS = [
    "Project ID", "Plan ID", "Primary Device/Task ID", "Primary Device/Task Name",
    "Device ID", "Name", "Abbreviated Names", "Device / Task", "System Type",
    "Device/Task Type", "Part Number", "Manufacturer", "Budgeted Hours", "Budgeted Cost",
    "Assigned To", "Assigned To ID", "Date Due", "Installed/Completed By",
    "Installed/Completed By ID", "Date Installed/Completed", "Priority", "Install Status",
    "Operational Status", "Images", "Serial Number", "IP Address", "MAC Address",
    "Barcode", "IP / Analog", "Interior / Exterior", "Coverage Area", "Coverage Direction",
    "Coverage Angle", "Coverage Range", "Height (ft)", "IDF / MDF", "Hub", "Port",
    "Connection Length (feet)", "Description", "Flagged", "Date Flagged", "Flag Notes",
    "Instructions", "Field Notes", "Labor Warranty Expiration", "Device Warranty Expiration",
    "Replacement Cost", "Custom Device ID", "Project", "Site", "Building", "Plan",
    "Coordinates", "Archived", "Shareable Link"
]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class BoundingBox:
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    
    @property
    def width(self) -> float:
        return self.max_x - self.min_x
    
    @property
    def height(self) -> float:
        return self.max_y - self.min_y


@dataclass
class Device:
    block_name: str
    layer: str
    x: float
    y: float
    attributes: dict = field(default_factory=dict)
    
    @property
    def name(self) -> str:
        """Get device name from attributes or block name"""
        for tag in NAME_TAGS:
            if tag in self.attributes and self.attributes[tag]:
                return self.attributes[tag]
        return self.block_name
    
    @property
    def system_type(self) -> str:
        """Auto-detect system type"""
        layer_upper = self.layer.upper()
        block_upper = self.block_name.upper()
        
        if any(x in layer_upper or x in block_upper for x in ["CCTV", "CAM", "VIDEO", "SURV"]):
            return "Video Surveillance"
        elif any(x in layer_upper or x in block_upper for x in ["ALARM", "NOTIF", "EFP", "FIRE"]):
            return "Fire Alarm"
        elif any(x in layer_upper for x in ["INTRUSION", "BURG", "SECURITY"]):
            return "Intrusion Detection"
        return "Security"
    
    @property
    def device_type(self) -> str:
        """Auto-detect device type"""
        block_upper = self.block_name.upper()
        
        if self.system_type == "Video Surveillance":
            if "DOME" in block_upper:
                return "Dome Camera"
            elif "PTZ" in block_upper:
                return "PTZ Camera"
            elif "BULLET" in block_upper:
                return "Bullet Camera"
            return "Fixed Camera"
        
        elif self.system_type == "Fire Alarm":
            if any(x in block_upper for x in ["SCR", "PC2R", "STROBE"]):
                return "Horn/Strobe"
            elif "P2RK" in block_upper:
                return "Weatherproof Horn/Strobe"
            elif any(x in block_upper for x in ["D4120", "SD", "SMOKE"]):
                return "Smoke Detector"
            elif any(x in block_upper for x in ["PULL", "FMM"]):
                return "Pull Station"
            elif "SVTS" in block_upper:
                return "Supervisory Device"
            elif "SWFS" in block_upper:
                return "Waterflow Switch"
            return "Notification Device"
        
        return "Device"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def matches_any_pattern(text: str, patterns: list[str]) -> bool:
    """Check if text matches any regex pattern (case-insensitive)"""
    text_lower = text.lower()
    for pattern in patterns:
        if re.match(pattern, text_lower):
            return True
    return False


def extract_store_number(filename: str) -> str:
    """Extract 3-4 digit store number from filename"""
    match = re.search(r'\b(\d{3,4})\b', filename)
    return match.group(1) if match else "UNKNOWN"


def convert_to_siteowl(x: float, y: float, bbox: BoundingBox) -> tuple[float, float]:
    """Convert CAD coordinates to SiteOwl coordinates"""
    if bbox.width <= 0 or bbox.height <= 0:
        return (0, 0)
    
    if SCALE_MODE == "FIT":
        scale = OBJECT_WIDTH / max(bbox.width, bbox.height)
    else:
        scale = OBJECT_WIDTH / bbox.width
    
    scaled_w = bbox.width * scale
    scaled_h = bbox.height * scale
    
    offset_x = (ARTBOARD_SIZE - scaled_w) / 2.0
    offset_y = (ARTBOARD_SIZE - scaled_h) / 2.0
    
    # CAD X right = artboard X right
    art_x = offset_x + (x - bbox.min_x) * scale
    # CAD Y up, SiteOwl Y down - flip using max_y
    art_y = offset_y + (bbox.max_y - y) * scale
    
    # Convert to 0-100 range
    site_x = art_x / 10.0
    site_y = art_y / 10.0
    
    return (round(site_x, 2), round(site_y, 2))


# =============================================================================
# DXF PROCESSING
# =============================================================================

def find_boundary(doc: ezdxf.document.Drawing) -> Optional[BoundingBox]:
    """Find the boundary/extents of the drawing"""
    msp = doc.modelspace()
    
    # Try to find the largest closed polyline
    largest_area = 0
    largest_bbox = None
    
    for entity in msp.query("LWPOLYLINE"):
        if entity.closed:
            try:
                points = list(entity.get_points())
                if len(points) >= 3:
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    
                    # Simple area calculation (shoelace formula)
                    n = len(points)
                    area = abs(sum(
                        points[i][0] * points[(i+1) % n][1] - points[(i+1) % n][0] * points[i][1]
                        for i in range(n)
                    )) / 2.0
                    
                    if area > largest_area:
                        largest_area = area
                        largest_bbox = BoundingBox(
                            min_x=min(xs),
                            min_y=min(ys),
                            max_x=max(xs),
                            max_y=max(ys)
                        )
            except Exception:
                continue
    
    if largest_bbox:
        print(f"  Boundary: {largest_bbox.width:.0f} x {largest_bbox.height:.0f} (area: {largest_area:.0f})")
        return largest_bbox
    
    # Fallback: use all entity extents
    print("  WARNING: No closed polyline found, using drawing extents")
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    
    for entity in msp:
        try:
            bbox = entity.dxf.handle  # Just checking entity is valid
            if hasattr(entity.dxf, 'insert'):
                x, y = entity.dxf.insert.x, entity.dxf.insert.y
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
        except Exception:
            continue
    
    if min_x != float('inf'):
        return BoundingBox(min_x, min_y, max_x, max_y)
    
    return None


def extract_devices(doc: ezdxf.document.Drawing) -> list[Device]:
    """Extract device block insertions from DXF"""
    msp = doc.modelspace()
    devices = []
    
    for entity in msp.query("INSERT"):
        block_name = entity.dxf.name
        layer = entity.dxf.layer
        
        # Skip excluded blocks
        if matches_any_pattern(block_name, EXCLUDE_BLOCK_PATTERNS):
            continue
        
        # Check if it matches device patterns
        is_device_layer = matches_any_pattern(layer, DEVICE_LAYER_PATTERNS)
        is_device_block = matches_any_pattern(block_name, DEVICE_BLOCK_PATTERNS)
        
        if not (is_device_layer or is_device_block):
            continue
        
        # Get insertion point
        x = entity.dxf.insert.x
        y = entity.dxf.insert.y
        
        # Get attributes
        attributes = {}
        if entity.has_attrib:
            for attrib in entity.attribs:
                tag = attrib.dxf.tag.upper()
                text = attrib.dxf.text
                if text:
                    attributes[tag] = text
        
        devices.append(Device(
            block_name=block_name,
            layer=layer,
            x=x,
            y=y,
            attributes=attributes
        ))
    
    return devices


def make_row(device: Device, siteowl_coords: tuple[float, float], store_num: str) -> list[str]:
    """Create a CSV row for a device"""
    x, y = siteowl_coords
    coord_text = f"({x}, {y})"
    
    row = [""] * len(HEADERS)
    
    row[HEADERS.index("Primary Device/Task Name")] = device.name
    row[HEADERS.index("Name")] = device.name
    row[HEADERS.index("Abbreviated Names")] = device.block_name
    row[HEADERS.index("Device / Task")] = "Device"
    row[HEADERS.index("System Type")] = device.system_type
    row[HEADERS.index("Device/Task Type")] = device.device_type
    row[HEADERS.index("Interior / Exterior")] = "Interior"
    row[HEADERS.index("Description")] = f"Store {store_num} | Layer: {device.layer} | Block: {device.block_name}"
    row[HEADERS.index("Site")] = store_num
    row[HEADERS.index("Coordinates")] = coord_text
    
    return row


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def process_dxf(dxf_path: Path, output_folder: Path) -> int:
    """Process a single DXF file and output CSV"""
    print(f"\n[FILE] Processing: {dxf_path.name}")
    
    # Extract store number
    store_num = extract_store_number(dxf_path.stem)
    print(f"  Store: {store_num}")
    
    # Load DXF
    try:
        doc = ezdxf.readfile(str(dxf_path))
    except Exception as e:
        print(f"  ERROR: Failed to read DXF: {e}")
        return 0
    
    # Find boundary
    bbox = find_boundary(doc)
    if not bbox:
        print("  ERROR: Could not determine boundary!")
        return 0
    
    # Extract devices
    devices = extract_devices(doc)
    print(f"  Found {len(devices)} devices")
    
    if not devices:
        print("  WARNING: No devices found!")
        return 0
    
    # Ensure output folder exists
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Write CSV
    csv_path = output_folder / f"{store_num}_SiteOwl_Export.csv"
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        
        for device in devices:
            coords = convert_to_siteowl(device.x, device.y, bbox)
            row = make_row(device, coords, store_num)
            writer.writerow(row)
    
    print(f"  SUCCESS: Exported {csv_path.name}")
    return len(devices)


def main():
    """Main entry point"""
    print("\n" + "=" * 50)
    print("  CadOwl - DXF to SiteOwl Converter")
    print("=" * 50)
    
    # Determine input files
    if len(sys.argv) > 1:
        # Single file mode
        dxf_files = [Path(sys.argv[1])]
    else:
        # Batch mode - process DXF folder
        if not DXF_FOLDER.exists():
            print(f"\nERROR: DXF folder not found: {DXF_FOLDER}")
            print("   Run DWG2DXFBATCH in AutoCAD first to convert DWG files!")
            sys.exit(1)
        
        dxf_files = list(DXF_FOLDER.glob("*.dxf"))
        
        if not dxf_files:
            print(f"\nERROR: No DXF files found in: {DXF_FOLDER}")
            print("   Run DWG2DXFBATCH in AutoCAD first!")
            sys.exit(1)
    
    print(f"\n[*] Found {len(dxf_files)} DXF file(s)")
    print(f"[*] Output: {OUTPUT_FOLDER}")
    
    total_devices = 0
    processed = 0
    
    for dxf_path in dxf_files:
        count = process_dxf(dxf_path, OUTPUT_FOLDER)
        if count > 0:
            total_devices += count
            processed += 1
    
    print("\n" + "=" * 50)
    print(f"  COMPLETE!")
    print(f"  Processed: {processed}/{len(dxf_files)} files")
    print(f"  Total devices: {total_devices}")
    print(f"  Output: {OUTPUT_FOLDER}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
