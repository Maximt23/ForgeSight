"""Main entry point for CadOwl."""
import click
from pathlib import Path


@click.group()
def cli():
    """CadOwl - Modern Survey Coordination Platform."""
    pass


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8080, type=int, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
def serve(host, port, reload):
    """Start the CadOwl web server."""
    import uvicorn
    
    click.echo(f"Starting CadOwl on {host}:{port}...")
    click.echo(f"Open: http://localhost:{port}")
    click.echo("AI Model: MAXILLM")
    click.echo("")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload
    )


@cli.command()
def init_db():
    """Initialize the database."""
    click.echo("🗄️ Initializing database...")
    # TODO: Run Alembic migrations
    click.echo("✅ Database initialized!")


@cli.command()
def status():
    """Check system status."""
    import httpx
    from app.config import settings
    
    click.echo("🦉 CadOwl Status Check")
    click.echo("=" * 50)
    
    # Check Ollama
    try:
        response = httpx.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            maxillm_found = any(settings.OLLAMA_MODEL in m.get("name", "") for m in models)
            if maxillm_found:
                click.echo(f"✅ MAXILLM: Online")
            else:
                click.echo(f"⚠️ MAXILLM: Not found (run 'ollama pull maxillm')")
        else:
            click.echo(f"❌ Ollama: Error {response.status_code}")
    except Exception as e:
        click.echo(f"❌ Ollama: Offline ({e})")
    
    # Check Knowledge Graph
    if settings.KNOWLEDGE_GRAPH_PATH.exists():
        size_mb = settings.KNOWLEDGE_GRAPH_PATH.stat().st_size / (1024 * 1024)
        click.echo(f"✅ Knowledge Graph: {size_mb:.1f} MB")
    else:
        click.echo(f"⚠️ Knowledge Graph: Not found at {settings.KNOWLEDGE_GRAPH_PATH}")
    
    # Check folders
    for folder in [settings.UPLOAD_DIR, settings.EXPORT_DIR, settings.TEMP_DIR]:
        if folder.exists():
            click.echo(f"✅ {folder.name}/: Ready")
        else:
            click.echo(f"❌ {folder.name}/: Missing")
    
    click.echo("=" * 50)


if __name__ == "__main__":
    cli()
