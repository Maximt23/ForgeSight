# Git Hooks (ForgeSight)

This repo uses tracked hooks via `core.hooksPath=.githooks`.

## post-commit

- Auto-pushes the current branch after commit.
- Non-destructive (`git push` only; no force push).
- Safe skips for detached HEAD and in-progress merge/rebase/cherry-pick.

## pre-push

- Runs guarded safety gate via `python -m scripts.safety.prepush_gate`.
- Blocks pushes when:
  - tracked files are dirty
  - merge conflict markers exist
  - branch is behind upstream
  - audit/tests fail

### Toggles

Disable autopush (session):

```bash
export FORGESIGHT_AUTOPUSH=0
```

Disable safety gate (session, emergency only):

```bash
export FORGESIGHT_SAFETY_DISABLE=1
```

Set safety mode:

```bash
export FORGESIGHT_SAFETY_MODE=smoke   # or full
```

PowerShell:

```powershell
$env:FORGESIGHT_AUTOPUSH = "0"
$env:FORGESIGHT_SAFETY_DISABLE = "1"
$env:FORGESIGHT_SAFETY_MODE = "smoke"
```
