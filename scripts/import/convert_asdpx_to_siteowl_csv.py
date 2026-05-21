"""CLI converter: Axis SiteDesigner ASDPX -> SiteOwl CSV (backend utility, no UI)."""

from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.adapters.axis_siteowl_adapter import convert_asdpx_to_siteowl_rows, write_siteowl_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert ASDPX to SiteOwl CSV")
    parser.add_argument("source", help="Path to .asdpx file")
    parser.add_argument("-o", "--output", help="Output CSV path", default=None)
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists() or source.suffix.lower() != ".asdpx":
        raise SystemExit(f"Invalid ASDPX source: {source}")

    output = Path(args.output) if args.output else Path("Output") / f"{source.stem}_siteowl.csv"
    rows, meta = convert_asdpx_to_siteowl_rows(source)
    write_siteowl_csv(rows, output)

    print(f"Converted: {source}")
    print(f"Rows: {meta['row_count']}")
    print(f"CSV: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
