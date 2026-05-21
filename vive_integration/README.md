# VIVE XR Integration Module

## Overview

Unity/C# components for mapping VIVE XR tracking coordinates to SiteOwl.

## Components

### ViveCoordinateMapper.cs
Main coordinate transformation for VIVE headset/controller positions.

```csharp
// Attach to any GameObject that needs position mapping
public class ViveCoordinateMapper : MonoBehaviour
{
    public FloorConfig floor;
    
    public SiteOwlCoord GetCurrentPosition()
    {
        var vivePos = transform.position;
        return transformer.ToSiteOwl(vivePos.x, vivePos.z, vivePos.y);
    }
}
```

### DeviceMatcher.cs
Matches VR-scanned device positions to CAD-imported devices.

```csharp
public class DeviceMatcher
{
    // Find matching device within tolerance
    public Device FindMatch(SiteOwlCoord position, float tolerance = 0.05f);
    
    // Batch match all scanned devices
    public MatchResult[] MatchAll(Device[] cadDevices, Device[] vrDevices);
}
```

### CalibrationWizard.cs
Interactive UI for floor calibration using known reference points.

## Setup

1. Import shared JSON schemas
2. Configure floor bounds in Inspector
3. Run calibration wizard
4. Start device scanning

## Coordinate Flow

```
VIVE Controller Position (meters, Y-up)
         │
         ▼
ViveCoordinateMapper.ToSiteOwl()
         │
         ▼
SiteOwl Normalized Coords (0-1, Y-down)
         │
         ▼
DeviceMatcher.FindMatch()
         │
         ▼
Matched Device from CAD import
```

## Dependencies

- SteamVR Plugin 2.x
- Newtonsoft.Json (for schema validation)
- shared/transform/TransformCore.cs

## Testing

1. Load test scene with mock floor
2. Run `TestTransform.cs` unit tests
3. Verify against `test_vectors.json`
