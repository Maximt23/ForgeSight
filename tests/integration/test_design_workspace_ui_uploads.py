from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_design_workspace_page_has_large_canvas_and_upload_controls() -> None:
    client = TestClient(app)

    resp = client.get("/projects/demo/design")
    assert resp.status_code == 200
    html = resp.text

    assert "Floorplan Upload (PDF / DWG / DXF / SVG / image)" in html
    assert "height=\"980\"" in html
    assert "Device Legend" in html


def test_floorplan_upload_accepts_svg_pdf_dxf() -> None:
    client = TestClient(app)

    files = [
        ("floor.svg", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "image/svg+xml", "svg"),
        ("floor.pdf", b"%PDF-1.4\n%mock\n", "application/pdf", "pdf"),
        ("floor.dxf", b"0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n", "application/dxf", "cad"),
    ]

    for name, content, mime, expected_kind in files:
        resp = client.post(
            "/ui-api/design/floorplans/upload",
            files={"file": (name, content, mime)},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["file_kind"] == expected_kind
        assert body["preview_url"].startswith("/ui-api/design/floorplans/")


def test_floorplan_upload_rejects_unsupported_extensions() -> None:
    client = TestClient(app)

    resp = client.post(
        "/ui-api/design/floorplans/upload",
        files={"file": ("payload.exe", b"MZ", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "Unsupported floorplan format" in resp.json()["detail"]
