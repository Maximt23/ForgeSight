#!/usr/bin/env python3
"""
dwg_converter.py - Convert DWG files to DXF using ODA File Converter

ODA File Converter is a free tool from Open Design Alliance:
https://www.opendesign.com/guestfiles/oda_file_converter

Workflow: Input (DWG) -> Staging (DXF) -> Output (CSV)
"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Tuple

# Common ODA File Converter installation paths
ODA_PATHS = [
    r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
    r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter 25.6.0\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter 24.12.0\ODAFileConverter.exe",
]

# Folder structure: Input (DWG) -> Staging (DXF) -> Output (CSV)
ONEDRIVE_BASE = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CADtoSiteOwl")
FOLDERS = {
    "cctv": {
        "input": ONEDRIVE_BASE / "Input-CCTV",
        "staging": ONEDRIVE_BASE / "Staging-CCTV",
        "output": ONEDRIVE_BASE / "Output-CCTV",
    },
    "fa": {
        "input": ONEDRIVE_BASE / "Input-FAIntrusion",
        "staging": ONEDRIVE_BASE / "Staging-FAIntrusion",
        "output": ONEDRIVE_BASE / "Output-FAIntrusion",
    },
}


def find_oda_converter() -> Optional[Path]:
    """Find ODA File Converter executable"""
    # Check if in PATH
    oda_in_path = shutil.which("ODAFileConverter")
    if oda_in_path:
        return Path(oda_in_path)
    
    # Check common installation paths
    for path_str in ODA_PATHS:
        path = Path(path_str)
        if path.exists():
            return path
    
    # Search in Program Files
    for prog_dir in [Path(r"C:\Program Files\ODA"), Path(r"C:\Program Files (x86)\ODA")]:
        if prog_dir.exists():
            for subdir in prog_dir.iterdir():
                exe = subdir / "ODAFileConverter.exe"
                if exe.exists():
                    return exe
    
    return None


def convert_dwg_to_dxf(
    input_folder: Path,
    output_folder: Path,
    version: str = "ACAD2018"
) -> Tuple[int, int, List[str]]:
    """
    Convert all DWG files in input_folder to DXF format.
    
    Args:
        input_folder: Folder containing DWG files
        output_folder: Where to save DXF files (MUST be different from input!)
        version: AutoCAD version for DXF (ACAD2018, ACAD2013, etc.)
    
    Returns:
        Tuple of (converted_count, failed_count, error_messages)
    """
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    
    # ODA requires different input/output folders
    if input_folder.resolve() == output_folder.resolve():
        return (0, 0, ["Input and output folders must be different for ODA File Converter"])
    
    oda_exe = find_oda_converter()
    if not oda_exe:
        return (0, 0, ["ODA File Converter not found. Install from: https://www.opendesign.com/guestfiles/oda_file_converter"])
    
    # Find DWG files
    dwg_files = list(input_folder.glob("*.dwg")) + list(input_folder.glob("*.DWG"))
    if not dwg_files:
        return (0, 0, [])
    
    print(f"\n[DWG->DXF] Found {len(dwg_files)} DWG file(s)")
    print(f"[DWG->DXF] Input:  {input_folder}")
    print(f"[DWG->DXF] Output: {output_folder}")
    print(f"[DWG->DXF] Using ODA: {oda_exe}")
    
    # Create output folder
    output_folder.mkdir(parents=True, exist_ok=True)
    
    converted = 0
    failed = 0
    errors = []
    
    try:
        # ODA converts all files in folder at once
        cmd = [
            str(oda_exe),
            str(input_folder),      # Input folder (DWG)
            str(output_folder),     # Output folder (DXF)
            version,                # Output version (ACAD2018)
            "DXF",                  # Output type
            "0",                    # Recurse subfolders (0=no)
            "1"                     # Audit each file (1=yes)
        ]
        
        print(f"[DWG->DXF] Converting...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # Check which files were converted
        for dwg in dwg_files:
            dxf_path = output_folder / f"{dwg.stem}.dxf"
            if dxf_path.exists():
                print(f"  [OK] {dwg.name} -> {dxf_path.name}")
                converted += 1
            else:
                print(f"  [X] {dwg.name} - conversion failed")
                failed += 1
                errors.append(f"Failed to convert: {dwg.name}")
        
    except subprocess.TimeoutExpired:
        errors.append("ODA File Converter timed out")
        failed = len(dwg_files)
    except Exception as e:
        errors.append(f"Conversion error: {e}")
        failed = len(dwg_files)
    
    print(f"[DWG->DXF] Complete: {converted} converted, {failed} failed")
    return (converted, failed, errors)


def get_cad_files_for_system(system_type: str) -> Tuple[List[Path], Path]:
    """
    Get all DXF files for a system, auto-converting DWG if needed.
    
    Workflow: Input (DWG) -> Staging (DXF) -> Output (CSV)
    
    Args:
        system_type: 'cctv' or 'fa'
    
    Returns:
        Tuple of (list of DXF file paths, output folder path)
    """
    if system_type not in FOLDERS:
        raise ValueError(f"Unknown system type: {system_type}. Use 'cctv' or 'fa'")
    
    folders = FOLDERS[system_type]
    input_folder = folders["input"]
    staging_folder = folders["staging"]
    output_folder = folders["output"]
    
    # Ensure folders exist
    input_folder.mkdir(parents=True, exist_ok=True)
    staging_folder.mkdir(parents=True, exist_ok=True)
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Check for DWG files in input folder
    dwg_files = list(input_folder.glob("*.dwg")) + list(input_folder.glob("*.DWG"))
    
    if dwg_files:
        # Convert DWG from Input -> Staging
        oda_exe = find_oda_converter()
        if oda_exe:
            convert_dwg_to_dxf(input_folder, staging_folder)
        else:
            print("\n" + "=" * 60)
            print("  [!] DWG FILES FOUND BUT CANNOT AUTO-CONVERT")
            print("=" * 60)
            print(f"\nFound {len(dwg_files)} DWG file(s) but ODA File Converter not installed.")
            print("\nInstall ODA File Converter (FREE):")
            print("  https://www.opendesign.com/guestfiles/oda_file_converter")
            print("=" * 60 + "\n")
    
    # Get DXF files from staging folder
    dxf_files = list(staging_folder.glob("*.dxf")) + list(staging_folder.glob("*.DXF"))
    
    return (sorted(set(dxf_files)), output_folder)


def get_cad_files(input_folder: Path, auto_convert: bool = True, staging_folder: Path = None) -> List[Path]:
    """
    Get all CAD files (DXF) from staging folder after converting DWG from input.
    
    Args:
        input_folder: Folder containing DWG files
        auto_convert: Whether to auto-convert DWG to DXF
        staging_folder: Where to put converted DXF files (required if auto_convert=True)
    
    Returns:
        List of DXF file paths to process (from staging folder)
    """
    input_folder = Path(input_folder)
    
    # If no staging folder specified, try to determine from input folder name
    if staging_folder is None:
        # Check if this matches a known system folder
        for sys_type, folders in FOLDERS.items():
            if input_folder.resolve() == folders["input"].resolve():
                staging_folder = folders["staging"]
                break
        
        if staging_folder is None:
            # Fallback: create staging folder next to input
            staging_folder = input_folder.parent / f"{input_folder.name}-staging"
    
    staging_folder = Path(staging_folder)
    staging_folder.mkdir(parents=True, exist_ok=True)
    
    # Check for DWG files in input folder
    dwg_files = list(input_folder.glob("*.dwg")) + list(input_folder.glob("*.DWG"))
    
    if dwg_files and auto_convert:
        oda_exe = find_oda_converter()
        if oda_exe:
            convert_dwg_to_dxf(input_folder, staging_folder)
        else:
            print("\n" + "=" * 60)
            print("  [!] DWG FILES FOUND BUT CANNOT AUTO-CONVERT")
            print("=" * 60)
            print(f"\nFound {len(dwg_files)} DWG file(s) but ODA File Converter not installed.")
            print("\nInstall ODA File Converter (FREE):")
            print("  https://www.opendesign.com/guestfiles/oda_file_converter")
            print("=" * 60 + "\n")
    
    # Get DXF files from staging folder
    dxf_files = list(staging_folder.glob("*.dxf")) + list(staging_folder.glob("*.DXF"))
    
    return sorted(set(dxf_files))


def check_oda_status() -> dict:
    """Check ODA File Converter installation status"""
    oda_exe = find_oda_converter()
    return {
        "installed": oda_exe is not None,
        "path": str(oda_exe) if oda_exe else None,
        "download_url": "https://www.opendesign.com/guestfiles/oda_file_converter"
    }


if __name__ == "__main__":
    # Test/status check
    status = check_oda_status()
    print("\n=== ODA File Converter Status ===")
    if status["installed"]:
        print(f"[OK] Installed: {status['path']}")
    else:
        print("[X] Not installed")
        print(f"    Download: {status['download_url']}")
    
    print("\n=== Folder Configuration ===")
    for sys_type, folders in FOLDERS.items():
        print(f"\n{sys_type.upper()}:")
        print(f"  Input:   {folders['input']}")
        print(f"  Staging: {folders['staging']}")
        print(f"  Output:  {folders['output']}")
