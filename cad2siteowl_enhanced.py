#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cad2siteowl_enhanced.py - Convert DXF blocks to SiteOwl with Excel cross-reference

This enhanced version merges:
- Accurate COORDINATES from CAD extraction
- Correct NAMES, SYSTEM TYPES, and DEVICE TYPES from master Excel files

Usage:
    python cad2siteowl_enhanced.py                    # Process all DXF in Input folder
    python cad2siteowl_enhanced.py path/to/file.dxf   # Process single file
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from difflib import SequenceMatcher

import ezdxf
from ezdxf.entities import Insert

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR = Path(__file__).parent.resolve()
DXF_FOLDER = SCRIPT_DIR / "Input"
OUTPUT_FOLDER = SCRIPT_DIR / "Output"

# Master Excel folders for reference data
MASTER_EXCEL_FA = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey")
MASTER_EXCEL_CCTV = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CCTV STORES DATA - Survey")

# SiteOwl coordinate settings
ARTBOARD_SIZE = 1000.0
OBJECT_WIDTH = 800.0
SCALE_MODE = "WIDTH"

# Device detection patterns (case-insensitive)
DEVICE_LAYER_PATTERNS = [
    r"notification", r".*e-alarm.*", r".*notf.*", r".*cctv.*",
    r".*camera.*", r".*security.*", r".*alarm.*", r"efp.*",
    r".*intrusion.*", r".*burg.*", r".*motion.*", r".*door.*",
]

DEVICE_BLOCK_PATTERNS = [
    r"^scr$", r"^pc2r$", r"^p2rk$", r"^d4120$", r"^d9412$", r"^d1256$",
    r"^d273$", r"^fmm.*", r"^vsr$", r"^pcvs$", r"efp.*e-.*", r"^a\$c.*",
    r"^wmpoint$", r"cam.*", r"camera.*", r"dome.*", r"ptz.*", r"bullet.*",
    r"cctv.*", r"^pull.*", r"^motion.*", r"^door.*", r"^smoke.*",
    r"^tamper.*", r"^flow.*", r"^rtu.*", r"^ps\d*$", r"^panic.*",
]

EXCLUDE_BLOCK_PATTERNS = [
    r"^\*u\d+$", r"^\$rma\$$", r"^xborder.*", r"^xfloor.*",
    r"^legend.*", r"^title.*", r"^shttitle.*", r"^stamp.*", r"^aecb_.*",
]

NAME_TAGS = ["NAME", "DEVICE", "D", "ID", "TAG", "S", "115CD", "WP", "CAMERA", "NUMBER", "LABEL"]

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
class ExcelDevice:
    """Device data from master Excel file"""
    name: str
    abbreviated_name: str
    system_type: str
    device_type: str
    description: str
    matched: bool = False
    
    @property
    def match_keywords(self) -> set:
        """Extract keywords for fuzzy matching"""
        text = f"{self.name} {self.description}".upper()
        # Extract meaningful words
        words = re.findall(r'[A-Z]+', text)
        return set(w for w in words if len(w) > 2)


@dataclass
class CadDevice:
    """Device extracted from CAD/DXF"""
    block_name: str
    layer: str
    x: float
    y: float
    attributes: dict = field(default_factory=dict)
    
    @property
    def raw_name(self) -> str:
        """Get device name from attributes or block name"""
        for tag in NAME_TAGS:
            if tag in self.attributes and self.attributes[tag]:
                return self.attributes[tag]
        return self.block_name
    
    @property
    def match_keywords(self) -> set:
        """Extract keywords for fuzzy matching"""
        text = f"{self.block_name} {self.layer} {self.raw_name}".upper()
        words = re.findall(r'[A-Z]+', text)
        return set(w for w in words if len(w) > 2)
    
    @property
    def inferred_system_type(self) -> str:
        """Auto-detect system type from CAD data"""
        layer_upper = self.layer.upper()
        block_upper = self.block_name.upper()
        name_upper = self.raw_name.upper()
        combined = f"{layer_upper} {block_upper} {name_upper}"
        
        if any(x in combined for x in ["CCTV", "CAM", "VIDEO", "SURV"]):
            return "Video Surveillance"
        elif any(x in combined for x in ["MOTION", "BURG", "DOOR", "INTRUSION"]):
            return "Intrusion Detection"
        elif any(x in combined for x in ["ALARM", "NOTIF", "EFP", "FIRE", "PULL", "SMOKE", "FLOW", "RTU", "TAMPER"]):
            return "Fire Alarm"
        return "Fire Alarm"  # Default to Fire Alarm


# =============================================================================
# EXCEL LOADING
# =============================================================================

def load_master_excel(store_num: str, system_type: str = "fa") -> list[ExcelDevice]:
    """Load device data from master Excel for a store
    
    Args:
        store_num: Store number
        system_type: 'fa' for Fire Alarm/Intrusion, 'cctv' for CCTV
    """
    # Select correct folder based on system type
    if system_type == "cctv":
        master_folder = MASTER_EXCEL_CCTV
        patterns = [
            f"Store_{store_num}_CCTV.csv",
            f"Store_{int(store_num)}_CCTV.csv",
            f"{store_num}_CCTV.csv",
        ]
    else:
        master_folder = MASTER_EXCEL_FA
        patterns = [
            f"Store_{store_num}_FA_Intrusion.csv",
            f"Store_{int(store_num)}_FA_Intrusion.csv",
        ]
    
    excel_path = None
    for pattern in patterns:
        path = master_folder / pattern
        if path.exists():
            excel_path = path
            break
    
    if not excel_path:
        print(f"  WARNING: No master Excel found for store {store_num} ({system_type})")
        return []
    
    print(f"  Loading master Excel: {excel_path.name}")
    
    devices = []
    try:
        with open(excel_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('Name', '').strip()
                if not name:
                    continue
                
                devices.append(ExcelDevice(
                    name=name,
                    abbreviated_name=row.get('Abbreviated Name', '').strip(),
                    system_type=row.get('System Type', '').strip(),
                    device_type=row.get('Device/Task Type', '').strip(),
                    description=row.get('Description', '').strip(),
                ))
    except Exception as e:
        print(f"  ERROR reading Excel: {e}")
        return []
    
    print(f"  Found {len(devices)} devices in master Excel")
    return devices


# =============================================================================
# MATCHING LOGIC
# =============================================================================

def similarity_score(text1: str, text2: str) -> float:
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, text1.upper(), text2.upper()).ratio()


def keyword_overlap(set1: set, set2: set) -> float:
    """Calculate keyword overlap score"""
    if not set1 or not set2:
        return 0.0
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union) if union else 0.0


def match_cad_to_excel(cad_device: CadDevice, excel_devices: list[ExcelDevice]) -> Optional[ExcelDevice]:
    """Find the best matching Excel device for a CAD device"""
    if not excel_devices:
        return None
    
    best_match = None
    best_score = 0.0
    
    cad_keywords = cad_device.match_keywords
    cad_system = cad_device.inferred_system_type
    
    for excel_dev in excel_devices:
        if excel_dev.matched:
            continue  # Already used
        
        score = 0.0
        
        # System type match is important
        if excel_dev.system_type == cad_system:
            score += 0.3
        elif excel_dev.system_type and cad_system:
            # Partial match (Fire Alarm vs Fire, etc.)
            if cad_system[:4].upper() in excel_dev.system_type.upper():
                score += 0.15
        
        # Keyword overlap
        excel_keywords = excel_dev.match_keywords
        overlap = keyword_overlap(cad_keywords, excel_keywords)
        score += overlap * 0.4
        
        # Name similarity
        name_sim = similarity_score(cad_device.raw_name, excel_dev.name)
        score += name_sim * 0.2
        
        # Abbreviated name match (if CAD has a number)
        cad_numbers = re.findall(r'\d+', cad_device.raw_name)
        if cad_numbers and excel_dev.abbreviated_name:
            if excel_dev.abbreviated_name in cad_numbers:
                score += 0.1
        
        if score > best_score:
            best_score = score
            best_match = excel_dev
    
    # Only return if we have a reasonable match (>0.25)
    if best_match and best_score > 0.25:
        best_match.matched = True
        return best_match
    
    return None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def matches_any_pattern(text: str, patterns: list[str]) -> bool:
    """Check if text matches any regex pattern"""
    text_lower = text.lower()
    for pattern in patterns:
        if re.match(pattern, text_lower):
            return True
    return False


def extract_store_number(filename: str) -> str:
    """Extract store number from filename"""
    match = re.search(r'\b(\d{3,5})\b', filename)
    return match.group(1) if match else "UNKNOWN"


def convert_to_siteowl(x: float, y: float, bbox: BoundingBox) -> tuple[float, float]:
    """Convert CAD coordinates to SiteOwl coordinates"""
    if bbox.width <= 0 or bbox.height <= 0:
        return (0, 0)
    
    scale = OBJECT_WIDTH / (max(bbox.width, bbox.height) if SCALE_MODE == "FIT" else bbox.width)
    
    scaled_w = bbox.width * scale
    scaled_h = bbox.height * scale
    
    offset_x = (ARTBOARD_SIZE - scaled_w) / 2.0
    offset_y = (ARTBOARD_SIZE - scaled_h) / 2.0
    
    art_x = offset_x + (x - bbox.min_x) * scale
    art_y = offset_y + (bbox.max_y - y) * scale
    
    site_x = art_x / 10.0
    site_y = art_y / 10.0
    
    return (round(site_x, 2), round(site_y, 2))


# =============================================================================
# DXF PROCESSING
# =============================================================================

def find_boundary(doc: ezdxf.document.Drawing) -> Optional[BoundingBox]:
    """Find the boundary/extents of the drawing"""
    msp = doc.modelspace()
    
    largest_area = 0
    largest_bbox = None
    
    for entity in msp.query("LWPOLYLINE"):
        if entity.closed:
            try:
                points = list(entity.get_points())
                if len(points) >= 3:
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    
                    n = len(points)
                    area = abs(sum(
                        points[i][0] * points[(i+1) % n][1] - points[(i+1) % n][0] * points[i][1]
                        for i in range(n)
                    )) / 2.0
                    
                    if area > largest_area:
                        largest_area = area
                        largest_bbox = BoundingBox(min(xs), min(ys), max(xs), max(ys))
            except Exception:
                continue
    
    if largest_bbox:
        print(f"  Boundary: {largest_bbox.width:.0f} x {largest_bbox.height:.0f}")
        return largest_bbox
    
    # Fallback to entity extents
    print("  WARNING: No closed polyline, using entity extents")
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    
    for entity in msp:
        try:
            if hasattr(entity.dxf, 'insert'):
                x, y = entity.dxf.insert.x, entity.dxf.insert.y
                min_x, max_x = min(min_x, x), max(max_x, x)
                min_y, max_y = min(min_y, y), max(max_y, y)
        except Exception:
            continue
    
    return BoundingBox(min_x, min_y, max_x, max_y) if min_x != float('inf') else None


def extract_devices(doc: ezdxf.document.Drawing) -> list[CadDevice]:
    """Extract device block insertions from DXF"""
    msp = doc.modelspace()
    devices = []
    
    for entity in msp.query("INSERT"):
        block_name = entity.dxf.name
        layer = entity.dxf.layer
        
        if matches_any_pattern(block_name, EXCLUDE_BLOCK_PATTERNS):
            continue
        
        is_device_layer = matches_any_pattern(layer, DEVICE_LAYER_PATTERNS)
        is_device_block = matches_any_pattern(block_name, DEVICE_BLOCK_PATTERNS)
        
        if not (is_device_layer or is_device_block):
            continue
        
        x = entity.dxf.insert.x
        y = entity.dxf.insert.y
        
        attributes = {}
        if entity.has_attrib:
            for attrib in entity.attribs:
                tag = attrib.dxf.tag.upper()
                text = attrib.dxf.text
                if text:
                    attributes[tag] = text
        
        devices.append(CadDevice(
            block_name=block_name,
            layer=layer,
            x=x,
            y=y,
            attributes=attributes
        ))
    
    return devices


def make_row(
    cad_device: CadDevice,
    excel_match: Optional[ExcelDevice],
    siteowl_coords: tuple[float, float],
    store_num: str
) -> list[str]:
    """Create a CSV row merging CAD coordinates with Excel naming"""
    x, y = siteowl_coords
    coord_text = f"({x}, {y})"
    
    row = [""] * len(HEADERS)
    
    if excel_match:
        # Use Excel data for naming
        row[HEADERS.index("Primary Device/Task Name")] = excel_match.name
        row[HEADERS.index("Name")] = excel_match.name
        row[HEADERS.index("Abbreviated Names")] = excel_match.abbreviated_name
        row[HEADERS.index("System Type")] = excel_match.system_type
        row[HEADERS.index("Device/Task Type")] = excel_match.device_type
        row[HEADERS.index("Description")] = excel_match.description
    else:
        # Fall back to CAD-derived data
        row[HEADERS.index("Primary Device/Task Name")] = cad_device.raw_name
        row[HEADERS.index("Name")] = cad_device.raw_name
        row[HEADERS.index("Abbreviated Names")] = cad_device.block_name
        row[HEADERS.index("System Type")] = cad_device.inferred_system_type
        row[HEADERS.index("Device/Task Type")] = "Device"
        row[HEADERS.index("Description")] = f"[UNMATCHED] Block: {cad_device.block_name} | Layer: {cad_device.layer}"
    
    row[HEADERS.index("Device / Task")] = "Device"
    row[HEADERS.index("Interior / Exterior")] = "Interior"
    row[HEADERS.index("Site")] = store_num
    row[HEADERS.index("Coordinates")] = coord_text  # FROM CAD - the accurate coordinates!
    
    return row


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def process_dxf(dxf_path: Path, output_folder: Path, system_type: str = "fa") -> int:
    """Process a single DXF file with Excel cross-reference"""
    print(f"\n[FILE] Processing: {dxf_path.name}")
    
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
    
    # Extract CAD devices
    cad_devices = extract_devices(doc)
    print(f"  Found {len(cad_devices)} devices in CAD")
    
    if not cad_devices:
        print("  WARNING: No devices found in CAD!")
        return 0
    
    # Load master Excel for this store (using correct system type)
    excel_devices = load_master_excel(store_num, system_type)
    
    # Match devices
    matched_count = 0
    unmatched_count = 0
    
    output_folder.mkdir(parents=True, exist_ok=True)
    csv_path = output_folder / f"{store_num}_SiteOwl_Enhanced.csv"
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        
        for cad_dev in cad_devices:
            coords = convert_to_siteowl(cad_dev.x, cad_dev.y, bbox)
            
            # Try to find matching Excel device
            excel_match = match_cad_to_excel(cad_dev, excel_devices)
            
            if excel_match:
                matched_count += 1
            else:
                unmatched_count += 1
            
            row = make_row(cad_dev, excel_match, coords, store_num)
            writer.writerow(row)
    
    print(f"  ✅ Matched: {matched_count} | ❌ Unmatched: {unmatched_count}")
    print(f"  SUCCESS: Exported {csv_path.name}")
    
    return len(cad_devices)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Convert DXF to SiteOwl CSV with Excel cross-reference")
    parser.add_argument("file", nargs="?", help="Single DXF file to process")
    parser.add_argument("--input", "-i", type=Path, help="Input folder for DXF files")
    parser.add_argument("--output", "-o", type=Path, help="Output folder for results")
    parser.add_argument("--system", "-s", choices=["fa", "cctv"], default="fa",
                        help="System type: 'fa' for Fire Alarm/Intrusion, 'cctv' for CCTV")
    args = parser.parse_args()
    
    # Determine input/output folders
    input_folder = args.input if args.input else DXF_FOLDER
    output_folder = args.output if args.output else OUTPUT_FOLDER
    system_type = args.system
    
    # Select correct master Excel folder
    master_folder = MASTER_EXCEL_CCTV if system_type == "cctv" else MASTER_EXCEL_FA
    
    print("\n" + "=" * 60)
    print(f"  CadOwl Enhanced - DXF + Excel Cross-Reference ({system_type.upper()})")
    print("=" * 60)
    
    if args.file:
        dxf_files = [Path(args.file)]
    else:
        if not input_folder.exists():
            print(f"\nERROR: DXF folder not found: {input_folder}")
            sys.exit(1)
        dxf_files = list(input_folder.glob("*.dxf"))
        if not dxf_files:
            print(f"\nERROR: No DXF files found in: {input_folder}")
            sys.exit(1)
    
    print(f"\n[*] Found {len(dxf_files)} DXF file(s)")
    print(f"[*] Input:  {input_folder}")
    print(f"[*] Master Excel: {master_folder}")
    print(f"[*] Output: {output_folder}")
    
    total_devices = 0
    processed = 0
    
    for dxf_path in dxf_files:
        count = process_dxf(dxf_path, output_folder, system_type)
        if count > 0:
            total_devices += count
            processed += 1
    
    print("\n" + "=" * 60)
    print(f"  COMPLETE!")
    print(f"  Processed: {processed}/{len(dxf_files)} files")
    print(f"  Total devices: {total_devices}")
    print(f"  Output: {output_folder}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
