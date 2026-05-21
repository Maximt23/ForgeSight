# Coordinate Transformation Core

## API Specification

Both Python and C# implementations MUST implement this identical API.

### Class: CoordinateTransformer

#### Constructor
```
CoordinateTransformer(
    floor_bounds: FloorBounds,
    source_system: SourceSystem,
    reference_points?: ReferencePoint[]  # Optional calibration points
)
```

#### Methods

##### to_siteowl(x, y, z?) -> SiteOwlCoord
Convert source coordinates to SiteOwl normalized coordinates.
- Input: Source system coordinates
- Output: Normalized (0-1) coordinates with Y-down orientation

##### from_siteowl(normalized_x, normalized_y) -> SourceCoord
Convert SiteOwl coordinates back to source system.
- Input: Normalized (0-1) SiteOwl coordinates
- Output: Source system coordinates

##### calibrate(reference_points: ReferencePoint[]) -> void
Apply manual calibration using known reference points.
- Input: Array of known CAD/VR ↔ SiteOwl coordinate pairs
- Effect: Adjusts transformation matrix for better accuracy

##### get_transform_matrix() -> Matrix3x3
Returns the current transformation matrix.

### Data Types

#### FloorBounds
```json
{
  "min_x": number,
  "min_y": number,
  "max_x": number,
  "max_y": number,
  "rotation_deg": number  // Optional, default 0
}
```

#### SourceSystem (enum)
- `CAD` - DXF/DWG coordinate system
- `VIVE` - VIVE XR tracking coordinates
- `MANUAL` - User-input coordinates

#### SiteOwlCoord
```json
{
  "x": number,  // 0.0 to 1.0, left to right
  "y": number,  // 0.0 to 1.0, top to bottom
  "z": number   // Optional elevation
}
```

#### ReferencePoint
```json
{
  "source": { "x": number, "y": number },
  "target": { "x": number, "y": number },
  "label": string  // e.g., "NW corner", "Camera 1"
}
```

## Transformation Algorithm

### Basic Transform (No Calibration)
```
siteowl_x = (source_x - min_x) / (max_x - min_x)
siteowl_y = 1.0 - ((source_y - min_y) / (max_y - min_y))  # Flip Y
```

### With Rotation
```
rotated = rotate_point(source, rotation_deg, center)
siteowl = basic_transform(rotated)
```

### With Calibration (Affine)
```
# Solve for affine matrix using reference points
# Apply matrix to all transformations
```

## Implementation Status

| Feature | Python | C# |
|---------|--------|-----|
| Basic transform | 🔲 | 🔲 |
| Rotation | 🔲 | 🔲 |
| Calibration | 🔲 | 🔲 |
| VIVE specifics | 🔲 | 🔲 |

Legend: 🔲 = Not started, 🟡 = In progress, ✅ = Complete
