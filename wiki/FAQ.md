# ❓ Frequently Asked Questions

---

## General

### What is CadOwl?

CadOwl is an enterprise security design platform that replaces manual CAD-to-SiteOwl workflows. It provides:
- Automated CAD file processing
- Design workflow management
- VR coordinate capture (VIVE XR)
- Device matching and merging
- Integration with Walmart systems

### How is CadOwl different from SiteOwl?

| Feature | SiteOwl | CadOwl |
|:--------|:--------|:-------|
| CAD Import | Manual CSV | Automated |
| Workflow | Basic | Full approval flow |
| VR Support | None | VIVE XR integration |
| AI Assist | None | Element AI integration |
| Offline | No | Yes (PWA) |

### Who should use CadOwl?

- Security designers creating floor plans
- Program managers overseeing projects
- Vendors performing installations
- QA reviewers validating designs

---

## Authentication

### How do I log in?

CadOwl uses Walmart SSO. Click "Login" and authenticate with your Walmart credentials.

### Why can't I approve designs?

You need the `reviewer` or `pm` role. Contact your admin to request role assignment.

### How do I get admin access?

Contact the CadOwl team via [Teams](https://teams.microsoft.com/...) or [Slack](https://walmart.enterprise.slack.com/...).

---

## Sites & Designs

### What's the difference between site types?

| Type | Purpose |
|:-----|:--------|
| Sandbox | Testing, prototyping |
| Design | Active planning |
| Installation | Being built |
| Live | Operational |
| Archived | Historical |

### Why can't I edit a design?

Designs become read-only after certain status transitions:
- **Submitted** — Waiting for review
- **Approved** — Ready for installation
- **Complete** — Installation done

Only designers can edit during **Draft** or **Revision Required** states.

### How do I request changes to an approved design?

Contact the PM to create a new design version. Approved designs cannot be modified.

---

## CAD Import

### What CAD formats are supported?

- **DXF** — Full support
- **DWG** — Requires conversion to DXF first

### Why aren't all my devices detected?

CadOwl uses pattern matching for device detection. If devices aren't detected:
1. Check block/layer naming conventions
2. Add custom patterns to `detector.py`
3. Use the `--report` flag to see unmatched blocks

### How do I add custom device patterns?

Edit `cadowl/core/detector.py` and add to `BLOCK_PATTERNS`:

```python
DevicePattern(r"(?i)^MY_CAMERA.*", SystemType.VIDEO_SURVEILLANCE, DeviceType.DOME_CAMERA, 1.0),
```

---

## Integrations

### How does VIVE XR integration work?

1. Calibrate VR space to floor plan
2. Walk to device locations in VR
3. Mark devices with controller
4. Export coordinates to CadOwl
5. Match with CAD devices

### Can I export back to SiteOwl?

Yes! Use the export feature:

```bash
uv run python -m cadowl convert input.dxf -o output.csv --format siteowl
```

---

## Troubleshooting

### The API won't start

1. Check `.env` file exists
2. Verify port 9010 is available
3. Check Python version (3.11+)
4. Run `uv pip install -r requirements.txt`

### SSO login fails

1. Verify VPN/Eagle WiFi connection
2. Clear browser cookies
3. Try incognito mode
4. Check Azure AD app registration

### Device coordinates are wrong

1. Verify CAD drawing units (feet vs inches)
2. Check coordinate transformation settings
3. Use calibration points for adjustment

---

## Related

- [Troubleshooting](Troubleshooting.md)
- [Quick Start](Quick-Start.md)
- [Glossary](Glossary.md)
