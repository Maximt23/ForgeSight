# Shared Coordinate Transformation Library

Cross-platform coordinate transformation system for CadOwl + VIVE XR integration.

## Purpose

This library provides a unified coordinate mapping system that works identically in:
- **Python** (CadOwl backend)
- **C#/Unity** (VIVE XR frontend)

## Directory Structure

```
shared/
├── transform/           # Core transformation algorithms
│   ├── transform_core.py    # Python implementation
│   ├── TransformCore.cs     # C# implementation (Unity-compatible)
│   └── README.md            # API documentation
├── schema/              # JSON Schema definitions
│   ├── device.schema.json   # Device data format
│   ├── floor.schema.json    # Floor plan format
│   └── transform.schema.json # Transformation parameters
└── tests/               # Cross-platform test harness
    ├── test_vectors.json    # Known-good coordinate pairs
    ├── test_transform.py    # Python unit tests
    └── TestTransform.cs     # C# unit tests
```

## Coordinate Systems

### Source Systems
| System | Units | Origin | Orientation |
|--------|-------|--------|-------------|
| CAD (DXF/DWG) | Drawing units | Bottom-left | Y-up |
| VIVE XR | Meters | Room center | Y-up, Z-forward |
| SiteOwl | Normalized 0-1 | Top-left | Y-down |

### Transformation Pipeline
```
CAD Coords ────┐
               ├──► Normalized World ──► SiteOwl Coords
VIVE Coords ───┘
```

## Usage

### Python
```python
from shared.transform.transform_core import CoordinateTransformer

transformer = CoordinateTransformer(
    floor_bounds={"min_x": 0, "min_y": 0, "max_x": 100, "max_y": 80},
    source_system="cad"
)
siteowl_coords = transformer.to_siteowl(cad_x=45.5, cad_y=32.1)
```

### C# (Unity)
```csharp
using CadOwl.Shared.Transform;

var transformer = new CoordinateTransformer(
    floorBounds: new FloorBounds(0, 0, 100, 80),
    sourceSystem: SourceSystem.VIVE
);
var siteOwlCoords = transformer.ToSiteOwl(vivePosition);
```

## Key Principles

1. **Identical Math**: Python and C# implementations must produce bit-identical results
2. **Test Vectors**: All implementations validated against `tests/test_vectors.json`
3. **Schema-First**: All data formats defined in JSON Schema before implementation
4. **Tolerance**: 0.001 normalized units (0.1% of floor dimension)

## Contributing

1. Check task board in `../relayops/tasks/`
2. Claim a VIVE-xxx task before starting work
3. Run cross-platform tests before committing
4. Update test vectors when adding new cases
