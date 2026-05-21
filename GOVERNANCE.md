# 🏛️ Project Governance

This document describes how decisions get made for CadOwl.

---

## Project Type

CadOwl is an **internal Walmart project** maintained primarily by one
person (the repo owner) with contributions from team members and AI coding
agents. It is **not** an open-source project (today). Decisions are made
faster and less formally than typical OSS projects.

---

## Roles

### Maintainer
- **Who**: Repo owner (see [CODEOWNERS](.github/CODEOWNERS))
- **Responsibilities**:
  - Final say on architecture and major direction
  - Approves PRs to `main`
  - Manages releases and tags
  - Sets priorities and roadmap
  - Liaises with Walmart leadership

### Contributors (Humans)
- **Who**: Walmart employees with repo access
- **Responsibilities**:
  - Open issues and PRs
  - Review each other's work
  - Follow [CONTRIBUTING.md](CONTRIBUTING.md)

### Contributors (AI Agents / Code Puppies)
- **Who**: Code Puppy instances spawned by humans
- **Responsibilities**:
  - Claim and complete scoped tasks
  - Coordinate via `relayops/`
  - Auto-commit using shared tooling
  - Never override human decisions silently
  - Always identify themselves in commit messages with their puppy ID

### Reviewers
- **Who**: Subject-matter experts (security, networking, ML, etc.)
- **Responsibilities**:
  - Review PRs in their domain
  - Block merges that violate architecture rules

---

## Decision Process

### Tactical Decisions
(Small features, bug fixes, refactors)

**Process**: PR → review → merge. Single reviewer is enough.

### Strategic Decisions
(New integrations, schema changes, breaking API changes)

**Process**:
1. Open an issue with an `RFC` label
2. Allow 3 business days for discussion
3. Maintainer makes the call
4. Implementation PR references the issue

### Emergency Decisions
(Production outages, security incidents)

**Process**: Maintainer acts unilaterally. Document the decision after
the fact in `docs/decisions/` (ADR format).

---

## Roadmap Authority

The [ROADMAP.md](ROADMAP.md) is owned by the Maintainer. Priorities can be
proposed by anyone via issue, but the Maintainer decides final order.

Major roadmap shifts (e.g., dropping a phase, adding a new platform) require
sign-off from Walmart leadership.

---

## Code Review Standards

### Required Reviewers
- All PRs to `main`: at least one CODEOWNER approval
- Schema changes: Maintainer + at least one other reviewer
- Integration with new external system: Maintainer + security review

### Review SLA
- First review within **2 business days**
- Subsequent reviews within **1 business day**
- Stale PRs (no activity 7 days): may be closed by Maintainer

### Auto-Merge
- Disabled. Every PR requires explicit human approval.
- Exception: dependabot PRs for patch-level security updates.

---

## Conflict Resolution

### Technical Disagreement
1. Discuss in the PR / issue thread
2. If unresolved, escalate to Maintainer
3. Maintainer decides; reasoning documented

### Inter-Puppy Conflicts
1. Detecting puppy writes to `relayops/state/conflicts.md`
2. Both puppies back off claimed work
3. Human reviews and assigns clear ownership
4. Work resumes

### Code Quality Disputes
- Style: follow the formatter (ruff). No bikeshedding.
- Architecture: defer to docs. If docs are silent, open an RFC.
- Testing: more tests is always acceptable. Less tests requires
  justification.

---

## Release Authority

- **Patch releases** (0.0.X): any CODEOWNER can release
- **Minor releases** (0.X.0): Maintainer approval required
- **Major releases** (X.0.0): Maintainer + Walmart leadership signoff

---

## Adding a New Contributor

### Human
1. Add to Walmart access groups (BQ, internal systems)
2. Add to repo `.github/CODEOWNERS` for their domain
3. Welcome PR with their info added to `docs/contributors.md`
4. Pair on first PR

### AI Agent (New Puppy Persona)
1. Spawn at [puppy.walmart.com/marketplace](https://puppy.walmart.com/marketplace)
2. Configure to claim tasks via `relayops/tasks/`
3. First few PRs reviewed extra carefully
4. Once trusted: same review standards as humans

---

## Deprecation Policy

When deprecating a feature:
1. **Mark as deprecated** in code + docs in version N
2. **Warn at runtime** in version N+1
3. **Remove** in version N+2

Minimum deprecation window: 3 months.

---

## Changing This Document

Governance changes require:
1. Open issue describing the change
2. 7-day comment window
3. Maintainer approval
4. PR to update this file

---

## Forking / Outside Use

CadOwl is internal Walmart code. **Do not** fork to public GitHub or share
outside Walmart without explicit Walmart Legal approval.

Internal forks (within Walmart) are fine, but please coordinate with the
Maintainer so we can share improvements.

---

🐶 *Clear governance = fast decisions = shipped features.*
