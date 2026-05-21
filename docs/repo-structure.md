# Repository Structure Standard

## Goal
Keep CadOwl organized for parallel enterprise development.

## Source of Truth Layout
- `apps/api` -> HTTP/API contracts and orchestration
- `apps/worker` -> background jobs
- `apps/web` -> UI shell (future)
- `apps/mobile` -> field workflows (future)
- `packages/*` -> domain engines
- `data/jsondb` -> JSON persistence (phase 1)
- `docs/*` -> product and engineering contracts
- `tests/*` -> unit/integration/e2e/load
- `.github/*` -> process automation and governance

## Legacy Transition Rule
Legacy root scripts are allowed temporarily but all new system features must land in structured folders.
