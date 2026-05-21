#!/usr/bin/env python3
"""Build or update CadOwl intelligent memory library from DWG/DXF files."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Iterable

from cadowl_memory import CadMemoryLibrary
from dwg_converter import convert_dwg_to_dxf


def collect_files(paths: Iterable[Path], recursive: bool, suffix: str) -> list[Path]:
    """Collect files for a given suffix from mixed file/folder inputs."""
    suffix = suffix.lower()
    pattern = f"**/*{suffix}" if recursive else f"*{suffix}"
    found: list[Path] = []

    for raw in paths:
        path = Path(raw)
        if path.is_file() and path.suffix.lower() == suffix:
            found.append(path)
            continue

        if path.is_dir():
            found.extend(p for p in path.glob(pattern) if p.is_file())

    # Stable + de-duped
    unique = {str(p.resolve()).lower(): p for p in found}
    return sorted(unique.values(), key=lambda p: str(p).lower())


def convert_selected_dwgs(dwg_files: list[Path], staging_folder: Path) -> tuple[list[Path], list[str]]:
    """Convert only selected DWG files by copying them into a temp conversion batch."""
    if not dwg_files:
        return ([], [])

    staging_folder.mkdir(parents=True, exist_ok=True)
    batch_input = staging_folder / "_dwg_batch_input"

    if batch_input.exists():
        shutil.rmtree(batch_input)
    batch_input.mkdir(parents=True, exist_ok=True)

    used_names: set[str] = set()
    for idx, dwg in enumerate(dwg_files, start=1):
        name = dwg.name
        if name.lower() in used_names:
            name = f"{dwg.stem}_{idx:03d}{dwg.suffix}"
        used_names.add(name.lower())
        shutil.copy2(dwg, batch_input / name)

    converted, failed, errors = convert_dwg_to_dxf(batch_input, staging_folder)

    print(f"\n[TRAIN] DWG conversion result: {converted} converted, {failed} failed")
    if errors:
        for err in errors:
            print(f"  - {err}")

    converted_dxf = sorted(
        p for p in staging_folder.glob("*.dxf") if p.is_file()
    )

    return (converted_dxf, errors)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest DWG/DXF files into an intelligent CAD memory tree"
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="One or more files/folders containing DWG/DXF",
    )
    parser.add_argument(
        "--db",
        type=Path,
        help="Custom SQLite DB path (default: cadowl_memory.db in project root)",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not recurse into subfolders",
    )
    parser.add_argument(
        "--department-map",
        type=Path,
        help="JSON file mapping department code to name (e.g. A/Y/Z)",
    )
    parser.add_argument(
        "--system",
        choices=["Fire Alarm", "Video Surveillance", "Intrusion Detection", "Unknown"],
        default="Fire Alarm",
        help="System to generate recommendations for",
    )
    parser.add_argument(
        "--convert-dwg",
        action="store_true",
        help="Convert selected DWG files to DXF first, then ingest converted DXF deeply",
    )
    parser.add_argument(
        "--staging-folder",
        type=Path,
        default=Path(__file__).resolve().parent / "Output" / "Memory-Staging",
        help="Where converted DXF files should be staged when --convert-dwg is used",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional JSON report output file",
    )
    args = parser.parse_args()

    recursive = not args.no_recursive
    input_paths = [Path(p) for p in args.paths]

    selected_dxf = collect_files(input_paths, recursive=recursive, suffix=".dxf")
    selected_dwg = collect_files(input_paths, recursive=recursive, suffix=".dwg")

    ingest_targets: list[Path] = [*selected_dxf]
    conversion_errors: list[str] = []

    if args.convert_dwg:
        converted_dxf, conversion_errors = convert_selected_dwgs(selected_dwg, args.staging_folder)
        ingest_targets.extend(converted_dxf)

    if not ingest_targets:
        print("\nNo ingestable DXF files were found.")
        if selected_dwg and not args.convert_dwg:
            print("Tip: DWG files were found; rerun with --convert-dwg for deep training.")
        return

    # De-dupe targets
    ingest_targets = sorted(
        {str(p.resolve()).lower(): p for p in ingest_targets}.values(),
        key=lambda p: str(p).lower(),
    )

    lib = CadMemoryLibrary(db_path=args.db, department_map_path=args.department_map)
    ingest_results = lib.ingest_paths(ingest_targets, recursive=False)

    ok = [r for r in ingest_results if r.status in {"ingested", "pending_dxf"}]
    failed = [r for r in ingest_results if r.status not in {"ingested", "pending_dxf"}]

    print("\n" + "=" * 68)
    print("CadOwl Intelligent Memory Library")
    print("=" * 68)
    print(f"Input paths: {len(input_paths)}")
    print(f"Selected DXF: {len(selected_dxf)} | Selected DWG: {len(selected_dwg)}")
    if args.convert_dwg:
        print(f"Converted DXF staged: {len([p for p in ingest_targets if p.parent == args.staging_folder])}")
    print(f"Processed entries: {len(ingest_results)}")
    print(f"Successful: {len(ok)} | Issues: {len(failed)}")

    if conversion_errors:
        print("\nDWG conversion issues:")
        for err in conversion_errors:
            print(f"  - {err}")

    if failed:
        print("\nIngest issues:")
        for row in failed[:20]:
            print(f"  - [{row.status}] {row.path} :: {row.notes}")

    stats = lib.summary()
    print("\nLibrary Stats:")
    for key, val in stats.items():
        print(f"  {key}: {val}")

    print("\nTop system->department edges:")
    dept_edges = lib.top_nodes("system_to_department", limit=10)
    if dept_edges:
        for edge in dept_edges:
            print(f"  {edge['parent_key']} -> {edge['child_key']} ({edge['weight']})")
    else:
        print("  (none yet)")

    print("\nTop department->aisle edges:")
    dept_aisle_edges = lib.top_nodes("department_to_aisle", limit=10)
    if dept_aisle_edges:
        for edge in dept_aisle_edges:
            print(f"  {edge['parent_key']} -> {edge['child_key']} ({edge['weight']})")
    else:
        print("  (none yet)")

    print("\nTop system->layer edges:")
    for edge in lib.top_nodes("system_to_layer", limit=10):
        print(f"  {edge['parent_key']} -> {edge['child_key']} ({edge['weight']})")

    recommendations = lib.recommended_patterns(args.system, top_n=12)
    print(f"\nRecommended pattern tree for {args.system}:")
    print("  Departments:", ", ".join(recommendations.get("departments", [])) or "(none)")
    print("  Aisles:     ", ", ".join(recommendations.get("aisles", [])) or "(none)")
    print("  Directions: ", ", ".join(recommendations.get("aisle_directions", [])) or "(none)")
    print("  Layers:     ", ", ".join(recommendations["layers"]) or "(none)")
    print("  Blocks:     ", ", ".join(recommendations["blocks"]) or "(none)")
    print("  Tags:       ", ", ".join(recommendations["tags"]) or "(none)")

    if args.json_out:
        payload = {
            "stats": stats,
            "recommendations": recommendations,
            "results": [
                {
                    "path": str(r.path),
                    "status": r.status,
                    "detected_devices": r.detected_devices,
                    "total_inserts": r.total_inserts,
                    "notes": r.notes,
                }
                for r in ingest_results
            ],
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nJSON report written: {args.json_out}")

    print("=" * 68 + "\n")


if __name__ == "__main__":
    main()
