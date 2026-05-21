#!/usr/bin/env python3
"""Quick block/layer analysis for CCTV DXF."""
import sys
import ezdxf
from pathlib import Path
from collections import Counter

def main():
    dxf_path = Path(r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CADtoSiteOwl\Staging-CCTV\0041 Bartlesville, OK Device Location.dxf")
    
    print(f"Loading {dxf_path.name} ({dxf_path.stat().st_size // 1_000_000}MB)...", flush=True)
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    
    print("Analyzing blocks...", flush=True)
    
    layers = Counter()
    blocks = Counter()
    block_layers = {}  # block -> set of layers
    
    for entity in msp.query("INSERT"):
        layer = entity.dxf.layer
        block = entity.dxf.name
        layers[layer] += 1
        blocks[block] += 1
        if block not in block_layers:
            block_layers[block] = set()
        block_layers[block].add(layer)
    
    print(f"\nTotal INSERT entities: {sum(blocks.values())}", flush=True)
    print(f"Unique blocks: {len(blocks)}", flush=True)
    print(f"Unique layers: {len(layers)}", flush=True)
    
    # Find camera/security related blocks
    print("\n=== CAMERA/SECURITY BLOCKS ===", flush=True)
    keywords = ['ptz', 'dome', 'bullet', 'cam', '360', 'flexidome', 'autodome', 
                'dinion', 'bosch', 'axis', 'pelco', 'hikvision', 'video',
                'monitor', 'encoder', 'decoder', 'nvr', 'recorder']
    
    found = []
    for block, count in blocks.most_common():
        block_lower = block.lower()
        if any(kw in block_lower for kw in keywords):
            found.append((block, count, list(block_layers[block])))
    
    if found:
        for block, count, blayers in found:
            print(f"  {block} ({count}x) - Layers: {blayers}", flush=True)
    else:
        print("  None found by keyword search!", flush=True)
    
    # Top blocks by count (likely devices if high count)
    print("\n=== TOP 30 BLOCKS BY COUNT ===", flush=True)
    for block, count in blocks.most_common(30):
        print(f"  {count:4d}x  {block[:60]}", flush=True)
    
    # All layers
    print("\n=== ALL LAYERS ===", flush=True)
    for layer, count in layers.most_common():
        print(f"  {count:4d}x  {layer}", flush=True)
    
    print("\nDone!", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
