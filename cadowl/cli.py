#!/usr/bin/env python3
"""
CadOwl CLI - Convert CAD files to SiteOwl coordinates.

Usage:
    python -m cadowl convert <dxf_file> [-o output.csv]
    python -m cadowl detect <dxf_file> [--report]
    python -m cadowl info <dxf_file>
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent to path if running directly
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from cadowl.core import (
    CoordinateMapper, ScaleMode, BoundingBox,
    DeviceDetector, Device,
    SiteOwlExporter, ExportOptions
)


def cmd_convert(args):
    """Convert DXF to SiteOwl CSV."""
    import ezdxf
    
    dxf_path = Path(args.file)
    if not dxf_path.exists():
        print(f"Error: File not found: {dxf_path}")
        return 1
    
    # Default output path
    output_path = Path(args.output) if args.output else dxf_path.with_suffix('.csv')
    
    print(f"Loading: {dxf_path.name}")
    doc = ezdxf.readfile(str(dxf_path))
    
    # Detect devices
    detector = DeviceDetector(min_confidence=args.min_confidence)
    devices = detector.extract_from_dxf(doc)
    print(f"Detected: {len(devices)} devices")
    
    if not devices:
        print("No devices found. Try lowering --min-confidence")
        return 1
    
    # Transform coordinates
    points = [(d.cad_x, d.cad_y) for d in devices]
    bbox = BoundingBox.from_points(points)
    
    mode = ScaleMode[args.scale_mode.upper()]
    mapper = CoordinateMapper(mode=mode)
    mapper.set_bounds(bbox)
    
    for device in devices:
        result = mapper.transform(device.cad_x, device.cad_y)
        device.art_x = result.art_x
        device.art_y = result.art_y
        device.site_x = result.site_x
        device.site_y = result.site_y
    
    # Export
    exporter = SiteOwlExporter()
    options = ExportOptions(
        include_unmatched=True,
        store_number=args.store
    )
    exporter.export(devices, output_path, options)
    
    print(f"Exported: {output_path}")
    print(f"Devices: {len(devices)}")
    
    return 0


def cmd_detect(args):
    """Detect devices in DXF without exporting."""
    import ezdxf
    
    dxf_path = Path(args.file)
    if not dxf_path.exists():
        print(f"Error: File not found: {dxf_path}")
        return 1
    
    print(f"Analyzing: {dxf_path.name}")
    doc = ezdxf.readfile(str(dxf_path))
    
    detector = DeviceDetector(min_confidence=args.min_confidence)
    
    if args.report:
        # Generate full report
        report = detector.generate_report(doc)
        
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"\n=== Detection Report ===")
            print(f"Total blocks: {report['total_blocks']}")
            print(f"Total inserts: {report['total_inserts']}")
            print(f"Detected: {report['detected_count']}")
            print(f"Unmatched: {report['unmatched_count']}")
            print(f"Layers: {len(report['layers'])}")
            
            print(f"\n--- Detected Devices ---")
            for d in report['detected'][:20]:
                print(f"  {d['block']:30} | {d['system']:20} | {d['confidence']:.0%}")
            
            if len(report['detected']) > 20:
                print(f"  ... and {len(report['detected']) - 20} more")
            
            print(f"\n--- Unmatched Blocks (sample) ---")
            for d in report['unmatched'][:10]:
                print(f"  {d['block']:30} | {d['layer']}")
    else:
        devices = detector.extract_from_dxf(doc)
        print(f"\nDetected {len(devices)} devices:\n")
        
        # Group by system type
        by_system = {}
        for d in devices:
            st = d.system_type.value
            by_system[st] = by_system.get(st, 0) + 1
        
        for system, count in sorted(by_system.items()):
            print(f"  {system}: {count}")
    
    return 0


def cmd_info(args):
    """Show DXF file info."""
    import ezdxf
    
    dxf_path = Path(args.file)
    if not dxf_path.exists():
        print(f"Error: File not found: {dxf_path}")
        return 1
    
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    
    # Count entities
    inserts = list(msp.query("INSERT"))
    
    print(f"\n=== DXF Info: {dxf_path.name} ===\n")
    print(f"DXF Version: {doc.dxfversion}")
    print(f"Encoding: {doc.encoding}")
    print(f"Total Inserts: {len(inserts)}")
    print(f"Unique Blocks: {len(set(e.dxf.name for e in inserts))}")
    print(f"Layers: {len(doc.layers)}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="CadOwl - CAD to SiteOwl coordinate converter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cadowl convert drawing.dxf
  cadowl convert drawing.dxf -o output.csv --store 1234
  cadowl detect drawing.dxf --report
  cadowl info drawing.dxf
"""
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Convert command
    p_convert = subparsers.add_parser('convert', help='Convert DXF to SiteOwl CSV')
    p_convert.add_argument('file', help='DXF file to convert')
    p_convert.add_argument('-o', '--output', help='Output CSV file')
    p_convert.add_argument('--store', help='Store number')
    p_convert.add_argument('--min-confidence', type=float, default=0.5,
                          help='Minimum detection confidence (0-1)')
    p_convert.add_argument('--scale-mode', default='fit_contain',
                          choices=['fit_width', 'fit_height', 'fit_contain', 'fit_cover', 'stretch'],
                          help='Coordinate scaling mode')
    
    # Detect command
    p_detect = subparsers.add_parser('detect', help='Detect devices in DXF')
    p_detect.add_argument('file', help='DXF file to analyze')
    p_detect.add_argument('--report', action='store_true', help='Generate detailed report')
    p_detect.add_argument('--json', action='store_true', help='Output as JSON')
    p_detect.add_argument('--min-confidence', type=float, default=0.3,
                          help='Minimum detection confidence (0-1)')
    
    # Info command
    p_info = subparsers.add_parser('info', help='Show DXF file info')
    p_info.add_argument('file', help='DXF file')
    
    args = parser.parse_args()
    
    if args.command == 'convert':
        return cmd_convert(args)
    elif args.command == 'detect':
        return cmd_detect(args)
    elif args.command == 'info':
        return cmd_info(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
