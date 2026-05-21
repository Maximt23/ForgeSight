"""CadOwl - Modern Survey Coordination Platform."""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pathlib import Path
import logging
import httpx

from .config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="CadOwl",
    description="Modern Survey Coordination Platform - Better than SiteOwl Relay Coordinator",
    version="1.0.0"
)

# Setup static files and templates
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent
DESIGN_RESEARCH_DIR = PROJECT_ROOT / "docs" / "design-research"

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
if DESIGN_RESEARCH_DIR.exists():
    app.mount("/design-research", StaticFiles(directory=DESIGN_RESEARCH_DIR), name="design-research")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

BRAND = {
    "app_name": settings.BRAND_APP_NAME,
    "tagline": settings.BRAND_TAGLINE,
    "icon_path": settings.BRAND_ICON_PATH,
    "shortcut_path": settings.BRAND_SHORTCUT_PATH,
    "primary_color": "#0053e2",
    "accent_color": "#ffc220",
}
templates.env.globals["brand"] = BRAND


@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    icon_file = BASE_DIR / "static" / "branding" / "cadowl.ico"
    return FileResponse(icon_file)


# === HOME PAGE ===

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page."""
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request, "brand": BRAND})


# === DASHBOARD ===

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard."""
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "request": request,
        "brand": BRAND,
        "stats": {
            "total_stores": 0,
            "active_surveys": 0,
            "pending_reviews": 0,
            "vendors": 0
        }
    })


# === MODULE PAGES ===

@app.get("/surveys", response_class=HTMLResponse)
async def surveys(request: Request):
    return templates.TemplateResponse(request=request, name="module_placeholder.html", context={"request": request, "brand": BRAND, "title": "Surveys", "emoji": "📝"})


@app.get("/stores", response_class=HTMLResponse)
async def stores(request: Request):
    return templates.TemplateResponse(request=request, name="module_placeholder.html", context={"request": request, "brand": BRAND, "title": "Stores", "emoji": "🏪"})


@app.get("/floorplans", response_class=HTMLResponse)
async def floorplans(request: Request):
    return templates.TemplateResponse(request=request, name="module_placeholder.html", context={"request": request, "brand": BRAND, "title": "Floor Plans", "emoji": "🗺️"})


@app.get("/equipment", response_class=HTMLResponse)
async def equipment(request: Request):
    return templates.TemplateResponse(request=request, name="module_placeholder.html", context={"request": request, "brand": BRAND, "title": "Equipment", "emoji": "📦"})


@app.get("/vendors", response_class=HTMLResponse)
async def vendors(request: Request):
    return templates.TemplateResponse(request=request, name="module_placeholder.html", context={"request": request, "brand": BRAND, "title": "Vendors", "emoji": "🤝"})


@app.get("/photos", response_class=HTMLResponse)
async def photos(request: Request):
    return templates.TemplateResponse(request=request, name="module_placeholder.html", context={"request": request, "brand": BRAND, "title": "Photos", "emoji": "📸"})


@app.get("/reports", response_class=HTMLResponse)
async def reports(request: Request):
    return templates.TemplateResponse(request=request, name="module_placeholder.html", context={"request": request, "brand": BRAND, "title": "Reports", "emoji": "📄"})


@app.get("/ai-assistant", response_class=HTMLResponse)
async def ai_assistant(request: Request):
    return templates.TemplateResponse(request=request, name="module_placeholder.html", context={"request": request, "brand": BRAND, "title": "AI Assistant", "emoji": "🤖"})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse(request=request, name="module_placeholder.html", context={"request": request, "brand": BRAND, "title": "Settings", "emoji": "⚙️"})


# === FORGESIGHT PRODUCT TABS ===

@app.get("/cad", response_class=HTMLResponse)
async def cad_product(request: Request):
    return templates.TemplateResponse(request=request, name="module_placeholder.html", context={"request": request, "brand": BRAND, "title": "ForgeSight CAD", "emoji": "📐"})


@app.get("/field", response_class=HTMLResponse)
async def field_product(request: Request):
    return templates.TemplateResponse(request=request, name="module_placeholder.html", context={"request": request, "brand": BRAND, "title": "ForgeSight Field", "emoji": "📱"})


@app.get("/vision", response_class=HTMLResponse)
async def vision_product(request: Request):
    return templates.TemplateResponse(request=request, name="module_placeholder.html", context={"request": request, "brand": BRAND, "title": "ForgeSight Vision", "emoji": "👁️"})


@app.get("/grid", response_class=HTMLResponse)
async def grid_product(request: Request):
    return templates.TemplateResponse(request=request, name="module_placeholder.html", context={"request": request, "brand": BRAND, "title": "ForgeSight Grid", "emoji": "🗺️"})


@app.get("/autodesign", response_class=HTMLResponse)
async def autodesign_product(request: Request):
    return templates.TemplateResponse(request=request, name="module_placeholder.html", context={"request": request, "brand": BRAND, "title": "ForgeSight AutoDesign", "emoji": "🧠"})


@app.get("/maxillm", response_class=HTMLResponse)
async def maxillm_product(request: Request):
    return templates.TemplateResponse(request=request, name="module_placeholder.html", context={"request": request, "brand": BRAND, "title": "MAXILLM Training", "emoji": "🎓"})


# === NEW UI SURFACES ===

@app.get("/sectors", response_class=HTMLResponse)
async def sectors(request: Request):
    return templates.TemplateResponse(request=request, name="sectors.html", context={"request": request, "brand": BRAND})


@app.get("/export-center", response_class=HTMLResponse)
async def export_center(request: Request):
    return templates.TemplateResponse(request=request, name="export_center.html", context={"request": request, "brand": BRAND})


@app.get("/design-lab", response_class=HTMLResponse)
async def design_lab(request: Request):
    """Stable in-repo UI playground using the 2026-05-21 design baseline."""
    return templates.TemplateResponse(
        request=request,
        name="design_lab.html",
        context={
            "request": request,
            "brand": BRAND,
            "baseline_available": DESIGN_RESEARCH_DIR.exists(),
            "baseline_path": str(DESIGN_RESEARCH_DIR),
        },
    )


@app.get("/projects/{project_id}/design", response_class=HTMLResponse)
async def project_design(request: Request, project_id: str):
    return templates.TemplateResponse(
        request=request,
        name="design_workspace.html",
        context={"request": request, "brand": BRAND, "project_id": project_id},
    )


# === FORGESEARCH API (design baseline contract) ===

@app.post("/api/forgesearch/classify")
async def forgesearch_classify(request: Request):
    payload = await request.json()
    text = str(payload.get("input", "")).strip().lower()

    intent = "query"
    if any(k in text for k in ("delete", "remove", "clear", "reset")):
        intent = "destructive"
    elif any(k in text for k in ("validate", "audit", "check", "compliance")):
        intent = "validate"
    elif any(k in text for k in ("move", "rename", "connect", "reassign")):
        intent = "modify"
    elif any(k in text for k in ("export", "csv", "pdf", "siteowl")):
        intent = "export"
    elif any(k in text for k in ("create", "add", "generate", "design", "draw")):
        intent = "generate"

    return {"intent": intent, "confidence": 0.72, "source": "rules-v1"}


@app.post("/api/forgesearch/execute")
async def forgesearch_execute(request: Request):
    payload = await request.json()
    return {
        "status": "accepted",
        "summary": "Execution preview generated.",
        "intent": payload.get("intent", "query"),
        "results": payload.get("results", []),
    }


# === UI -> CORE API BRIDGE ===

@app.post("/ui-api/exports/{export_type}")
async def ui_export_bridge(export_type: str, request: Request):
    payload = await request.json()
    url = f"{settings.CORE_API_BASE_URL}/api/exports/{export_type}"
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload)
        return JSONResponse(status_code=response.status_code, content=response.json())
    except Exception as exc:
        return JSONResponse(status_code=502, content={"detail": f"Core API unavailable: {exc}"})


@app.get("/ui-api/exports/history")
async def ui_export_history(limit: int = 25):
    url = f"{settings.CORE_API_BASE_URL}/api/exports/history"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params={"limit": limit})
        return JSONResponse(status_code=response.status_code, content=response.json())
    except Exception as exc:
        return JSONResponse(status_code=502, content={"detail": f"Core API unavailable: {exc}"})


@app.get("/ui-api/exports/{export_id}")
async def ui_export_metadata(export_id: str):
    url = f"{settings.CORE_API_BASE_URL}/api/exports/{export_id}/metadata"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
        return JSONResponse(status_code=response.status_code, content=response.json())
    except Exception as exc:
        return JSONResponse(status_code=502, content={"detail": f"Core API unavailable: {exc}"})


@app.get("/ui-api/projects/{project_id}/devices")
async def ui_project_devices(project_id: str, site_number: str):
    url = f"{settings.CORE_API_BASE_URL}/api/v1/devices"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params={"project_id": project_id, "site_number": site_number})
        return JSONResponse(status_code=response.status_code, content=response.json())
    except Exception as exc:
        return JSONResponse(status_code=502, content={"detail": f"Core API unavailable: {exc}"})


@app.post("/ui-api/projects/{project_id}/devices")
async def ui_create_device(project_id: str, request: Request):
    payload = await request.json()
    payload["project_id"] = project_id
    url = f"{settings.CORE_API_BASE_URL}/api/v1/devices"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
        return JSONResponse(status_code=response.status_code, content=response.json())
    except Exception as exc:
        return JSONResponse(status_code=502, content={"detail": f"Core API unavailable: {exc}"})


@app.get("/ui-api/projects/{project_id}/zones")
async def ui_project_zones(project_id: str, floor_id: str):
    url = f"{settings.CORE_API_BASE_URL}/api/v1/zones"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params={"project_id": project_id, "floor_id": floor_id})
        return JSONResponse(status_code=response.status_code, content=response.json())
    except Exception as exc:
        return JSONResponse(status_code=502, content={"detail": f"Core API unavailable: {exc}"})


@app.post("/ui-api/projects/{project_id}/zones")
async def ui_create_zone(project_id: str, request: Request):
    payload = await request.json()
    payload["project_id"] = project_id
    url = f"{settings.CORE_API_BASE_URL}/api/v1/zones"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
        return JSONResponse(status_code=response.status_code, content=response.json())
    except Exception as exc:
        return JSONResponse(status_code=502, content={"detail": f"Core API unavailable: {exc}"})


@app.get("/ui-api/projects/{project_id}/cables")
async def ui_project_cables(project_id: str, site_number: str):
    url = f"{settings.CORE_API_BASE_URL}/api/v1/cables"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params={"project_id": project_id, "site_number": site_number})
        return JSONResponse(status_code=response.status_code, content=response.json())
    except Exception as exc:
        return JSONResponse(status_code=502, content={"detail": f"Core API unavailable: {exc}"})


@app.post("/ui-api/projects/{project_id}/cables")
async def ui_create_cable(project_id: str, request: Request):
    payload = await request.json()
    payload["project_id"] = project_id
    url = f"{settings.CORE_API_BASE_URL}/api/v1/cables"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
        return JSONResponse(status_code=response.status_code, content=response.json())
    except Exception as exc:
        return JSONResponse(status_code=502, content={"detail": f"Core API unavailable: {exc}"})


@app.get("/ui-api/build-status")
async def ui_build_status():
    return {
        "platform": "ForgeSight / CadOwl / MAXILLM",
        "directive": "zero-hallucination",
        "modules": [
            {"name": "Project Management", "status": "implemented"},
            {"name": "Design Workspace", "status": "in_progress"},
            {"name": "Interactive Canvas", "status": "in_progress"},
            {"name": "Device Library", "status": "planned"},
            {"name": "Device Families", "status": "planned"},
            {"name": "Batch Import Center", "status": "implemented"},
            {"name": "Batch Delete / Re-upload Engine", "status": "planned"},
            {"name": "Validation Engine", "status": "implemented"},
            {"name": "Metadata Engine", "status": "implemented"},
            {"name": "Export Center", "status": "implemented"},
            {"name": "Zone Engine", "status": "implemented"},
            {"name": "Cable / Topology Engine", "status": "implemented"},
            {"name": "Camera FOV / Coverage Engine", "status": "planned"},
            {"name": "Coordinate / GIS Engine", "status": "implemented"},
            {"name": "AI Design Command System", "status": "planned"},
            {"name": "MAXILLM Design Intelligence", "status": "in_progress"},
            {"name": "Event / Audit Log", "status": "implemented"},
            {"name": "Revision / Rollback System", "status": "implemented"},
            {"name": "API Layer", "status": "implemented"},
            {"name": "Admin / Development Intelligence Layer", "status": "planned"},
        ],
        "note": "Modules marked planned are explicitly not complete.",
    }


# === API HEALTH CHECK ===

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "ai_connected": True
    }


@app.get("/api/stats/stores", response_class=HTMLResponse)
async def stores_stat():
    return "<span>750</span>"


# === STARTUP EVENT ===

@app.on_event("startup")
async def startup():
    """Run on startup."""
    logger.info("🦉 CadOwl starting up...")
    logger.info(f"📍 Host: {settings.APP_HOST}:{settings.APP_PORT}")
    logger.info(f"🤖 AI Model: {settings.OLLAMA_MODEL}")
    logger.info("✅ Ready to fly!")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True
    )
