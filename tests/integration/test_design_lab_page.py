from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_design_lab_page_loads() -> None:
    client = TestClient(app)

    resp = client.get("/design-lab")
    assert resp.status_code == 200
    html = resp.text

    assert "Design Lab" in html
    assert "Walmart Token Guardrails" in html
    assert "/design-research/forgesearch-preview.html" in html


def test_design_research_assets_are_served() -> None:
    client = TestClient(app)

    resp = client.get("/design-research/design-preview.html")
    assert resp.status_code == 200
    assert "<!doctype html>" in resp.text.lower()
