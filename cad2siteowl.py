#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cad2siteowl.py - Convert DXF block insertions to SiteOwl coordinates

Creates:
- CSV file with SiteOwl coordinates (0-100 range)
- DXF file showing devices on 1000x1000 artboard
- PDF visualization for verification

Usage:
    python cad2siteowl.py                    # Process all DXF in Input folder
    python cad2siteowl.py path/to/file.dxf   # Process single file
"""

import argparse
import csv
import re
import sys
import math
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

import ezdxf
from ezdxf import colors
from ezdxf.entities import Insert
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

# Local module for DWG→DXF conversion
try:
    from dwg_converter import get_cad_files, check_oda_status
    HAS_DWG_CONVERTER = True
except ImportError:
    HAS_DWG_CONVERTER = False
    def get_cad_files(folder, auto_convert=True):
        return list(Path(folder).glob("*.dxf"))

# =============================================================================
# CONFIGURATION
# =============================================================================

# Folders - use parent CADtoSiteOwl folder's Input/Output
SCRIPT_DIR = Path(__file__).parent.resolve()
PARENT_DIR = SCRIPT_DIR.parent  # CADtoSiteOwl folder
DXF_FOLDER = PARENT_DIR / "Input"
OUTPUT_FOLDER = PARENT_DIR / "Output"

# SiteOwl artboard settings
ARTBOARD_SIZE = 1000        # 1000 x 1000 artboard
FLOORPLAN_WIDTH = 800       # Scale floorplan to 800 units wide
MARGIN = 100                # 100 unit margin on each side (centered)

# Device detection patterns (case-insensitive regex)
DEVICE_LAYER_PATTERNS = [
    r".*notification.*",
    r".*e-alarm.*",
    r".*efp.*",
    r".*fire.*",
    r".*cctv.*",
    r".*camera.*",
    r".*video.*",
    r".*intrusion.*",
    r".*burg.*",
    r".*security.*",
]

DEVICE_BLOCK_PATTERNS = [
    r"^scr$",           # Horn/strobe
    r"^pc2r$",          # Horn/strobe
    r"^p2rk$",          # Weatherproof horn/strobe
    r"^d4120$",         # Smoke detector
    r".*smoke.*",
    r".*strobe.*",
    r".*horn.*",
    r".*pull.*",
    r".*cam.*",
    r".*dome.*",
    r".*ptz.*",
    r".*bullet.*",
    r"^a\$c.*",         # Anonymous blocks (fire alarm symbols)
    r".*swfs.*",        # Waterflow switch
    r".*svts.*",        # Supervisory
    r".*itjb.*",        # Junction box
    r".*swit.*",        # Switch
    r".*wmpoint.*",     # Walmart point
    r"^efp.*",          # Fire protection
    r"^e-.*",           # E- prefixed devices
]

EXCLUDE_BLOCK_PATTERNS = [
    r"^\*.*",           # Anonymous blocks starting with *
    r"^_.*",            # System blocks
    r".*title.*",       # Title blocks
    r".*border.*",      # Border blocks
    r".*legend.*",      # Legends
    r".*schedule.*",    # Schedules
    r".*detail.*",      # Details
    r".*viewport.*",    # Viewports
    r".*defpoints.*",   # Defpoints
    r"^aecb_.*",        # MEP connectors
]

# Attribute tags to try for device names (in order)
NAME_TAGS = ["NAME", "DEVICE", "D", "ID", "TAG", "S", "115CD", "WP", "CAMERA", "NUMBER"]

# =============================================================================
# SITEOWL CSV HEADERS (56 columns)
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
    
    @property
    def center_x(self) -> float:
        return (self.min_x + self.max_x) / 2
    
    @property
    def center_y(self) -> float:
        return (self.min_y + self.max_y) / 2


@dataclass
class Device:
    block_name: str
    layer: str
    cad_x: float      # Original CAD X
    cad_y: float      # Original CAD Y
    art_x: float = 0  # Artboard X (0-1000)
    art_y: float = 0  # Artboard Y (0-1000)
    site_x: float = 0 # SiteOwl X (0-100)
    site_y: float = 0 # SiteOwl Y (0-100)
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
    """Extract 3-5 digit store number from filename"""
    match = re.search(r'\b(\d{3,5})\b', filename)
    return match.group(1) if match else "UNKNOWN"


# =============================================================================
# COORDINATE TRANSFORMATION
# =============================================================================

def calculate_device_bounds(devices: List[Device]) -> Optional[BoundingBox]:
    """Calculate bounding box from device positions"""
    if not devices:
        return None
    
    xs = [d.cad_x for d in devices]
    ys = [d.cad_y for d in devices]
    
    return BoundingBox(
        min_x=min(xs),
        min_y=min(ys),
        max_x=max(xs),
        max_y=max(ys)
    )


def transform_coordinates(devices: List[Device], bbox: BoundingBox) -> None:
    """Transform CAD coordinates to SiteOwl coordinates (in place)"""
    if bbox.width <= 0 and bbox.height <= 0:
        return
    
    # Calculate scale to fit in 800x800 area (centered in 1000x1000)
    # Use the larger dimension to maintain aspect ratio
    cad_max_dim = max(bbox.width, bbox.height)
    if cad_max_dim <= 0:
        cad_max_dim = 1
    
    scale = FLOORPLAN_WIDTH / cad_max_dim
    
    # Calculate scaled dimensions
    scaled_w = bbox.width * scale
    scaled_h = bbox.height * scale
    
    # Offset to center in artboard
    offset_x = (ARTBOARD_SIZE - scaled_w) / 2.0
    offset_y = (ARTBOARD_SIZE - scaled_h) / 2.0
    
    for device in devices:
        # Transform to artboard coordinates (0-1000)
        # X: left-to-right stays the same
        device.art_x = offset_x + (device.cad_x - bbox.min_x) * scale
        
        # Y: CAD is Y-up, SiteOwl is Y-down, so flip
        device.art_y = offset_y + (bbox.max_y - device.cad_y) * scale
        
        # Transform to SiteOwl coordinates (0-100)
        device.site_x = round(device.art_x / 10.0, 2)
        device.site_y = round(device.art_y / 10.0, 2)


# =============================================================================
# DXF PROCESSING
# =============================================================================

def extract_devices(doc: ezdxf.document.Drawing) -> List[Device]:
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
                if text and text.strip():
                    attributes[tag] = text.strip()
        
        devices.append(Device(
            block_name=block_name,
            layer=layer,
            cad_x=x,
            cad_y=y,
            attributes=attributes
        ))
    
    return devices


# =============================================================================
# OUTPUT GENERATION
# =============================================================================

def create_artboard_dxf(devices: List[Device], output_path: Path, store_number: str) -> None:
    """Create a DXF showing devices on SiteOwl-style artboard"""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Create layers
    doc.layers.add("ARTBOARD", color=colors.GRAY)
    doc.layers.add("FLOORPLAN_AREA", color=colors.CYAN)
    doc.layers.add("DEVICES", color=colors.RED)
    doc.layers.add("LABELS", color=colors.YELLOW)
    doc.layers.add("GRID", color=colors.GRAY)
    
    # Draw 1000x1000 artboard boundary
    msp.add_lwpolyline(
        [(0, 0), (1000, 0), (1000, 1000), (0, 1000), (0, 0)],
        dxfattribs={"layer": "ARTBOARD", "lineweight": 50}
    )
    
    # Draw 800x800 floorplan area (centered)
    margin = (ARTBOARD_SIZE - FLOORPLAN_WIDTH) / 2
    msp.add_lwpolyline(
        [(margin, margin), (margin + 800, margin), 
         (margin + 800, margin + 800), (margin, margin + 800), (margin, margin)],
        dxfattribs={"layer": "FLOORPLAN_AREA", "linetype": "DASHED"}
    )
    
    # Draw grid lines every 100 units (10 in SiteOwl coords)
    for i in range(0, 1001, 100):
        msp.add_line((i, 0), (i, 1000), dxfattribs={"layer": "GRID"})
        msp.add_line((0, i), (1000, i), dxfattribs={"layer": "GRID"})
        # Add coordinate labels
        msp.add_text(str(i // 10), dxfattribs={"layer": "LABELS", "height": 15}).set_placement((i, -20))
        msp.add_text(str(i // 10), dxfattribs={"layer": "LABELS", "height": 15}).set_placement((-30, i))
    
    # Draw devices
    for i, device in enumerate(devices):
        # Draw circle for device
        msp.add_circle(
            (device.art_x, device.art_y), 
            radius=8,
            dxfattribs={"layer": "DEVICES"}
        )
        
        # Add device number
        msp.add_text(
            str(i + 1),
            dxfattribs={"layer": "LABELS", "height": 6}
        ).set_placement((device.art_x + 10, device.art_y))
    
    # Add title
    msp.add_text(
        f"Store {store_number} - SiteOwl Artboard Preview",
        dxfattribs={"layer": "LABELS", "height": 25}
    ).set_placement((500, 1050), align=ezdxf.enums.TextEntityAlignment.CENTER)
    
    msp.add_text(
        f"Devices: {len(devices)} | Artboard: 1000x1000 | SiteOwl: 0-100",
        dxfattribs={"layer": "LABELS", "height": 15}
    ).set_placement((500, 1020), align=ezdxf.enums.TextEntityAlignment.CENTER)
    
    doc.saveas(output_path)
    print(f"  Created artboard DXF: {output_path.name}")


def create_artboard_pdf(devices: List[Device], output_path: Path, store_number: str) -> None:
    """Create a PDF visualization of the artboard"""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        from matplotlib.patches import Circle, Rectangle
        from matplotlib.collections import PatchCollection
    except ImportError:
        print("  WARNING: matplotlib not installed, skipping PDF generation")
        return
    
    fig, ax = plt.subplots(1, 1, figsize=(12, 12))
    
    # Set up the artboard
    ax.set_xlim(-50, 1050)
    ax.set_ylim(-50, 1050)
    ax.set_aspect('equal')
    ax.set_facecolor('#f5f5f5')
    
    # Draw artboard boundary (1000x1000)
    artboard = Rectangle((0, 0), 1000, 1000, fill=True, 
                          facecolor='white', edgecolor='#333333', linewidth=2)
    ax.add_patch(artboard)
    
    # Draw floorplan area (800x800 centered)
    margin = (ARTBOARD_SIZE - FLOORPLAN_WIDTH) / 2
    floorplan = Rectangle((margin, margin), 800, 800, fill=False,
                          edgecolor='#0053e2', linewidth=1.5, linestyle='--')
    ax.add_patch(floorplan)
    
    # Draw grid
    for i in range(0, 1001, 100):
        ax.axhline(y=i, color='#cccccc', linewidth=0.5, zorder=1)
        ax.axvline(x=i, color='#cccccc', linewidth=0.5, zorder=1)
        # Labels
        ax.text(i, -15, str(i // 10), ha='center', va='top', fontsize=8, color='#666666')
        ax.text(-15, i, str(i // 10), ha='right', va='center', fontsize=8, color='#666666')
    
    # Draw devices
    for i, device in enumerate(devices):
        # Color by system type
        if device.system_type == "Fire Alarm":
            color = '#ea1100'  # Walmart red
        elif device.system_type == "Video Surveillance":
            color = '#0053e2'  # Walmart blue
        else:
            color = '#ffc220'  # Walmart spark
        
        circle = Circle((device.art_x, device.art_y), 12, 
                        facecolor=color, edgecolor='white', linewidth=1, zorder=3)
        ax.add_patch(circle)
        
        # Device number
        ax.text(device.art_x, device.art_y, str(i + 1), 
                ha='center', va='center', fontsize=6, color='white', fontweight='bold', zorder=4)
    
    # Title
    ax.set_title(f"Store {store_number} - SiteOwl Artboard Preview\n"
                 f"{len(devices)} devices | Artboard: 1000x1000 | SiteOwl coords: 0-100",
                 fontsize=14, fontweight='bold', pad=20)
    
    # Legend
    legend_y = -35
    ax.add_patch(Circle((750, legend_y), 8, facecolor='#ea1100', transform=ax.transData, clip_on=False))
    ax.text(765, legend_y, 'Fire Alarm', va='center', fontsize=9)
    ax.add_patch(Circle((850, legend_y), 8, facecolor='#0053e2', transform=ax.transData, clip_on=False))
    ax.text(865, legend_y, 'CCTV', va='center', fontsize=9)
    ax.add_patch(Circle((920, legend_y), 8, facecolor='#ffc220', transform=ax.transData, clip_on=False))
    ax.text(935, legend_y, 'Other', va='center', fontsize=9)
    
    # Remove axes
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  Created artboard PDF: {output_path.name}")


def write_csv(devices: List[Device], output_path: Path, store_number: str) -> None:
    """Write devices to SiteOwl CSV format"""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        
        for device in devices:
            row = {h: "" for h in HEADERS}
            row["Name"] = device.name
            row["Primary Device/Task Name"] = device.name
            row["Abbreviated Names"] = device.block_name
            row["Device / Task"] = "Device"
            row["System Type"] = device.system_type
            row["Device/Task Type"] = device.device_type
            row["Interior / Exterior"] = "Interior"
            row["Site"] = store_number
            row["Description"] = f"Store {store_number} | Layer: {device.layer} | Block: {device.block_name}"
            row["Coordinates"] = f"({device.site_x}, {device.site_y})"
            writer.writerow(row)
    
    print(f"  Created CSV: {output_path.name}")


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def process_dxf(dxf_path: Path, output_folder: Path) -> int:
    """Process a single DXF file"""
    print(f"\n[FILE] Processing: {dxf_path.name}")
    
    store_number = extract_store_number(dxf_path.stem)
    print(f"  Store: {store_number}")
    
    try:
        doc = ezdxf.readfile(str(dxf_path))
    except Exception as e:
        print(f"  ERROR: Could not read DXF: {e}")
        return 0
    
    # Extract devices
    devices = extract_devices(doc)
    if not devices:
        print("  WARNING: No devices found!")
        return 0
    
    print(f"  Found {len(devices)} devices")
    
    # Calculate bounds from device positions
    bbox = calculate_device_bounds(devices)
    if bbox:
        print(f"  CAD bounds: ({bbox.min_x:.0f}, {bbox.min_y:.0f}) to ({bbox.max_x:.0f}, {bbox.max_y:.0f})")
        print(f"  CAD size: {bbox.width:.0f} x {bbox.height:.0f}")
    
    # Transform coordinates
    transform_coordinates(devices, bbox)
    
    # Verify coordinates are in range
    out_of_range = sum(1 for d in devices if d.site_x < 0 or d.site_x > 100 or d.site_y < 0 or d.site_y > 100)
    if out_of_range > 0:
        print(f"  WARNING: {out_of_range} devices outside 0-100 range!")
    
    # Sample coordinates
    print(f"  Sample coords: ({devices[0].site_x}, {devices[0].site_y})")
    
    # Create output files
    output_folder.mkdir(exist_ok=True)
    base_name = f"{store_number}_SiteOwl"
    
    # CSV
    csv_path = output_folder / f"{base_name}_Export.csv"
    write_csv(devices, csv_path, store_number)
    
    # Artboard DXF
    dxf_out_path = output_folder / f"{base_name}_Artboard.dxf"
    create_artboard_dxf(devices, dxf_out_path, store_number)
    
    # Artboard PDF
    pdf_path = output_folder / f"{base_name}_Artboard.pdf"
    create_artboard_pdf(devices, pdf_path, store_number)
    
    print(f"  SUCCESS: {len(devices)} devices exported")
    return len(devices)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Convert DXF to SiteOwl CSV")
    parser.add_argument("file", nargs="?", help="Single DXF file to process")
    parser.add_argument("--input", "-i", type=Path, help="Input folder for DXF files")
    parser.add_argument("--output", "-o", type=Path, help="Output folder for results")
    parser.add_argument("--system", "-s", choices=["fa", "cctv"], default="fa",
                        help="System type (not used in basic mode, for compatibility)")
    args = parser.parse_args()
    
    # Determine input/output folders
    input_folder = args.input if args.input else DXF_FOLDER
    output_folder = args.output if args.output else OUTPUT_FOLDER
    
    print("\n" + "=" * 50)
    print("  CadOwl - DXF to SiteOwl Converter")
    print("=" * 50)
    
    # Handle command line arguments
    if args.file:
        dxf_files = [Path(args.file)]
    else:
        input_folder.mkdir(exist_ok=True)
        # Get DXF files (and auto-convert DWG if ODA is installed)
        dxf_files = get_cad_files(input_folder, auto_convert=True)
    
    if not dxf_files:
        print(f"\n[!] No DXF or DWG files found in {input_folder}")
        print("    Either install ODA File Converter or run DWG2DXFBATCH in AutoCAD.")
        return
    
    print(f"\n[*] Found {len(dxf_files)} CAD file(s)")
    print(f"[*] Input:  {input_folder}")
    print(f"[*] Output: {output_folder}")
    
    total_devices = 0
    success_count = 0
    
    for dxf_path in dxf_files:
        count = process_dxf(dxf_path, output_folder)
        if count > 0:
            total_devices += count
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"  COMPLETE!")
    print(f"  Processed: {success_count}/{len(dxf_files)} files")
    print(f"  Total devices: {total_devices}")
    print(f"  Output: {output_folder}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
