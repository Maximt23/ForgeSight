"""CadOwl - Modern Survey Coordination Platform."""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
import logging

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
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
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
