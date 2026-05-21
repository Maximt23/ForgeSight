"""Configuration settings."""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings."""

    # App
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080
    SECRET_KEY: str = "cadowl-secret-key-change-in-production"

    # Branding
    BRAND_APP_NAME: str = "CadOwl"
    BRAND_TAGLINE: str = "Modern Survey Coordination Platform"
    BRAND_ICON_PATH: str = "/static/branding/cadowl.ico"
    BRAND_SHORTCUT_PATH: str = r"C:\Users\vn59j7j\OneDrive - Walmart Inc\Desktop\CadOwl.lnk"
    
    # Database
    DATABASE_URL: str = "sqlite:///cadowl.db"
    
    # MAXILLM / Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "maxillm"

    # Core API integration
    CORE_API_BASE_URL: str = "http://127.0.0.1:9010"
    
    # Knowledge Graph
    KNOWLEDGE_GRAPH_PATH: Path = Path("../knowledge-graph/graph.db")
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: list = [
        ".pdf", ".jpg", ".jpeg", ".png", ".svg", ".dxf", ".dwg", ".xlsx", ".docx"
    ]
    
    # Paths
    UPLOAD_DIR: Path = Path("uploads")
    EXPORT_DIR: Path = Path("exports")
    TEMP_DIR: Path = Path("temp")
    LOGS_DIR: Path = Path("logs")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Create directories
for directory in [settings.UPLOAD_DIR, settings.EXPORT_DIR, settings.TEMP_DIR, settings.LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
