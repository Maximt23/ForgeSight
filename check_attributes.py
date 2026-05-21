#!/usr/bin/env python3
"""Check attributes in DXF blocks."""
import ezdxf
from pathlib import Path

dxf = Path(r'C:\Users\vn59j7j\OneDrive - Walmart Inc\Master Excel Pathing\CADtoSiteOwl\Staging-CCTV\0041 Bartlesville, OK Device Location.dxf')
doc = ezdxf.readfile(str(dxf))
msp = doc.modelspace()

output = []
output.append("Blocks with attributes:")

found = 0
for entity in msp.query('INSERT'):
    if hasattr(entity, 'attribs'):
        attribs_list = list(entity.attribs)
        if attribs_list:
            attribs = {a.dxf.tag: a.dxf.text for a in attribs_list}
            if attribs and found < 30:
                output.append(f"  Block: {entity.dxf.name[:50]}")
                for tag, val in list(attribs.items())[:5]:
                    output.append(f"    {tag}: {val}")
                output.append("")
                found += 1

output.append(f"Total blocks with attributes: {found}")

# Write to file
with open("analysis/attributes_check.txt", "w") as f:
    f.write("\n".join(output))

print(f"Output written to analysis/attributes_check.txt")
