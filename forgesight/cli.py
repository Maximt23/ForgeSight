"""
ForgeSight CLI - Command Line Interface

Usage:
    forgesight cad convert drawing.dxf -o output.csv
    forgesight cad detect drawing.dxf --report
    forgesight grid transform --bounds "0,0,1000,500"
    forgesight serve --port 9010
    forgesight version
"""

import argparse
import sys
from pathlib import Path


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="forgesight",
        description="🔮 ForgeSight AI - Enterprise Security Design Intelligence"
    )
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # === CAD Commands ===
    cad_parser = subparsers.add_parser("cad", help="CAD/DXF operations")
    cad_sub = cad_parser.add_subparsers(dest="cad_command")
    
    # cad convert
    convert_parser = cad_sub.add_parser("convert", help="Convert CAD to SiteOwl CSV")
    convert_parser.add_argument("input", help="Input DXF/DWG file")
    convert_parser.add_argument("-o", "--output", help="Output CSV file")
    convert_parser.add_argument("--store", help="Store number")
    convert_parser.add_argument("--format", default="siteowl", help="Output format")
    
    # cad detect
    detect_parser = cad_sub.add_parser("detect", help="Detect devices in CAD")
    detect_parser.add_argument("input", help="Input DXF file")
    detect_parser.add_argument("--report", action="store_true", help="Show detailed report")
    
    # cad batch
    batch_parser = cad_sub.add_parser("batch", help="Batch process directory")
    batch_parser.add_argument("input_dir", help="Input directory")
    batch_parser.add_argument("-o", "--output_dir", help="Output directory")
    
    # === Grid Commands ===
    grid_parser = subparsers.add_parser("grid", help="Coordinate/GIS operations")
    grid_sub = grid_parser.add_subparsers(dest="grid_command")
    
    # grid transform
    transform_parser = grid_sub.add_parser("transform", help="Transform coordinates")
    transform_parser.add_argument("--bounds", help="Source bounds (min_x,min_y,max_x,max_y)")
    transform_parser.add_argument("--point", help="Point to transform (x,y)")
    transform_parser.add_argument("--mode", default="FIT_CONTAIN", help="Scale mode")
    
    # grid match
    match_parser = grid_sub.add_parser("match", help="Match devices from sources")
    match_parser.add_argument("--source", help="Source devices JSON")
    match_parser.add_argument("--target", help="Target devices JSON")
    match_parser.add_argument("--tolerance", type=float, default=0.05)
    
    # === Server Commands ===
    serve_parser = subparsers.add_parser("serve", help="Start API server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host")
    serve_parser.add_argument("--port", type=int, default=9010, help="Port")
    serve_parser.add_argument("--reload", action="store_true", help="Auto-reload")
    
    # === Vision Commands ===
    vision_parser = subparsers.add_parser("vision", help="Coverage analysis")
    vision_sub = vision_parser.add_subparsers(dest="vision_command")
    
    # vision analyze
    analyze_parser = vision_sub.add_parser("analyze", help="Analyze coverage")
    analyze_parser.add_argument("--floor-plan", help="Floor plan JSON")
    analyze_parser.add_argument("--cameras", help="Cameras JSON")
    analyze_parser.add_argument("-o", "--output", help="Output heatmap")
    
    # Parse args
    args = parser.parse_args()
    
    if args.version:
        from forgesight import __version__
        print(f"🔮 ForgeSight AI v{__version__}")
        return 0
    
    if args.command == "cad":
        return handle_cad(args)
    elif args.command == "grid":
        return handle_grid(args)
    elif args.command == "serve":
        return handle_serve(args)
    elif args.command == "vision":
        return handle_vision(args)
    else:
        parser.print_help()
        return 1


def handle_cad(args):
    """Handle CAD commands."""
    if args.cad_command == "convert":
        from cadowl.cli import convert_command
        # Use legacy cadowl for now
        return convert_command(args.input, args.output, args.store)
    
    elif args.cad_command == "detect":
        from cadowl.cli import detect_command
        return detect_command(args.input, args.report)
    
    elif args.cad_command == "batch":
        print("Batch processing not yet implemented")
        return 1
    
    return 1


def handle_grid(args):
    """Handle Grid commands."""
    if args.grid_command == "transform":
        from forgesight.grid import CoordinateTransformer, Bounds, ScaleMode
        
        if args.bounds:
            parts = [float(x) for x in args.bounds.split(",")]
            bounds = Bounds(min_x=parts[0], min_y=parts[1], max_x=parts[2], max_y=parts[3])
        else:
            bounds = Bounds(min_x=0, min_y=0, max_x=1000, max_y=1000)
        
        mode = ScaleMode[args.mode.upper()]
        transformer = CoordinateTransformer(mode=mode)
        transformer.set_bounds(bounds)
        
        if args.point:
            x, y = [float(p) for p in args.point.split(",")]
            result = transformer.transform(x, y)
            print(f"Input: ({x}, {y})")
            print(f"SiteOwl: ({result.site_x}, {result.site_y})")
            print(f"Artboard: ({result.art_x}, {result.art_y})")
        else:
            print(f"Bounds: {bounds}")
            print(f"Mode: {mode}")
            print(f"Matrix: {transformer.get_transform_matrix()}")
        
        return 0
    
    elif args.grid_command == "match":
        import json
        from forgesight.grid import match_devices
        
        with open(args.source) as f:
            source = json.load(f)
        with open(args.target) as f:
            target = json.load(f)
        
        result = match_devices(source, target, tolerance=args.tolerance)
        
        print(f"Matched: {len(result.matched)}")
        print(f"Unmatched source: {len(result.unmatched_source)}")
        print(f"Unmatched target: {len(result.unmatched_target)}")
        print(f"Match rate: {result.match_rate:.0%}")
        
        return 0
    
    return 1


def handle_serve(args):
    """Handle serve command."""
    import uvicorn
    
    print(f"🔮 Starting ForgeSight Core API on {args.host}:{args.port}")
    
    uvicorn.run(
        "apps.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )
    
    return 0


def handle_vision(args):
    """Handle Vision commands."""
    if args.vision_command == "analyze":
        import json
        from forgesight.vision import Camera, CoverageAnalyzer
        
        floor_plan = {}
        if args.floor_plan:
            with open(args.floor_plan) as f:
                floor_plan = json.load(f)
        
        cameras = []
        if args.cameras:
            with open(args.cameras) as f:
                cameras_data = json.load(f)
                for c in cameras_data:
                    cameras.append(Camera(**c))
        
        analyzer = CoverageAnalyzer(floor_plan)
        analyzer.add_cameras(cameras)
        
        stats = analyzer.get_statistics()
        print(f"Coverage: {stats.coverage_percent:.1f}%")
        print(f"Blind spots: {stats.blind_spot_count}")
        print(f"Overlap: {stats.overlap_percent:.1f}%")
        
        if args.output:
            heatmap = analyzer.generate_heatmap()
            with open(args.output, "w") as f:
                json.dump(heatmap, f)
            print(f"Heatmap saved to {args.output}")
        
        return 0
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
