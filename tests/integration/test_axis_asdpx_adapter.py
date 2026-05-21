from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.adapters.axis_siteowl_adapter import convert_asdpx_to_siteowl_rows
from apps.api.main import app


def test_asdpx_conversion_rows():
    source = Path(r"C:\MAXILLM\cadowl\data\sample-imports\siteowl_workflow_v2\Sample_2996.asdpx")
    assert source.exists()

    rows, meta = convert_asdpx_to_siteowl_rows(source)
    assert meta["row_count"] > 0
    assert len(rows) == meta["row_count"]

    sample = rows[0]
    assert sample["System Type"] == "Video Surveillance"
    assert sample["Coordinates"].startswith('"(')
    assert "," in sample["Field Notes"]


def test_asdpx_preview_endpoint():
    source = str(Path(r"C:\MAXILLM\cadowl\data\sample-imports\siteowl_workflow_v2\Sample_2996.asdpx"))
    client = TestClient(app)

    r = client.post("/api/v1/import/asdpx/preview", json={"source_path": source})
    assert r.status_code == 200
    body = r.json()
    assert body["row_count"] > 0
    assert len(body["sample_rows"]) > 0
