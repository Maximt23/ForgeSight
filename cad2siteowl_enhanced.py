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
from typing import Optional

import ezdxf

from enhanced_boundary import convert_to_siteowl, find_boundary
from enhanced_matching import match_cad_to_excel
from enhanced_models import CadDevice, ExcelDevice

# Local module for DWG->DXF conversion
try:
    from dwg_converter import get_cad_files, FOLDERS
    HAS_DWG_CONVERTER = True
except ImportError:
    HAS_DWG_CONVERTER = False
    FOLDERS = {}

    def get_cad_files(folder, auto_convert=True, staging_folder=None):
        return list(Path(folder).glob("*.dxf"))

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR = Path(__file__).parent.resolve()
DXF_FOLDER = SCRIPT_DIR / "Input"
OUTPUT_FOLDER = SCRIPT_DIR / "Output"

# Master Excel folders for reference data
MASTER_EXCEL_FA = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\FA&Intrusion STORES DATA - Survey")
MASTER_EXCEL_CCTV = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CCTV STORES DATA - Survey")

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


# =============================================================================
# DXF PROCESSING
# =============================================================================

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
    
    # Extract CAD devices first - boundary scoring uses device coverage
    cad_devices = extract_devices(doc)
    print(f"  Found {len(cad_devices)} devices in CAD")
    
    if not cad_devices:
        print("  WARNING: No devices found in CAD!")
        return 0

    # Find best-fit boundary after device extraction
    bbox = find_boundary(doc, cad_devices)
    if not bbox:
        print("  ERROR: Could not determine boundary!")
        return 0
    
    # Load master Excel for this store (using correct system type)
    excel_devices = load_master_excel(store_num, system_type)
    
    # Match devices
    matched_count = 0
    unmatched_count = 0
    out_of_range = 0
    site_x_values: list[float] = []
    site_y_values: list[float] = []
    
    output_folder.mkdir(parents=True, exist_ok=True)
    csv_path = output_folder / f"{store_num}_SiteOwl_Enhanced.csv"
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        
        for cad_dev in cad_devices:
            coords = convert_to_siteowl(cad_dev.x, cad_dev.y, bbox)
            site_x, site_y = coords
            site_x_values.append(site_x)
            site_y_values.append(site_y)

            if site_x < 0 or site_x > 100 or site_y < 0 or site_y > 100:
                out_of_range += 1
            
            # Try to find matching Excel device
            excel_match = match_cad_to_excel(cad_dev, excel_devices)
            
            if excel_match:
                matched_count += 1
            else:
                unmatched_count += 1
            
            row = make_row(cad_dev, excel_match, coords, store_num)
            writer.writerow(row)
    
    print(f"  [MATCHED] {matched_count} | [UNMATCHED] {unmatched_count}")
    print(
        f"  Coordinates: X[{min(site_x_values):.2f}, {max(site_x_values):.2f}] "
        f"Y[{min(site_y_values):.2f}, {max(site_y_values):.2f}] | "
        f"Out-of-range: {out_of_range}/{len(cad_devices)}"
    )
    print(f"  SUCCESS: Exported {csv_path.name}")
    
    return len(cad_devices)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Convert DXF to SiteOwl CSV with Excel cross-reference")
    parser.add_argument("file", nargs="?", help="Single DXF file to process")
    parser.add_argument("--input", "-i", type=Path, help="Input folder for DWG files")
    parser.add_argument("--staging", type=Path, help="Staging folder for DXF files")
    parser.add_argument("--output", "-o", type=Path, help="Output folder for CSV results")
    parser.add_argument("--system", "-s", choices=["fa", "cctv"], default="fa",
                        help="System type: 'fa' for Fire Alarm/Intrusion, 'cctv' for CCTV")
    args = parser.parse_args()
    
    system_type = args.system
    
    # Use system-specific folders if available, otherwise use args
    if HAS_DWG_CONVERTER and system_type in FOLDERS:
        folders = FOLDERS[system_type]
        input_folder = args.input if args.input else folders["input"]
        staging_folder = args.staging if args.staging else folders["staging"]
        output_folder = args.output if args.output else folders["output"]
    else:
        input_folder = args.input if args.input else DXF_FOLDER
        staging_folder = args.staging if args.staging else (input_folder.parent / f"{input_folder.name}-staging")
        output_folder = args.output if args.output else OUTPUT_FOLDER
    
    # Select correct master Excel folder
    master_folder = MASTER_EXCEL_CCTV if system_type == "cctv" else MASTER_EXCEL_FA
    
    print("\n" + "=" * 60)
    print(f"  CadOwl Enhanced - DWG/DXF to SiteOwl ({system_type.upper()})")
    print("=" * 60)
    print(f"\n  Workflow: Input (DWG) -> Staging (DXF) -> Output (CSV)")
    
    if args.file:
        dxf_files = [Path(args.file)]
    else:
        if not input_folder.exists():
            print(f"\nERROR: Input folder not found: {input_folder}")
            sys.exit(1)
        
        # Get DXF files from staging (auto-convert DWG from input if ODA is installed)
        dxf_files = get_cad_files(input_folder, auto_convert=True, staging_folder=staging_folder)
        
        if not dxf_files:
            print(f"\nERROR: No DXF files in staging folder: {staging_folder}")
            print(f"       Put DWG files in: {input_folder}")
            sys.exit(1)
    
    print(f"\n[*] Found {len(dxf_files)} DXF file(s) to process")
    print(f"[*] Input:   {input_folder}")
    print(f"[*] Staging: {staging_folder}")
    print(f"[*] Output:  {output_folder}")
    print(f"[*] Master Excel: {master_folder}")
    
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
