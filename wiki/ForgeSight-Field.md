# 📱 ForgeSight Field

> **Mobile/VR Site Survey Application**

Capture real-world conditions with mobile devices and VIVE XR for accurate as-built documentation.

---

## Overview

ForgeSight Field bridges the gap between design and reality. Survey technicians use mobile devices or VR headsets to:

- Capture actual device locations
- Document site conditions
- Take georeferenced photos
- Validate design accuracy

---

## Platforms

### 📱 Mobile App (PWA)

Progressive Web App for iOS/Android:

- Works offline
- Camera integration
- GPS/indoor positioning
- Syncs when connected

### 🥽 VIVE XR Integration

Virtual reality for warehouse-scale surveys:

- Room-scale tracking
- Controller-based marking
- Real-time visualization
- Export to ForgeSight Grid

---

## Features

### 🎯 Device Marking

1. Walk to device location
2. Point at device
3. Click to mark
4. Add metadata

```csharp
// Unity/C# - VIVE XR
using ForgeSight.Field;

var marker = new DeviceMarker();
marker.OnDeviceMarked += (position, deviceType) => {
    var siteOwlCoords = transformer.Transform(position);
    SyncToCloud(siteOwlCoords, deviceType);
};
```

### 📸 Photo Documentation

- Georeferenced photos
- Automatic device association
- Cloud sync
- Annotation tools

### 🔄 Offline-First

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Field     │────►│   Local     │────►│   Cloud     │
│   Survey    │     │   Storage   │     │   Sync      │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │  Conflict   │
                    │  Resolution │
                    └─────────────┘
```

---

## VIVE XR Setup

### Requirements

- HTC VIVE Pro 2 or VIVE XR Elite
- SteamVR
- Calibration markers
- Windows 10/11

### Calibration

1. Place 3+ markers at known locations
2. Start ForgeSight Field VR
3. Point at each marker and confirm
4. System calculates transformation matrix

```csharp
// Calibration in Unity
CalibrationManager.AddPoint(vrPosition, siteOwlCoords);
CalibrationManager.AddPoint(vrPosition2, siteOwlCoords2);
CalibrationManager.AddPoint(vrPosition3, siteOwlCoords3);

var matrix = CalibrationManager.ComputeTransform();
// matrix is now ready for use
```

### Coordinate Transformation

```csharp
using ForgeSight.Shared.Transform;

var transformer = new CoordinateTransformer(ScaleMode.FitContain);
transformer.SetBounds(roomBounds);

// In VR update loop
var vrPos = controller.position;
var result = transformer.Transform(vrPos.x, vrPos.z); // VR Y is height

Debug.Log($"SiteOwl: ({result.SiteX}, {result.SiteY})");
```

---

## Mobile App Usage

### Starting a Survey

1. Login with Walmart SSO
2. Select site from list
3. Download floor plan (offline cache)
4. Begin survey

### Marking Devices

1. Tap "Add Device" button
2. Select device type
3. Position on floor plan (GPS or manual)
4. Capture photo
5. Add notes
6. Save

### Syncing

- Auto-sync when online
- Manual sync button
- Conflict resolution UI
- Progress indicator

---

## API Integration

### Submit Survey Data

```bash
POST /api/v1/field/surveys
Content-Type: application/json

{
  "site_id": "uuid",
  "surveyor": "tech@walmart.com",
  "devices": [
    {
      "type": "dome_camera",
      "x": 45.2,
      "y": 32.1,
      "photo_url": "https://...",
      "notes": "Mounted on column"
    }
  ]
}
```

### Get Survey Status

```bash
GET /api/v1/field/surveys/{survey_id}
```

---

## Best Practices

1. **Calibrate First** — Always calibrate before surveying
2. **Mark Consistently** — Point at device center
3. **Take Photos** — Document everything
4. **Sync Regularly** — Don't wait until end
5. **Note Issues** — Flag discrepancies

---

## Related

- [ForgeSight Grid](ForgeSight-Grid.md) — Coordinate engine
- [ForgeSight CAD](ForgeSight-CAD.md) — Compare with designs
- [Device Matching](../shared/matching/README.md) — Correlation algorithm
