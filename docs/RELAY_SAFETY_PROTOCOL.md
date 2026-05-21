# Relay Safety Protocol (System-Wide)

This defines safety controls across coding, handoffs, and push/release.

## 1) Mandatory Gates

Every push runs `.githooks/pre-push` which executes:

- `python -m scripts.safety.prepush_gate --mode ${FORGESIGHT_SAFETY_MODE:-full}`

Blocking conditions:

1. Tracked files dirty
2. Merge conflict markers present
3. Branch behind upstream
4. Audit failure
5. Test failure

## 2) Safety Modes

- `full` (default): full audit + full test suite
- `smoke`: focused audit + focused integration tests

PowerShell examples:

```powershell
$env:FORGESIGHT_SAFETY_MODE = "smoke"
$env:FORGESIGHT_SAFETY_DISABLE = "1"   # emergency use only
```

## 3) Cross-Agent Handoff Contract

Any relay handoff must include:

- Objective + scope
- Files changed
- Commands run and outputs
- Test/audit evidence
- Known risks and rollback commit SHA

No "done" claim without command evidence.

## 4) Severity Matrix

- **SEV-1**: Data corruption/security risk/prod outage
  - Stop pushes, freeze merges, rollback immediately.
- **SEV-2**: Feature broken, no data loss
  - Patch branch + hotfix in same day.
- **SEV-3**: UI inconsistency/regression
  - Queue in next sprint, unless customer-visible.
- **SEV-4**: Cosmetic/docs-only
  - Batch with routine maintenance.

## 5) Rollback Protocol

1. Identify bad SHA (`git log --oneline`)
2. Create rollback branch from `main`
3. Revert targeted commit(s): `git revert <sha>`
4. Run audit + tests
5. Push + open PR with incident notes

## 6) Design Safety Rule

All UI changes must reference `docs/design-research/*` baseline before merge.
