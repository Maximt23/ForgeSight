# 🤝 Contributing to CadOwl

Welcome! CadOwl is built by humans **and** AI coding agents (Code Puppies)
working together. This guide covers both.

---

## Code of Conduct

Be kind. Assume good intent. Critique code, not people. We're solving
hard problems and everyone has bad days. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

---

## Before You Start

1. **Read [docs/ECOSYSTEM.md](docs/ECOSYSTEM.md)** to understand where
   CadOwl fits with MAXILLM and VIVE-SiteOwl-XR.
2. **Read [docs/architecture.md](docs/architecture.md)** for the technical
   model.
3. **Check open issues** to see if your idea is already in flight.
4. **Check [relayops/state/registry.md](../relayops/state/registry.md)**
   to see what other agents are currently working on.

---

## Setup

### Prerequisites
- Python 3.11+
- `uv` package manager (preferred over `pip`)
- Git
- Walmart VPN or Eagle WiFi

### Install
```bash
git clone https://gecgithub01.walmart.com/vn59j7j/CadOwl.git
cd CadOwl
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt \
  --index-url https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple \
  --allow-insecure-host pypi.ci.artifacts.walmart.com
```

### Run the API locally
```bash
python -m uvicorn apps.api.main:app --reload --port 9010
```

### Run tests before opening a PR
```bash
python -m pytest tests/ -q
```

---

## The Golden Rules

These are non-negotiable. Violating them will get your PR rejected.

### 1. No Silent Failures
Every error must be logged, returned, or raised. If a write fails halfway,
the event ledger must record it and the API must return a non-2xx response.

### 2. Every Mutating Endpoint Emits an Event
Before responding to a successful mutation, append an entry to
`data/jsondb/event_ledger.jsonl`. No exceptions.

### 3. Schema-Validate All Writes
JSON Schema in `apps/api/schemas_json/*.api.schema.json` is the source of
truth. Validate inputs **before** touching storage.

### 4. Idempotency for Bulk/Import
Any endpoint that imports or batch-writes must require an
`Idempotency-Key` header and dedupe correctly.

### 5. Soft Delete + Rollback
Destructive operations must be reversible. Add a rollback point before
mutating.

### 6. Adapters Stay Decoupled
External format parsers (DXF, CSV, PDF, SiteOwl) live in `packages/import/`
and convert TO the internal domain model. The domain model never imports
external library types.

### 7. Tests Are Mandatory
- New endpoint → integration test
- New domain rule → unit test
- New parser → fixture-based test
- No PR merges without passing CI

### 8. Never Commit Secrets
- No API keys, tokens, passwords
- No customer PII, HIPAA, PCI data
- No scraped competitor pricing/assortment data
- No internal store videos/photos with identifying info

If you accidentally commit a secret, rotate it immediately and use
`git filter-branch` or BFG to scrub history.

### 9. Never Force-Push to `main`
Use feature branches. PRs only. We roll forward, not back.

### 10. Walmart Policy Compliance
- No competitor scraping (against policy)
- No pen-testing tools
- No tunneling software (Dev-Tunnel banned)
- Use Element AI for any LLM calls
- Host webapps via AI Innovation Lab

---

## Workflow

### Human Workflow
1. **Pick or open an issue** (use the templates)
2. **Branch** off `main`: `git checkout -b feature/short-description`
3. **Code + test**
4. **Run linters**: `ruff check .` and `ruff format .`
5. **Commit** with conventional message (see below)
6. **Push + open PR** with the template filled in
7. **Wait for CI** to pass
8. **Request review** from a CODEOWNER
9. **Merge** (squash merge preferred for feature branches)

### AI Agent (Code Puppy) Workflow
1. **Claim a task** atomically:
   ```python
   from src.core.puppy_coordinator import coordinator
   if not coordinator.claim_task("feature_x", "Description"):
       # someone else owns it, pick another
       return
   ```
2. **Work only inside your scope** — don't touch files outside your task
3. **Auto-commit** as you go:
   ```python
   from src.core.auto_git import commit_changes
   commit_changes("Implemented X")
   ```
4. **Release** the task when done
5. **Drop a coordination message** in `relayops/outbox/` if other puppies
   should know

If you detect a conflict (two puppies modifying the same file), write to
`relayops/state/conflicts.md` and back off.

---

## Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

<optional longer body>

<optional footer with breaking changes / issue refs>
```

Types:
- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation only
- `test` — adding/updating tests
- `refactor` — code change that doesn't add features or fix bugs
- `perf` — performance improvement
- `chore` — tooling, deps, build
- `ci` — CI configuration

Examples:
```
feat(import): add DXF block-pattern matcher for Bosch cameras
fix(api): return 409 instead of 500 on idempotency key collision
docs(integrations): document Grafana switch correlation flow
test(rollback): cover concurrent rollback request race
```

For AI agents, prefix with `[MAXILLM]` or your project tag:
```
[MAXILLM] feat(gis): add building footprint geocoding
```

---

## Pull Request Guidelines

### Size
- **Prefer small PRs.** < 400 lines diff is the sweet spot.
- If you need > 800 lines, split it into a stack of PRs.

### Description
Use the PR template. Required sections:
- **What** — one-paragraph summary
- **Why** — link to issue or business reason
- **How** — key design decisions
- **Testing** — what you ran, what passed
- **Risk** — what could break, how to roll back

### Review
- At least one CODEOWNER approval required
- All CI checks must pass
- Comments resolved before merge

---

## Code Style

### Python
- Format with `ruff format`
- Lint with `ruff check`
- Type hints required on public functions
- Docstrings on modules and public classes (Google style)
- Max line length: 100

### File Size
- Keep files under **600 lines**. Split if growing larger.
- One class per file is fine, multiple is also fine if cohesive.

### Naming
- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- `SCREAMING_SNAKE` for constants
- Test files: `test_<module>.py`

### Imports
- Standard library first
- Third-party second
- Local imports last
- Absolute imports preferred over relative

### Testing
- `pytest` for everything
- `pytest-asyncio` for async code
- Fixtures in `conftest.py`
- Real DB in integration tests, in-memory for unit tests

---

## Documentation

### When to Update Docs
- New endpoint → update `docs/api-spec.md`
- New domain rule → update `docs/architecture.md`
- New integration → update `docs/INTEGRATIONS.md`
- Cross-project change → update `docs/ECOSYSTEM.md`
- Breaking change → update `CHANGELOG.md`

### Diagrams
Use Mermaid or ASCII art (preferred — renders everywhere). PNGs only if
necessary, and check them into `docs/img/`.

---

## Release Process

Phase-based releases. See `ROADMAP.md` for current phase.

When tagging a release:
1. Update `CHANGELOG.md` with all merged PRs since last release
2. Bump version in `apps/api/__init__.py`
3. Tag: `git tag -a v0.x.y -m "Phase X release"`
4. Push tag: `git push origin v0.x.y`
5. Announce in `#mint-support` Slack channel

---

## Reporting Bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml).
Include:
- CadOwl version / commit SHA
- Steps to reproduce
- Expected vs. actual behavior
- Logs (redact secrets!)
- Screenshots if UI-related

---

## Reporting Security Issues

**DO NOT** open a public issue. See [SECURITY.md](SECURITY.md).

---

## Questions?

- 💬 Slack: `#mint-support`
- 📧 Email the repo maintainer (see CODEOWNERS)
- 🐶 Spawn a Code Puppy: [puppy.walmart.com](https://puppy.walmart.com)

---

🐶 *Thanks for contributing. Every commit makes the platform stronger.*
