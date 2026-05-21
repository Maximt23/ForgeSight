"""
CLI runner for the audit system.

Usage:
    python -m scripts.audit                          # run all checks, print summary
    python -m scripts.audit --html report.html       # also write HTML report
    python -m scripts.audit --json out.json          # also write JSON report
    python -m scripts.audit --check endpoints,docs   # subset of checks
    python -m scripts.audit --no-fail                # always exit 0 (informational mode)
    python -m scripts.audit --history audit-history/ # save snapshot for regression tracking

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Windows console can't handle most emoji — force UTF-8 if possible
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

from .checks import deps, docs, endpoints, files, imports, migrations, orphans, schemas, tests, todos
from .html_report import render as render_html
from .types import REPO_ROOT, CheckResult, Severity

# All available checks
_CHECKS = {
    "imports": imports.run,
    "endpoints": endpoints.run,
    "files": files.run,
    "tests": tests.run,
    "todos": todos.run,
    "deps": deps.run,
    "schemas": schemas.run,
    "docs": docs.run,
    "orphans": orphans.run,
    "migrations": migrations.run,
}


# ─── ANSI for console output ─────────────────────────────────────────


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    GRAY = "\033[90m"


# Emoji-safe glyphs for cross-platform console
if os.name == "nt":
    _OK = "[OK]"
    _FAIL = "[FAIL]"
    _DOG = "[*]"
    _LIST = "[+]"
    _DOC = "[doc]"
    _SNAP = "[snap]"
    _UP = "[+]"
    _DOWN = "[-]"
    _EQ = "[=]"
else:
    _OK = "✅"
    _FAIL = "❌"
    _DOG = "🐶"
    _LIST = "📋"
    _DOC = "📄"
    _SNAP = "📸"
    _UP = "⚠️"
    _DOWN = "✨"
    _EQ = "➡️"


def _supports_color() -> bool:
    return sys.stdout.isatty() and os.name != "nt"  # Windows cmd is unpredictable


def _color(text: str, code: str) -> str:
    return f"{code}{text}{C.RESET}" if _supports_color() else text


# ─── Console reporter ───────────────────────────────────────


def print_console_report(results: list[CheckResult]) -> None:
    """Print a tight human-readable summary."""
    print()
    print(_color("=" * 80, C.BLUE))
    print(_color(f"{_DOG} CadOwl / ForgeSight Audit Report", C.BOLD))
    print(_color(f"   Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", C.GRAY))
    print(_color("=" * 80, C.BLUE))
    print()

    total_errors = total_warnings = total_info = 0
    total_critical = 0
    for r in results:
        status_icon = _OK if r.passed else _FAIL
        status_color = C.GREEN if r.passed else C.RED

        critical = sum(1 for f in r.findings if f.severity == Severity.CRITICAL)
        errors = sum(1 for f in r.findings if f.severity == Severity.ERROR)
        warnings = sum(1 for f in r.findings if f.severity == Severity.WARNING)
        info = sum(1 for f in r.findings if f.severity == Severity.INFO)

        total_critical += critical
        total_errors += errors
        total_warnings += warnings
        total_info += info

        line = (
            f"  {status_icon} {_color(r.check.ljust(14), C.BOLD)} "
            f"{_color(str(r.items_scanned).rjust(6), C.GRAY)} items "
            f"{_color(str(int(r.duration_ms)).rjust(5), C.GRAY)}ms "
        )
        if critical:
            line += _color(f"  {critical} critical", C.RED)
        if errors:
            line += _color(f"  {errors} errors", C.RED)
        if warnings:
            line += _color(f"  {warnings} warn", C.YELLOW)
        if info:
            line += _color(f"  {info} info", C.GRAY)
        if r.error:
            line += _color(f"  CHECK CRASHED: {r.error}", C.RED)

        print(line)

    print()
    print(_color("-" * 80, C.GRAY))
    overall = total_errors + total_critical == 0
    status = (
        _color(f"{_OK} ALL CHECKS PASSED", C.GREEN + C.BOLD)
        if overall
        else _color(f"{_FAIL} AUDIT FAILED — {total_critical + total_errors} blocking issue(s)", C.RED + C.BOLD)
    )
    print(f"  {status}")
    print(_color(f"  Totals: {total_critical} critical · {total_errors} errors · {total_warnings} warnings · {total_info} info", C.GRAY))
    print()


def print_findings_detail(results: list[CheckResult], min_severity: Severity = Severity.WARNING) -> None:
    """Print detailed findings at or above min_severity."""
    severity_order = [Severity.CRITICAL, Severity.ERROR, Severity.WARNING, Severity.INFO]
    cutoff = severity_order.index(min_severity)

    for r in results:
        relevant = [
            f for f in r.findings if severity_order.index(f.severity) <= cutoff
        ]
        if not relevant:
            continue

        print()
        print(_color(f"  {_LIST} {r.check.upper()}", C.BOLD + C.BLUE))
        print(_color(f"  {'-' * 76}", C.GRAY))

        for f in relevant:
            sev_color = {
                Severity.CRITICAL: C.RED + C.BOLD,
                Severity.ERROR: C.RED,
                Severity.WARNING: C.YELLOW,
                Severity.INFO: C.GRAY,
            }[f.severity]
            print(f"    {_color(f.severity.value.upper().rjust(8), sev_color)}  {f.title}")
            if f.file:
                loc = f.file + (f":{f.line}" if f.line else "")
                print(f"             {_color(loc, C.GRAY)}")
            if f.suggestion:
                print(f"             {_color('→ ' + f.suggestion, C.GRAY)}")


# ─── History tracking ────────────────────────────────────────────────


def save_history(results: list[CheckResult], history_dir: Path) -> Path:
    """Snapshot current results with a timestamp for regression tracking."""
    history_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    snapshot = history_dir / f"audit-{timestamp}.json"

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": [r.to_dict() for r in results],
        "summary": {
            "total_checks": len(results),
            "total_findings": sum(len(r.findings) for r in results),
            "all_passed": all(r.passed for r in results),
        },
    }
    snapshot.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return snapshot


def compare_to_previous(current: list[CheckResult], history_dir: Path) -> str | None:
    """Compare current run to most recent snapshot. Returns diff summary."""
    if not history_dir.exists():
        return None
    snapshots = sorted(history_dir.glob("audit-*.json"))
    if len(snapshots) < 2:  # we just saved one
        return None

    previous = snapshots[-2]  # -1 is the one we just saved
    try:
        prev_data = json.loads(previous.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    prev_findings = prev_data["summary"]["total_findings"]
    curr_findings = sum(len(r.findings) for r in current)
    delta = curr_findings - prev_findings

    if delta > 0:
        return f"{_UP}  +{delta} new findings vs previous run ({previous.name})"
    elif delta < 0:
        return f"{_DOWN} {-delta} fewer findings vs previous run ({previous.name})"
    else:
        return f"{_EQ}  No change vs previous run ({previous.name})"


# ─── Main ────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="scripts.audit", description="CadOwl ongoing audit")
    p.add_argument("--check", help="Comma-separated check names (default: all)")
    p.add_argument("--html", type=Path, help="Write HTML report to this path")
    p.add_argument("--json", type=Path, help="Write JSON report to this path")
    p.add_argument("--history", type=Path, help="Snapshot results to this directory")
    p.add_argument("--no-fail", action="store_true", help="Always exit 0")
    p.add_argument("--quiet", action="store_true", help="Suppress detailed findings")
    p.add_argument("--min-severity", choices=[s.value for s in Severity], default="warning",
                   help="Show findings at or above this severity in detail (default: warning)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # Ensure repo root on sys.path
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    # Select checks
    if args.check:
        selected = {name: _CHECKS[name] for name in args.check.split(",") if name in _CHECKS}
        if not selected:
            print(f"No valid checks selected. Available: {', '.join(_CHECKS)}")
            return 2
    else:
        selected = _CHECKS

    # Run them all (sequential — most are fast; parallel would obscure ordering)
    results: list[CheckResult] = []
    overall_start = time.perf_counter()
    for name, runner in selected.items():
        try:
            r = runner()
        except Exception as exc:  # noqa: BLE001
            r = CheckResult(check=name, error=f"{type(exc).__name__}: {exc}")
        results.append(r)

    total_duration_ms = (time.perf_counter() - overall_start) * 1000

    # Console output
    print_console_report(results)
    if not args.quiet:
        print_findings_detail(results, Severity(args.min_severity))
        print()
    print(_color(f"  Total runtime: {total_duration_ms:.0f}ms", C.GRAY))
    print()

    # HTML report
    if args.html:
        render_html(results, args.html)
        print(_color(f"  {_DOC} HTML report: {args.html}", C.BLUE))

    # JSON report
    if args.json:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_duration_ms": total_duration_ms,
            "results": [r.to_dict() for r in results],
        }
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(_color(f"  {_DOC} JSON report: {args.json}", C.BLUE))

    # History snapshot
    if args.history:
        snapshot = save_history(results, args.history)
        print(_color(f"  {_SNAP} Snapshot: {snapshot}", C.BLUE))
        diff = compare_to_previous(results, args.history)
        if diff:
            print(_color(f"  {diff}", C.YELLOW))

    print()

    # Exit code
    if args.no_fail:
        return 0
    blocking = sum(
        1 for r in results
        for f in r.findings
        if f.severity in (Severity.ERROR, Severity.CRITICAL)
    ) + sum(1 for r in results if r.error)
    return 0 if blocking == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
