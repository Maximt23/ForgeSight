#!/usr/bin/env python3
"""
Pattern Analysis Script for CadOwl
CADOWL-001: Scan DXF files and identify unmatched block/layer patterns

Outputs: analysis/unmatched_patterns.json
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Add cadowl to path
sys.path.insert(0, str(Path(__file__).parent))

import ezdxf
from cadowl.core.detector import (
    DeviceDetector, 
    LAYER_PATTERNS, 
    BLOCK_PATTERNS, 
    EXCLUDE_PATTERNS
)


# Directories to scan
SCAN_DIRS = [
    Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CADtoSiteOwl\Staging-CCTV"),
    Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CADtoSiteOwl\Staging-FAIntrusion"),
    Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CADtoSiteOwl\CadOwl\Input"),
]

# Keywords that suggest a block MIGHT be a security device (for manual review)
SECURITY_KEYWORDS = [
    "cam", "camera", "cctv", "video", "dome", "ptz", "bullet", "nvr", "dvr",
    "smoke", "fire", "alarm", "strobe", "horn", "pull", "detect", "sensor",
    "motion", "pir", "door", "contact", "glass", "break", "panic", "duress",
    "reader", "card", "access", "keypad", "lock", "burg", "intrus", "security",
    "monitor", "surveillance", "ip", "analog", "bosch", "axis", "hikvision",
    "pelco", "samsung", "hanwha", "system sensor", "notifier", "simplex"
]


def compile_patterns():
    """Compile all existing patterns."""
    layer_compiled = [re.compile(p.pattern, re.IGNORECASE) for p in LAYER_PATTERNS]
    block_compiled = [re.compile(p.pattern, re.IGNORECASE) for p in BLOCK_PATTERNS]
    exclude_compiled = [re.compile(p, re.IGNORECASE) for p in EXCLUDE_PATTERNS]
    return layer_compiled, block_compiled, exclude_compiled


def matches_any(text, patterns):
    """Check if text matches any pattern."""
    return any(p.match(text) for p in patterns)


def looks_like_security_device(name):
    """Heuristic check if block/layer name looks security-related."""
    name_lower = name.lower()
    return any(kw in name_lower for kw in SECURITY_KEYWORDS)


def analyze_dxf(dxf_path, layer_patterns, block_patterns, exclude_patterns):
    """Analyze a single DXF file."""
    try:
        doc = ezdxf.readfile(str(dxf_path))
    except Exception as e:
        return {"error": str(e)}
    
    msp = doc.modelspace()
    
    # Collect all unique blocks and layers
    blocks = defaultdict(lambda: {"count": 0, "layers": set()})
    layers = set()
    
    for entity in msp.query("INSERT"):
        block_name = entity.dxf.name
        layer = entity.dxf.layer
        
        blocks[block_name]["count"] += 1
        blocks[block_name]["layers"].add(layer)
        layers.add(layer)
    
    # Classify blocks
    matched_blocks = []
    unmatched_blocks = []
    excluded_blocks = []
    potential_devices = []  # Unmatched but looks like a device
    
    for block_name, info in blocks.items():
        if matches_any(block_name, exclude_patterns):
            excluded_blocks.append(block_name)
        elif matches_any(block_name, block_patterns):
            matched_blocks.append(block_name)
        else:
            # Check if layer matches
            layer_matched = any(
                matches_any(layer, layer_patterns) 
                for layer in info["layers"]
            )
            if layer_matched:
                matched_blocks.append(block_name)
            else:
                unmatched_blocks.append(block_name)
                if looks_like_security_device(block_name):
                    potential_devices.append(block_name)
    
    # Classify layers
    matched_layers = [l for l in layers if matches_any(l, layer_patterns)]
    unmatched_layers = [l for l in layers if not matches_any(l, layer_patterns)]
    potential_device_layers = [l for l in unmatched_layers if looks_like_security_device(l)]
    
    return {
        "total_inserts": sum(b["count"] for b in blocks.values()),
        "unique_blocks": len(blocks),
        "unique_layers": len(layers),
        "matched_blocks": len(matched_blocks),
        "unmatched_blocks": len(unmatched_blocks),
        "excluded_blocks": len(excluded_blocks),
        "matched_layers": len(matched_layers),
        "unmatched_layers": len(unmatched_layers),
        "potential_device_blocks": potential_devices,
        "potential_device_layers": potential_device_layers,
        "unmatched_block_list": sorted(unmatched_blocks)[:50],  # Limit output
        "unmatched_layer_list": sorted(unmatched_layers)[:30],
    }


def main():
    print("=" * 60)
    print("CadOwl Pattern Analysis (CADOWL-001)")
    print("=" * 60)
    
    # Compile patterns
    layer_patterns, block_patterns, exclude_patterns = compile_patterns()
    print(f"\nLoaded patterns: {len(LAYER_PATTERNS)} layer, {len(BLOCK_PATTERNS)} block, {len(EXCLUDE_PATTERNS)} exclude")
    
    # Find all DXF files
    dxf_files = []
    for scan_dir in SCAN_DIRS:
        if scan_dir.exists():
            dxf_files.extend(scan_dir.glob("**/*.dxf"))
            print(f"Scanning: {scan_dir}")
        else:
            print(f"[SKIP] Directory not found: {scan_dir}")
    
    print(f"\nFound {len(dxf_files)} DXF files to analyze\n")
    
    # Analyze each file
    results = {}
    all_potential_blocks = set()
    all_potential_layers = set()
    total_matched = 0
    total_unmatched = 0
    
    for i, dxf_path in enumerate(dxf_files, 1):
        print(f"[{i}/{len(dxf_files)}] {dxf_path.name}...", end=" ")
        
        analysis = analyze_dxf(dxf_path, layer_patterns, block_patterns, exclude_patterns)
        
        if "error" in analysis:
            print(f"ERROR: {analysis['error']}")
            results[str(dxf_path)] = analysis
            continue
        
        print(f"OK ({analysis['matched_blocks']} matched, {analysis['unmatched_blocks']} unmatched)")
        
        results[str(dxf_path.name)] = analysis
        
        # Aggregate potential devices
        all_potential_blocks.update(analysis.get("potential_device_blocks", []))
        all_potential_layers.update(analysis.get("potential_device_layers", []))
        total_matched += analysis["matched_blocks"]
        total_unmatched += analysis["unmatched_blocks"]
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Files analyzed: {len(dxf_files)}")
    print(f"Total matched blocks: {total_matched}")
    print(f"Total unmatched blocks: {total_unmatched}")
    match_rate = total_matched / (total_matched + total_unmatched) * 100 if (total_matched + total_unmatched) > 0 else 0
    print(f"Match rate: {match_rate:.1f}%")
    
    print(f"\n--- Potential Device Blocks (need patterns) ---")
    for block in sorted(all_potential_blocks)[:30]:
        print(f"  - {block}")
    if len(all_potential_blocks) > 30:
        print(f"  ... and {len(all_potential_blocks) - 30} more")
    
    print(f"\n--- Potential Device Layers (need patterns) ---")
    for layer in sorted(all_potential_layers)[:20]:
        print(f"  - {layer}")
    if len(all_potential_layers) > 20:
        print(f"  ... and {len(all_potential_layers) - 20} more")
    
    # Save results
    output = {
        "summary": {
            "files_analyzed": len(dxf_files),
            "total_matched_blocks": total_matched,
            "total_unmatched_blocks": total_unmatched,
            "match_rate_percent": round(match_rate, 2),
            "potential_device_blocks": sorted(all_potential_blocks),
            "potential_device_layers": sorted(all_potential_layers),
        },
        "by_file": results
    }
    
    output_path = Path(__file__).parent / "analysis" / "unmatched_patterns.json"
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=list)
    
    print(f"\n[OK] Results saved to: {output_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
