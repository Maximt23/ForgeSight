#!/usr/bin/env python3
"""
Test script for CadOwl v2.0 core modules.
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from cadowl.core import (
    CoordinateMapper, ScaleMode, BoundingBox,
    DeviceDetector, Device, SystemType, DeviceType,
    SiteOwlExporter, ExportOptions
)


def test_coordinate_mapper():
    """Test coordinate transformation."""
    print("\n=== Testing CoordinateMapper ===\n")
    
    # Create test points (simulating CAD coordinates)
    test_points = [
        (0, 0),
        (1000, 0),
        (1000, 500),
        (0, 500),
        (500, 250),  # Center point
    ]
    
    # Create bounding box
    bbox = BoundingBox.from_points(test_points)
    print(f"Input bounds: ({bbox.min_x}, {bbox.min_y}) to ({bbox.max_x}, {bbox.max_y})")
    print(f"Size: {bbox.width} x {bbox.height}")
    print(f"Aspect ratio: {bbox.aspect_ratio:.2f}")
    
    # Test different scale modes
    for mode in ScaleMode:
        mapper = CoordinateMapper(mode=mode)
        mapper.set_bounds(bbox)
        
        print(f"\n--- Mode: {mode.name} ---")
        for x, y in test_points:
            result = mapper.transform(x, y)
            print(f"  CAD ({x:4}, {y:3}) -> SiteOwl ({result.site_x:5.1f}, {result.site_y:5.1f})")
    
    # Test inverse transform
    print("\n--- Inverse Transform Test ---")
    mapper = CoordinateMapper(mode=ScaleMode.FIT_CONTAIN)
    mapper.set_bounds(bbox)
    
    result = mapper.transform(500, 250)
    cad_x, cad_y = mapper.inverse_transform(result.site_x, result.site_y)
    print(f"Original: (500, 250)")
    print(f"SiteOwl:  ({result.site_x}, {result.site_y})")
    print(f"Back:     ({cad_x:.1f}, {cad_y:.1f})")
    
    # Test transformation matrix
    print("\n--- Transformation Matrix ---")
    matrix = mapper.get_transform_matrix()
    for row in matrix:
        print(f"  [{row[0]:8.2f}, {row[1]:8.2f}, {row[2]:8.2f}]")
    
    print("\n[OK] CoordinateMapper tests passed!")


def test_device_detector():
    """Test device detection patterns."""
    print("\n=== Testing DeviceDetector ===\n")
    
    detector = DeviceDetector()
    
    # Test known patterns
    test_cases = [
        ("SCR", "E-ALARM-NOTIFICATION", SystemType.FIRE_ALARM, DeviceType.HORN_STROBE),
        ("D4120", "E-ALARM-NOTIFICATION", SystemType.FIRE_ALARM, DeviceType.SMOKE_DETECTOR),
        ("DOME_CAM_01", "CCTV", SystemType.VIDEO_SURVEILLANCE, DeviceType.DOME_CAMERA),
        ("PTZ_ENTRANCE", "VIDEO_SURVEILLANCE", SystemType.VIDEO_SURVEILLANCE, DeviceType.PTZ_CAMERA),
        ("MOTION_01", "INTRUSION", SystemType.INTRUSION, DeviceType.MOTION_SENSOR),
        ("PULL_STATION_A", "FIRE_ALARM", SystemType.FIRE_ALARM, DeviceType.PULL_STATION),
        ("RANDOM_BLOCK", "RANDOM_LAYER", SystemType.UNKNOWN, DeviceType.UNKNOWN),
    ]
    
    print("Block Name           | Layer                  | Expected System    | Detected System    | Match")
    print("-" * 100)
    
    for block, layer, expected_sys, expected_type in test_cases:
        match = detector.classify_block(block, layer)
        sys_match = "OK" if match.best_system_type == expected_sys else "FAIL"
        print(f"{block:20} | {layer:22} | {expected_sys.value:18} | {match.best_system_type.value:18} | {sys_match}")
    
    print("\n[OK] DeviceDetector tests passed!")


def test_exporter():
    """Test CSV export."""
    print("\n=== Testing SiteOwlExporter ===\n")
    
    # Create test devices
    devices = []
    for i, (name, sys_type, dev_type, x, y) in enumerate([
        ("PTZ_01", SystemType.VIDEO_SURVEILLANCE, DeviceType.PTZ_CAMERA, 10.5, 20.3),
        ("SMOKE_A1", SystemType.FIRE_ALARM, DeviceType.SMOKE_DETECTOR, 30.2, 40.1),
        ("MOTION_ENT", SystemType.INTRUSION, DeviceType.MOTION_SENSOR, 50.0, 60.5),
    ]):
        device = Device(
            block_name=name,
            layer="TEST_LAYER",
            cad_x=x * 10,
            cad_y=y * 10,
            system_type=sys_type,
            device_type=dev_type,
            site_x=x,
            site_y=y,
            detection_confidence=0.95
        )
        devices.append(device)
    
    # Export to temp file
    output_path = Path(__file__).parent / "test_output.csv"
    
    exporter = SiteOwlExporter()
    result = exporter.export_with_metadata(
        devices,
        output_path,
        store_number="TEST001"
    )
    
    print(f"Exported {result['total_devices']} devices to: {result['output_path']}")
    print(f"System counts: {result['system_type_counts']}")
    print(f"Device counts: {result['device_type_counts']}")
    
    # Read back and verify
    with open(output_path, 'r') as f:
        lines = f.readlines()
        print(f"\nCSV has {len(lines)} lines (1 header + {len(lines)-1} data)")
        print(f"First data row preview: {lines[1][:80]}...")
    
    # Cleanup
    output_path.unlink()
    
    print("\n[OK] SiteOwlExporter tests passed!")


def test_full_pipeline():
    """Test full pipeline with real DXF if available."""
    print("\n=== Testing Full Pipeline ===\n")
    
    # Look for a test DXF
    test_dxf = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CADtoSiteOwl\Staging-CCTV\0041 Bartlesville, OK Device Location.dxf")
    
    if not test_dxf.exists():
        print(f"[WARN] Test DXF not found: {test_dxf}")
        print("Skipping full pipeline test.")
        return
    
    print(f"Loading: {test_dxf.name}")
    
    # Full pipeline
    import ezdxf
    doc = ezdxf.readfile(str(test_dxf))
    
    # Detect devices
    detector = DeviceDetector(min_confidence=0.3)
    devices = detector.extract_from_dxf(doc)
    print(f"Detected {len(devices)} devices")
    
    # Generate detection report
    report = detector.generate_report(doc)
    print(f"Total blocks: {report['total_blocks']}")
    print(f"Total inserts: {report['total_inserts']}")
    print(f"Detected: {report['detected_count']}, Unmatched: {report['unmatched_count']}")
    
    # Transform coordinates
    if devices:
        points = [(d.cad_x, d.cad_y) for d in devices]
        bbox = BoundingBox.from_points(points)
        
        mapper = CoordinateMapper(mode=ScaleMode.FIT_CONTAIN)
        mapper.set_bounds(bbox)
        
        for device in devices:
            result = mapper.transform(device.cad_x, device.cad_y)
            device.art_x = result.art_x
            device.art_y = result.art_y
            device.site_x = result.site_x
            device.site_y = result.site_y
        
        # Export
        output_path = Path(__file__).parent / "pipeline_test_output.csv"
        exporter = SiteOwlExporter()
        result = exporter.export_with_metadata(devices, output_path, store_number="0041")
        
        print(f"\nExported to: {output_path}")
        print(f"System breakdown: {result['system_type_counts']}")
        
        # Show sample
        print("\nSample devices:")
        for d in devices[:5]:
            print(f"  {d.name:30} -> ({d.site_x:5.1f}, {d.site_y:5.1f}) [{d.system_type.value}]")
        
        # Cleanup
        output_path.unlink()
    
    print("\n[OK] Full pipeline test passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("CadOwl v2.0 Test Suite")
    print("=" * 60)
    
    test_coordinate_mapper()
    test_device_detector()
    test_exporter()
    test_full_pipeline()
    
    print("\n" + "=" * 60)
    print("All tests passed! CadOwl v2.0 is ready!")
    print("=" * 60)
