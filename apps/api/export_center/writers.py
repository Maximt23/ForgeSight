import csv
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from openpyxl import Workbook
from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from cadowl.core.exporter import SITEOWL_HEADERS


def write_json(path: Path, payload: dict | list) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_xlsx(path: Path, sheets: dict[str, list[dict]]) -> None:
    wb = Workbook()
    first = True
    for sheet_name, rows in sheets.items():
        ws = wb.active if first else wb.create_sheet()
        ws.title = sheet_name[:31]
        first = False
        if not rows:
            ws.append(["empty"])
            continue
        headers = list(rows[0].keys())
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h) for h in headers])
    wb.save(path)


def write_pdf(path: Path, title: str, lines: list[str]) -> None:
    pdf = canvas.Canvas(str(path), pagesize=letter)
    _, h = letter
    y = h - 40
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, title)
    y -= 24
    pdf.setFont("Helvetica", 10)
    for line in lines:
        pdf.drawString(40, y, line[:120])
        y -= 14
        if y < 40:
            pdf.showPage()
            y = h - 40
            pdf.setFont("Helvetica", 10)
    pdf.save()


def device_geojson_rows(devices: list[dict]) -> dict:
    features = []
    for d in devices:
        x, y = d.get("local_x", 0), d.get("local_y", 0)
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [x, y]},
                "properties": {"device_id": d.get("device_id"), "name": d.get("device_name")},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def cad_drawings(out_dir: Path, devices: list[dict]) -> list[str]:
    written: list[str] = []

    svg_path = out_dir / "cad_layout.svg"
    circles = []
    for d in devices:
        x = max(0, min(100, float(d.get("local_x") or 0))) * 8
        y = max(0, min(100, float(d.get("local_y") or 0))) * 8
        circles.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#0053e2" />')
    svg = "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800">',
            '<rect width="800" height="800" fill="white" stroke="#d9d9d9"/>',
            *circles,
            "</svg>",
        ]
    )
    svg_path.write_text(svg, encoding="utf-8")
    written.append(str(svg_path))

    png_path = out_dir / "cad_layout.png"
    img = Image.new("RGB", (800, 800), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (799, 799)], outline="#cccccc")
    for d in devices:
        x = max(0, min(100, float(d.get("local_x") or 0))) * 8
        y = max(0, min(100, float(d.get("local_y") or 0))) * 8
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill="#0053e2")
    img.save(png_path)
    written.append(str(png_path))

    pdf_path = out_dir / "cad_layout.pdf"
    write_pdf(pdf_path, "CAD Layout Summary", [f"Devices plotted: {len(devices)}"])
    written.append(str(pdf_path))

    dxf_path = out_dir / "cad_layout.dxf"
    entities = []
    for d in devices:
        x = max(0, min(100, float(d.get("local_x") or 0)))
        y = max(0, min(100, float(d.get("local_y") or 0)))
        entities.extend(["0", "POINT", "8", "DEVICES", "10", f"{x}", "20", f"{y}", "30", "0.0"])
    dxf = [
        "0", "SECTION", "2", "HEADER", "0", "ENDSEC",
        "0", "SECTION", "2", "ENTITIES", *entities, "0", "ENDSEC", "0", "EOF",
    ]
    dxf_path.write_text("\n".join(dxf), encoding="utf-8")
    written.append(str(dxf_path))

    return written


def siteowl_rows(devices: list[dict], site_number: str) -> list[dict]:
    rows = []
    for idx, d in enumerate(devices, start=1):
        row = {h: "" for h in SITEOWL_HEADERS}
        row["Project ID"] = site_number
        row["Plan ID"] = str(idx)
        row["Device ID"] = f"New{idx:04d}"
        row["Name"] = d.get("device_name") or f"Device {idx}"
        row["Device / Task"] = "Device"
        row["System Type"] = "Video Surveillance"
        row["Device/Task Type"] = d.get("device_type") or "Camera"
        x = float(d.get("local_x", 0))
        y = float(d.get("local_y", 0))
        row["Coordinates"] = f'"({x:05.2f}, {y:05.2f})"'
        rows.append(row)
    return rows


def build_manifest(export_id: str, export_type: str, request, metadata: dict, files: list[str]) -> dict:
    val_rows = metadata.get("validation_metadata", [])
    device_rows = metadata.get("device_metadata", [])
    coord_conf = [x.get("coordinate_confidence", 0) for x in device_rows] or [100]
    score = 100 - (len([v for v in val_rows if v.get("severity") == "critical"]) * 5)
    return {
        "export_id": export_id,
        "project_id": str(request.project_id),
        "site_number": metadata["project_metadata"]["site_number"],
        "export_type": export_type,
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": request.created_by,
        "app_version": "1.0.0",
        "schema_version": "2026.05",
        "files_included": files,
        "record_counts": {
            "devices": len(device_rows),
            "zones": len(metadata.get("zone_metadata", [])),
            "cables": len(metadata.get("cable_metadata", [])),
            "validation_errors": len(val_rows),
            "ai_suggestions": len(metadata.get("ai_metadata", [])),
        },
        "validation_score": max(0, score),
        "coordinate_confidence": round(sum(coord_conf) / max(1, len(coord_conf)), 2),
        "rollback_available": True,
    }


def write_zip(zip_path: Path, out_dir: Path, files: list[str]) -> str:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_name in files:
            zf.write(out_dir / file_name, arcname=file_name)
    return str(zip_path)
