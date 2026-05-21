# ⚡ Quick Start

Get CadOwl running in 5 minutes!

---

## Prerequisites

- Python 3.11+
- Git
- Walmart VPN or Eagle WiFi

---

## 1. Clone the Repository

```bash
git clone https://gecgithub01.walmart.com/vn59j7j/CadOwl.git
cd CadOwl
```

## 2. Set Up Environment

```bash
# Create virtual environment
uv venv

# Install dependencies
uv pip install -r requirements.txt --index-url https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple
```

## 3. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env file
# For local development, set:
#   CADOWL_DEV_MODE=true
```

## 4. Start the API Server

```bash
uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 9010 --reload
```

## 5. Open the Dashboard

Navigate to: **http://localhost:9010**

You should see the CadOwl dashboard!

---

## 🎯 First Steps

### Create Your First Site

```bash
curl -X POST http://localhost:9010/api/v1/sites \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "00000000-0000-0000-0000-000000000001",
    "site_number": "1234",
    "name": "My First Store",
    "site_type": "sandbox"
  }'
```

### Create a Design

```bash
curl -X POST http://localhost:9010/api/v1/designs \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "00000000-0000-0000-0000-000000000001",
    "site_id": "<site_id_from_above>",
    "name": "CCTV Design v1",
    "design_type": "cctv",
    "priority": "normal"
  }'
```

### Import a CAD File

```bash
uv run python -m cadowl convert path/to/drawing.dxf -o output.csv --store 1234
```

---

## 📚 Next Steps

- [Site Lifecycle Guide](User-Guide-Site-Lifecycle.md) — Understand site phases
- [Design Workflow](User-Guide-Design-Workflow.md) — Learn the approval process
- [API Reference](Dev-API-Reference.md) — Full API documentation

---

## 🆘 Need Help?

- Check the [FAQ](FAQ.md)
- Visit [Troubleshooting](Troubleshooting.md)
- Ask in [#cadowl-support](https://walmart.enterprise.slack.com/archives/C094Y1D24JY)
