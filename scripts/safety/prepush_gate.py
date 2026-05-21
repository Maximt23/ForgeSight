from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc


def _print_step(msg: str) -> None:
    print(f"[safety] {msg}")


def check_clean_tree() -> None:
    _print_step("checking working tree cleanliness")
    proc = _run(["git", "status", "--porcelain"], check=False)
    dirty_lines = [line for line in proc.stdout.splitlines() if line and not line.startswith("??")]
    if dirty_lines:
        raise RuntimeError("Tracked files are dirty. Commit or stash before pushing.\n" + "\n".join(dirty_lines[:20]))


def check_conflict_markers() -> None:
    _print_step("scanning for unresolved merge markers")
    proc= _run(
        ["git", "grep", "-n", "-E", r"^(<<<<<<< |>>>>>>>)", "--", "."],
        check=False,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr or proc.stdout)
    if proc.returncode == 0 and proc.stdout.strip():
        raise RuntimeError("Unresolved merge markers found:\n" + proc.stdout)


def check_upstream_sync() -> None:
    _print_step("checking upstream divergence")
    upstream = _run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], check=False)
    if upstream.returncode != 0:
        _print_step("no upstream configured; skipping divergence gate")
        return

    counts = _run(["git", "rev-list", "--left-right", "--count", "@{u}...HEAD"], check=True)
    left_right = counts.stdout.strip().split()
    if len(left_right) != 2:
        return
    behind, ahead = int(left_right[0]), int(left_right[1])
    if behind > 0:
        raise RuntimeError(
            f"Branch is behind upstream by {behind} commit(s). Pull/rebase first to avoid unsafe overwrite."
        )
    _print_step(f"upstream ok (ahead={ahead}, behind={behind})")


def run_audit(mode: str) -> None:
    _print_step(f"running audit ({mode})")
    if mode == "smoke":
        _run(["python", "-m", "scripts.audit", "--check", "files,endpoints,schemas", "--quiet"])
    else:
        _run(["python", "-m", "scripts.audit", "--quiet"])


def run_tests(mode: str) -> None:
    _print_step(f"running tests ({mode})")
    if mode == "smoke":
        _run(
            [
                "pytest",
                "-q",
                "tests/integration/test_validation_routes.py",
                "tests/integration/test_design_lab_page.py",
            ]
        )
    else:
        _run(["pytest", "-q"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ForgeSight pre-push safety gate")
    parser.add_argument("--mode", choices=("full", "smoke"), default=os.getenv("FORGESIGHT_SAFETY_MODE", "full"))
    parser.add_argument("--skip-audit", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        check_clean_tree()
        check_conflict_markers()
        check_upstream_sync()

        if not args.skip_audit:
            run_audit(args.mode)
        if not args.skip_tests:
            run_tests(args.mode)

        _print_step("all safety checks passed")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[safety] BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
