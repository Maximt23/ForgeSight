"""
ForgeSight CAD - CAD/DXF/PDF Design Engine

Extract devices and coordinates from CAD drawings.

Usage:
    from forgesight.cad import DXFParser, DeviceDetector, SiteOwlExporter
    
    parser = DXFParser("drawing.dxf")
    entities = parser.extract_blocks()
    
    detector = DeviceDetector()
    devices = detector.detect(entities)
    
    exporter = SiteOwlExporter(store_number="1234")
    exporter.export(devices, "output.csv")
"""

# Re-export from legacy cadowl for backwards compatibility
from cadowl.core.detector import (
    DeviceDetector,
    Device,
    SystemType,
    DeviceType,
    DevicePattern,
    LAYER_PATTERNS,
    BLOCK_PATTERNS,
    EXCLUDE_PATTERNS,
)
from cadowl.core.mapper import (
    CoordinateMapper,
    ScaleMode,
)
from cadowl.core.exporter import (
    SiteOwlExporter,
    ExportFormat,
)

# New name for parser
try:
    import ezdxf
    
    class DXFParser:
        """Parse DXF files and extract block insertions."""
        
        def __init__(self, filepath: str):
            self.filepath = filepath
            self.doc = None
            
        def load(self):
            """Load the DXF file."""
            self.doc = ezdxf.readfile(self.filepath)
            return self
            
        def extract_blocks(self):
            """Extract all block insertions from modelspace."""
            if self.doc is None:
                self.load()
            
            msp = self.doc.modelspace()
            return list(msp.query("INSERT"))
        
        def get_bounds(self):
            """Get bounding box of all entities."""
            if self.doc is None:
                self.load()
            
            msp = self.doc.modelspace()
            
            min_x = min_y = float('inf')
            max_x = max_y = float('-inf')
            
            for entity in msp.query("INSERT"):
                x, y, _ = entity.dxf.insert
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
            
            return {
                "min_x": min_x if min_x != float('inf') else 0,
                "min_y": min_y if min_y != float('inf') else 0,
                "max_x": max_x if max_x != float('-inf') else 1000,
                "max_y": max_y if max_y != float('-inf') else 1000,
            }
            
except ImportError:
    DXFParser = None


__all__ = [
    "DXFParser",
    "DeviceDetector",
    "Device",
    "SystemType",
    "DeviceType",
    "DevicePattern",
    "CoordinateMapper",
    "ScaleMode",
    "SiteOwlExporter",
    "ExportFormat",
    "LAYER_PATTERNS",
    "BLOCK_PATTERNS",
    "EXCLUDE_PATTERNS",
]
