#!/usr/bin/env python3
"""
dwg_converter.py - Convert DWG files to DXF using ODA File Converter

ODA File Converter is a free tool from Open Design Alliance:
https://www.opendesign.com/guestfiles/oda_file_converter

This module provides automatic DWG→DXF conversion for CadOwl.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Tuple

# Common ODA File Converter installation paths
ODA_PATHS = [
    r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
    r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter 25.6.0\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter 24.12.0\ODAFileConverter.exe",
]


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
    output_folder: Optional[Path] = None,
    version: str = "ACAD2018"
) -> Tuple[int, int, List[str]]:
    """
    Convert all DWG files in input_folder to DXF format.
    
    Args:
        input_folder: Folder containing DWG files
        output_folder: Where to save DXF files (defaults to input_folder)
        version: AutoCAD version for DXF (ACAD2018, ACAD2013, etc.)
    
    Returns:
        Tuple of (converted_count, failed_count, error_messages)
    """
    if output_folder is None:
        output_folder = input_folder
    
    oda_exe = find_oda_converter()
    if not oda_exe:
        return (0, 0, ["ODA File Converter not found. Install from: https://www.opendesign.com/guestfiles/oda_file_converter"])
    
    # Find DWG files
    dwg_files = list(input_folder.glob("*.dwg")) + list(input_folder.glob("*.DWG"))
    if not dwg_files:
        return (0, 0, [])
    
    print(f"\n[DWG→DXF] Found {len(dwg_files)} DWG file(s)")
    print(f"[DWG→DXF] Using ODA: {oda_exe}")
    
    # ODA File Converter command line:
    # ODAFileConverter <input_folder> <output_folder> <output_version> <output_type> <recurse> <audit>
    # output_type: DXF (text), DXB (binary)
    
    # Create temp folder structure for ODA
    output_folder.mkdir(parents=True, exist_ok=True)
    
    converted = 0
    failed = 0
    errors = []
    
    try:
        # ODA converts all files in folder at once
        cmd = [
            str(oda_exe),
            str(input_folder),      # Input folder
            str(output_folder),     # Output folder  
            version,                # Output version (ACAD2018)
            "DXF",                  # Output type
            "0",                    # Recurse subfolders (0=no)
            "1"                     # Audit each file (1=yes)
        ]
        
        print(f"[DWG→DXF] Converting...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # Check which files were converted
        for dwg in dwg_files:
            dxf_path = output_folder / f"{dwg.stem}.dxf"
            if dxf_path.exists():
                print(f"  ✅ {dwg.name} → {dxf_path.name}")
                converted += 1
            else:
                print(f"  ❌ {dwg.name} - conversion failed")
                failed += 1
                errors.append(f"Failed to convert: {dwg.name}")
        
    except subprocess.TimeoutExpired:
        errors.append("ODA File Converter timed out")
        failed = len(dwg_files)
    except Exception as e:
        errors.append(f"Conversion error: {e}")
        failed = len(dwg_files)
    
    print(f"[DWG→DXF] Complete: {converted} converted, {failed} failed")
    return (converted, failed, errors)


def get_cad_files(input_folder: Path, auto_convert: bool = True) -> List[Path]:
    """
    Get all CAD files (DXF and DWG) from a folder.
    If auto_convert is True, converts DWG to DXF automatically.
    
    Returns list of DXF file paths to process.
    """
    input_folder = Path(input_folder)
    
    # Get existing DXF files
    dxf_files = list(input_folder.glob("*.dxf")) + list(input_folder.glob("*.DXF"))
    
    # Get DWG files
    dwg_files = list(input_folder.glob("*.dwg")) + list(input_folder.glob("*.DWG"))
    
    if dwg_files and auto_convert:
        oda_exe = find_oda_converter()
        if oda_exe:
            converted, failed, errors = convert_dwg_to_dxf(input_folder, input_folder)
            
            # Add newly converted DXF files
            for dwg in dwg_files:
                dxf_path = input_folder / f"{dwg.stem}.dxf"
                if dxf_path.exists() and dxf_path not in dxf_files:
                    dxf_files.append(dxf_path)
        else:
            print("\n" + "=" * 60)
            print("  ⚠️  DWG FILES FOUND BUT CANNOT AUTO-CONVERT")
            print("=" * 60)
            print(f"\nFound {len(dwg_files)} DWG file(s) but ODA File Converter not installed.")
            print("\nOptions:")
            print("  1. Install ODA File Converter (FREE):")
            print("     https://www.opendesign.com/guestfiles/oda_file_converter")
            print("\n  2. Convert manually in AutoCAD:")
            print("     Load DWG2DXF.lsp and run: DWG2DXFBATCH")
            print("\n  3. Save as DXF from AutoCAD: File → Save As → DXF")
            print("=" * 60 + "\n")
    
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
        print(f"✅ Installed: {status['path']}")
    else:
        print("❌ Not installed")
        print(f"   Download: {status['download_url']}")
