# Git Hooks (ForgeSight)

This repo uses tracked hooks via `core.hooksPath=.githooks`.

## post-commit

- Auto-pushes the current branch after commit.
- Non-destructive (`git push` only; no force push).
- Safe skips for detached HEAD and in-progress merge/rebase/cherry-pick.

### Toggle

Disable for one terminal session:

```bash
export FORGESIGHT_AUTOPUSH=0
```

PowerShell:

```powershell
$env:FORGESIGHT_AUTOPUSH = "0"
```
