"""
🔮 ForgeSight AI

Enterprise Security Design Intelligence Platform

Products:
    - ForgeSight CAD: CAD/DXF/PDF design engine
    - ForgeSight Field: Mobile/VR site survey app
    - ForgeSight Vision: Camera/FOV coverage engine
    - ForgeSight Grid: GIS/coordinates/zoning engine
    - ForgeSight Core: API/data platform
    - ForgeSight AutoDesign: ML design recommendation engine

Usage:
    from forgesight.cad import DXFParser, DeviceDetector
    from forgesight.grid import CoordinateTransformer
    from forgesight.core import get_current_user

CLI:
    forgesight cad convert drawing.dxf -o output.csv
    forgesight grid transform --bounds "0,0,1000,500"
    forgesight serve --port 9010
"""

__version__ = "0.1.0"
__author__ = "Walmart Security Design Team"
__product__ = "ForgeSight AI"

# Convenience imports
from forgesight.cad import (
    DXFParser,
    DeviceDetector,
    SiteOwlExporter,
)
from forgesight.grid import (
    CoordinateTransformer,
    DeviceMatcher,
    Bounds,
    ScaleMode,
)

__all__ = [
    "DXFParser",
    "DeviceDetector", 
    "SiteOwlExporter",
    "CoordinateTransformer",
    "DeviceMatcher",
    "Bounds",
    "ScaleMode",
    "__version__",
]
