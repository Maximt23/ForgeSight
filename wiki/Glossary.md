# 📖 Glossary

Common terms and definitions used in CadOwl.

---

## A

### Artboard
The 1000x1000 unit canvas used for coordinate normalization. Floor plans are centered within an 800x800 area with 100-unit margins.

### Azure AD
Microsoft Entra ID (formerly Azure Active Directory). Walmart's identity provider for SSO.

---

## B

### Block (CAD)
A reusable symbol in CAD drawings. Devices are typically represented as block insertions.

---

## C

### CAD
Computer-Aided Design. Software for creating technical drawings (AutoCAD, etc.).

### Commissioning
The process of testing and verifying an installed security system before going live.

### Coordinate Transformation
Converting coordinates from one system (CAD, VR) to another (SiteOwl).

---

## D

### Design
A security system plan for a site. Includes device layouts, specifications, and workflow status.

### Design Type
The category of security system: CCTV, Fire Alarm, Intrusion, Access Control, etc.

### Device
A physical security component: camera, smoke detector, card reader, etc.

### DXF
Drawing Exchange Format. An open CAD file format that CadOwl can import directly.

### DWG
AutoCAD's native file format. Requires conversion to DXF for import.

---

## E

### Element AI
Walmart's internal AI platform used for design assistance and review suggestions.

---

## F

### Floor Plan
A top-down view of a building floor showing device locations.

---

## H

### Hungarian Algorithm
An optimization algorithm used for matching devices from multiple sources.

---

## I

### INSERT (CAD)
A CAD entity representing a block placed in a drawing. Each INSERT has position, rotation, and scale.

---

## J

### JSONL
JSON Lines format. Each line is a valid JSON object. Used for event logging.

### JWT
JSON Web Token. The authentication token format used by CadOwl.

---

## L

### Layer (CAD)
A logical grouping in CAD drawings. Devices are often organized on specific layers (e.g., "CCTV", "FIRE_ALARM").

### Lifecycle
The phases a site moves through: Sandbox → Design → Installation → Live → Archived.

---

## M

### Merge Strategy
Rules for combining device data from multiple sources (CAD, VR, manual entry).

---

## P

### Pattern Matching
The process of identifying devices in CAD files using regex patterns on block/layer names.

### Permission
A specific action a user can perform (e.g., `design:approve`).

### Priority
Urgency level for designs: Critical, High, Normal, Low, Backlog.

### PVM
Public View Monitor. Screens displaying camera feeds in public areas.

---

## R

### Role
A collection of permissions assigned to users: Viewer, Designer, Reviewer, PM, Admin.

---

## S

### Sandbox
A testing environment for prototyping designs without affecting production data.

### SiteOwl
The existing security design platform that CadOwl enhances/replaces.

### SiteOwl Coordinates
Normalized coordinates in the 0-100 range used by SiteOwl's web interface.

### SSO
Single Sign-On. Authentication that allows using one set of credentials across multiple systems.

### Status
The current workflow state of a design: Draft, Submitted, In Review, Approved, etc.

---

## T

### Transition
Moving a site or design from one status/type to another (e.g., Draft → Submitted).

---

## V

### VIVE XR
HTC VIVE virtual reality headset used for walking store layouts and capturing device coordinates.

### Vendor
A third-party company that performs security system installations.

---

## W

### Workflow
The sequence of status transitions a design follows from creation to production.

---

## Related

- [FAQ](FAQ.md)
- [Architecture](Dev-Architecture.md)
- [API Reference](Dev-API-Reference.md)
