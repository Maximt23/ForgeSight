# 🔍 Ongoing Audit System

> *"Trust, but verify — automatically."*

A modular reality-check system that runs against the codebase to catch
hallucinations, drift, and the kind of "looks-right-but-isn't" bugs that
slip past code review.

## What It Checks

| Check | Catches |
|-------|---------|
| **imports** | Modules that don't actually load (broken imports, syntax errors, missing deps) |
| **endpoints** | API routes mentioned in docs that don't exist in code, and routes in code never documented |
| **files** | Files exceeding the 600-line CLAUDE.md guideline |
| **tests** | Source modules with no corresponding test file |
| **todos** | TODO / FIXME / XXX / HACK / BUG markers (with severity by type) |
| **deps** | Packages imported but not declared in `requirements.txt`, and vice versa |
| **schemas** | Drift between Pydantic schemas, SQLAlchemy models, and JSON schemas |
| **docs** | Broken markdown links and references to nonexistent files |
| **orphans** | Python modules nobody imports (dead code) |
| **migrations** | Alembic model/migration drift (un-generated migrations) |

## Quick Start

```bash
# Run everything (fails on errors)
python -m scripts.audit

# Just one check
python -m scripts.audit --check endpoints
python -m scripts.audit --check imports,deps

# Generate HTML + JSON reports
python -m scripts.audit --html report.html --json report.json

# Don't fail the shell (CI informational mode)
python -m scripts.audit --no-fail

# Track findings over time
python -m scripts.audit --history audit-history/

# Show only critical issues in console
python -m scripts.audit --min-severity error
```

## Severity Levels

| Level | Fails CI? | Use When |
|-------|-----------|----------|
| `critical` | ✅ Yes | Production-breaking (syntax errors, missing deps) |
| `error` | ✅ Yes | Real bug / drift that must be fixed |
| `warning` | ❌ No | Should fix soon (large files, missing tests) |
| `info` | ❌ No | Informational only (TODOs, possibly unused deps) |

## Suppression Mechanism

When a finding is real but tracked (e.g., "PDF export is planned, ticket
FORGE-202"), add it to `scripts/audit/suppressions.json`:

```json
{
  "endpoints": [
    {
      "endpoint": "/api/v1/exports/pdf",
      "reason": "PLANNED — listed in product roadmap, CSV/XLSX exist today.",
      "ticket": "FORGE-202",
      "expires": "2026-09-01"
    }
  ]
}
```

**Every suppression must have:**
- A `reason` (so future-you knows why)
- A `ticket` (so it's tracked somewhere outside this file)
- An `expires` date (so suppressions can't become permanent lies)

When a suppression expires, the finding is upgraded back to `error` with
a note that the suppression is stale. **This is intentional** — it forces
periodic re-review.

## CI Integration

The audit runs:
1. On every push to `main`
2. On every pull request to `main`
3. Daily at 14:00 UTC (catches drift even without commits)
4. On-demand via "Run workflow" button

PRs get a status comment with the finding counts. The full HTML report
is uploaded as a workflow artifact.

## Architecture

```
scripts/audit/
├── __init__.py
├── __main__.py           # CLI entry point + reporters
├── types.py              # Finding, CheckResult, Severity
├── suppressions.py       # Loader for suppressions.json
├── suppressions.json     # Known-tracked findings
├── html_report.py        # Self-contained HTML report generator
└── checks/
    ├── __init__.py
    ├── endpoints.py
    ├── imports.py
    ├── files.py
    ├── tests.py
    ├── todos.py
    ├── deps.py
    ├── schemas.py
    ├── docs.py
    ├── orphans.py
    └── migrations.py
```

Each check is a single module with a `run() -> CheckResult` function.
**That's the whole interface.** Adding a new check is a 50-line file.

## Adding a New Check

1. Create `scripts/audit/checks/your_check.py`:
   ```python
   from ..types import REPO_ROOT, CheckResult, Finding, Severity
   import time

   def run() -> CheckResult:
       start = time.perf_counter()
       result = CheckResult(check="your_check")
       # ... do stuff, add Finding objects to result.findings ...
       result.duration_ms = (time.perf_counter() - start) * 1000
       return result
   ```

2. Register it in `scripts/audit/__main__.py`:
   ```python
   from .checks import your_check
   _CHECKS["your_check"] = your_check.run
   ```

3. Add suppression key mapping if needed in `suppressions.py`:
   ```python
   key_field = {..., "your_check": "your_id_field"}
   ```

That's it. Run `python -m scripts.audit --check your_check` to verify.

## What Counts as a "Hallucination"

The audit specifically catches these patterns:

1. **Documented but doesn't exist** — e.g. docs say `GET /api/v1/<thing>` for an unbuilt route.
2. **Imports something missing** — `from cadowl.bar import Baz`, no Baz.
3. **Silent try/except hiding failure** — found one of these on day 1!
4. **Schema mismatch** — Pydantic has `User`, DB doesn't, OR they have
   different field types.
5. **Model added, migration missing** — Alembic detects drift.
6. **Reference to a file that was deleted/renamed** — broken doc links.
7. **Code nobody uses** — orphan modules left over from refactors.
8. **Dependency claimed but not used** (or used but not claimed).

## Run History

Every run with `--history audit-history/` writes a timestamped JSON
snapshot. The CLI auto-diffs against the previous snapshot:

```
  📸 Snapshot: audit-history/audit-20260521-163807.json
  ⚠️  +3 new findings vs previous run (audit-20260521-160212.json)
```

This makes regressions visible without setting up a real time-series DB.

## Authored / Owned

Copyright © 2024-2026 Walmart Inc. All rights reserved.
Authored by Maxim Tsitolovsky · Built by Maxim's Puppy 🐶
