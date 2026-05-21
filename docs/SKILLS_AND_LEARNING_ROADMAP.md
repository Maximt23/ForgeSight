# CadOwl Skills & Learning Roadmap

> Purpose: make capability growth auditable, governed, and repeatable.

## 1) Governance Objectives

- Build a clear record of what skills exist.
- Track what is still in development.
- Define control checks for every major capability.
- Capture evidence for audit and compliance reviews.
- Tie learning outcomes to delivery quality.

## 2) Skill Catalog (Current State)

### 2.1 CAD Pipeline Operations

Status: **Implemented**

- DWG -> DXF -> CSV workflow orchestration
- Staging-folder based conversion design
- ODA converter path discovery + error handling
- System-specific folder routing (FA/CCTV)

Audit evidence:
- `dwg_converter.py`
- `Process-FA.bat`, `Process-CCTV.bat`
- Runtime console output with conversion counts

Control checks:
- Input/output folders are never identical for ODA.
- Missing converter returns actionable guidance.
- No DXF in staging returns explicit error.

---

### 2.2 Device Extraction & Classification

Status: **Implemented**

- Regex-based layer/block pattern detection
- Exclusion list for non-device blocks
- Store number extraction from filename

Audit evidence:
- `cad2siteowl.py`
- `cad2siteowl_enhanced.py`

Control checks:
- Pattern sets are versioned in source.
- Exclusion patterns prevent false positives.
- Extraction path returns deterministic mode labels.

---

### 2.3 Matching Intelligence (CAD <-> Excel)

Status: **Implemented and tuning**

- Multi-factor scoring:
  - system-type signal
  - keyword overlap
  - name similarity
  - numeric/abbreviation hints
- Matched/unmatched counters per file

Audit evidence:
- `enhanced_matching.py`
- CSV output rows with `[UNMATCHED]` descriptors

Control checks:
- Thresholded match acceptance (> minimum score)
- Single-use match locking on Excel rows
- Summary prints include matched/unmatched totals

---

### 2.4 Boundary & Coordinate Normalization

Status: **Implemented**

- Candidate boundaries from:
  - closed polylines
  - DXF header extents
  - device-derived bounding boxes
- Coverage/area scoring for candidate selection
- SiteOwl coordinate transform normalization

Audit evidence:
- `enhanced_boundary.py`
- Runtime logs: boundary source, size, coverage

Control checks:
- Invalid/NaN/Inf extents are rejected.
- Low coverage triggers safe fallback.
- Out-of-range coordinate counts are reported.

---

### 2.5 Memory Library & Pattern Learning

Status: **Implemented and expanding**

- Persistent SQLite memory graph of CAD patterns
- Tree edges include:
  - SYSTEM -> DEPT -> AISLE -> LAYER -> BLOCK -> TAG
- Recommendation generation per target system
- Optional DWG conversion before deep training

Audit evidence:
- `build_memory_library.py`
- `cadowl_memory/library.py`
- `cadowl_memory/recommendations.py`
- JSON report output (`--json-out`)

Control checks:
- File ingest status tracked (`ingested`, `pending_dxf`, etc.)
- Edge weights and timestamps are persisted.
- Department map fallback defaults are enforced.

---

### 2.6 Layout Fallback Heuristics (WMRT/SPAC)

Status: **Implemented and tuning**

- Fallback candidate extraction when no primary matches
- Optional runtime disable (`--no-layout-fallback`)

Audit evidence:
- `cad2siteowl_enhanced.py` fallback mode paths
- Runtime extraction mode labels (`pattern-match`, `layout-fallback`)

Control checks:
- Fallback only executes when primary returns none.
- Exclusion patterns still apply to fallback path.
- Operator can disable fallback during validation.

---

### 2.7 Name Variance Learning

Status: **In development / active research**

- Learns naming transformations and token aliases
- Measures similarity and overlap distributions
- Produces pair datasets for review

Audit evidence:
- `learn_name_variance.py`
- Generated JSON/CSV pair outputs

Control checks:
- Minimum confidence thresholds are configurable.
- Match metadata is retained for traceability.
- Cross-system source labels are stored.

---

### 2.8 Engineering Process Skills

Status: **Implemented**

- Modularization of large scripts into focused modules
- Atomic git commits by capability slice
- Runtime smoke checks + compile checks

Audit evidence:
- `enhanced_models.py`, `enhanced_matching.py`, `enhanced_boundary.py`
- Git history showing capability-scoped commits

Control checks:
- Keep files cohesive and maintainable.
- Require passing compile and CLI help checks.
- Keep behavioral changes documented in commits.

## 3) Learning Lessons Captured

1. **Separation beats shortcuts**
   - Conversion, extraction, matching, and reporting should stay decoupled.

2. **Fallbacks are a feature, not a failure**
   - Real CAD data is inconsistent; controlled fallback keeps flow resilient.

3. **Memory improves precision over time**
   - Learned patterns reduce dependence on static regex-only detection.

4. **Auditability must be built-in**
   - Status labels, counters, and logs are as important as output files.

5. **Small commits reduce risk**
   - Capability-based commits improve rollback and review quality.

## 4) Audit Controls Matrix

### 4.1 Operational Controls

- C1: Conversion folder separation enforced
- C2: Empty staging detection with actionable message
- C3: Explicit mode labeling for extraction path
- C4: Boundary confidence and fallback logging
- C5: Match confidence thresholding and counters

### 4.2 Data Quality Controls

- D1: Excluded block filters always applied
- D2: Out-of-range coordinate counts reported
- D3: Unmatched rows retain source CAD context
- D4: Memory edge weights are persistent and queryable

### 4.3 Governance Controls

- G1: Capability changes land in atomic commits
- G2: New skill behavior must have runtime evidence
- G3: README/docs updated for operator-facing changes
- G4: Feature flags available for risk-managed rollout

## 5) Evidence Collection Standard

For each release or major training run, collect:

- Git commit IDs for capability changes
- Command lines executed
- Console summaries (matched/unmatched, boundary info)
- Training summaries (top edges, recommendations)
- Generated report artifacts (CSV/JSON)

Recommended artifact bundle folder name:

`audit/<YYYY-MM-DD>_<scope>/`

## 6) Cadence & Ownership

- Weekly: skill status review and metric check
- Bi-weekly: threshold tuning review
- Monthly: governance and controls retrospective

Suggested owners:
- Pipeline reliability owner
- Matching quality owner
- Memory learning owner
- Audit/governance owner

## 7) Next Governance Upgrades

- Add structured run manifest for each batch execution.
- Add automated regression sample pack for known stores.
- Add confidence dashboards for match and fallback rates.
- Add signed release checklist for production runs.

---

Created for governance-first delivery: build trust, then scale.
