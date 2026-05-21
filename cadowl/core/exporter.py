"""
SiteOwl CSV exporter for CadOwl.

Exports detected devices to SiteOwl-compatible CSV format.
"""

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from .detector import Device, SystemType, DeviceType


# SiteOwl CSV column headers (56 columns)
SITEOWL_HEADERS = [
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

# Column indices for quick access
COL_DEVICE_ID = 4
COL_NAME = 5
COL_SYSTEM_TYPE = 8
COL_DEVICE_TYPE = 9
COL_DESCRIPTION = 39
COL_COORDINATES = 53


@dataclass
class ExportOptions:
    """Options for CSV export."""
    
    include_unmatched: bool = True        # Include low-confidence devices
    include_description: bool = True      # Add CAD info to description
    device_id_prefix: str = "New"         # Prefix for device IDs
    store_number: Optional[str] = None    # Store number for metadata
    plan_name: Optional[str] = None       # Plan name
    add_timestamp: bool = False           # Add export timestamp


class SiteOwlExporter:
    """
    Export devices to SiteOwl CSV format.
    
    Example:
        exporter = SiteOwlExporter()
        exporter.export(devices, "output.csv", store_number="1234")
    """
    
    def __init__(self, headers: Optional[List[str]] = None):
        """
        Initialize exporter.
        
        Args:
            headers: Custom headers (or use SiteOwl defaults)
        """
        self.headers = headers or SITEOWL_HEADERS
    
    def device_to_row(
        self, 
        device: Device, 
        index: int,
        options: ExportOptions
    ) -> List[str]:
        """
        Convert device to CSV row.
        
        Args:
            device: Device to convert
            index: Device index (for ID generation)
            options: Export options
            
        Returns:
            List of column values
        """
        # Create empty row
        row = [""] * len(self.headers)
        
        # Device ID
        device_id = f"{options.device_id_prefix}{index:04d}"
        row[COL_DEVICE_ID] = device_id
        
        # Name
        row[COL_NAME] = device.name
        
        # System Type
        if device.system_type != SystemType.UNKNOWN:
            row[COL_SYSTEM_TYPE] = device.system_type.value
        
        # Device Type
        if device.device_type != DeviceType.UNKNOWN:
            row[COL_DEVICE_TYPE] = device.device_type.value
        
        # Coordinates
        row[COL_COORDINATES] = device.coordinates_str
        
        # Description with CAD metadata
        if options.include_description:
            desc_parts = []
            desc_parts.append(f"Block: {device.block_name}")
            desc_parts.append(f"Layer: {device.layer}")
            if device.detection_confidence < 1.0:
                desc_parts.append(f"Confidence: {device.detection_confidence:.0%}")
            row[COL_DESCRIPTION] = " | ".join(desc_parts)
        
        return row
    
    def export(
        self,
        devices: List[Device],
        output_path: Union[str, Path],
        options: Optional[ExportOptions] = None
    ) -> Path:
        """
        Export devices to SiteOwl CSV.
        
        Args:
            devices: List of devices to export
            output_path: Output file path
            options: Export options
            
        Returns:
            Path to created CSV file
        """
        options = options or ExportOptions()
        output_path = Path(output_path)
        
        # Filter devices if needed
        export_devices = devices
        if not options.include_unmatched:
            export_devices = [
                d for d in devices 
                if d.detection_confidence >= 0.5
            ]
        
        # Write CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(self.headers)
            
            for i, device in enumerate(export_devices, start=1):
                row = self.device_to_row(device, i, options)
                writer.writerow(row)
        
        return output_path
    
    def export_with_metadata(
        self,
        devices: List[Device],
        output_path: Union[str, Path],
        store_number: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Export devices and return metadata about the export.
        
        Args:
            devices: Devices to export
            output_path: Output path
            store_number: Store number
            metadata: Additional metadata
            
        Returns:
            Export metadata dict
        """
        options = ExportOptions(store_number=store_number)
        output = self.export(devices, output_path, options)
        
        # Count by system type
        system_counts = {}
        for device in devices:
            st = device.system_type.value
            system_counts[st] = system_counts.get(st, 0) + 1
        
        # Count by device type
        type_counts = {}
        for device in devices:
            dt = device.device_type.value
            type_counts[dt] = type_counts.get(dt, 0) + 1
        
        result = {
            "output_path": str(output),
            "timestamp": datetime.now().isoformat(),
            "total_devices": len(devices),
            "store_number": store_number,
            "system_type_counts": system_counts,
            "device_type_counts": type_counts,
        }
        
        if metadata:
            result.update(metadata)
        
        return result


class SiteOwlMerger:
    """
    Merge CadOwl devices with existing SiteOwl CSV.
    
    Strategies:
    - UPDATE_COORDINATES: Only update coordinates, preserve other data
    - APPEND_NEW: Add new devices, don't modify existing
    - REPLACE: Replace existing, add new
    """
    
    def __init__(self, headers: Optional[List[str]] = None):
        self.headers = headers or SITEOWL_HEADERS
    
    def load_csv(self, csv_path: Path) -> List[Dict[str, str]]:
        """Load existing SiteOwl CSV as list of dicts."""
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    
    def merge_coordinates(
        self,
        existing_csv: Path,
        devices: List[Device],
        output_path: Path,
        match_by: str = "name"  # "name" or "position"
    ) -> Dict:
        """
        Merge CAD coordinates into existing SiteOwl CSV.
        
        Args:
            existing_csv: Path to existing CSV
            devices: Devices with CAD coordinates
            output_path: Output path for merged CSV
            match_by: How to match devices ("name" or "position")
            
        Returns:
            Merge statistics
        """
        existing = self.load_csv(existing_csv)
        
        # Build lookup
        device_coords = {}
        for d in devices:
            key = d.name.upper().strip()
            device_coords[key] = d.coordinates_str
        
        # Merge
        matched = 0
        unmatched = 0
        
        for row in existing:
            name = row.get("Name", "").upper().strip()
            if name in device_coords:
                row["Coordinates"] = device_coords[name]
                matched += 1
            else:
                unmatched += 1
        
        # Write merged CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            writer.writeheader()
            writer.writerows(existing)
        
        return {
            "output_path": str(output_path),
            "total_existing": len(existing),
            "matched": matched,
            "unmatched": unmatched,
            "match_rate": matched / len(existing) if existing else 0
        }
