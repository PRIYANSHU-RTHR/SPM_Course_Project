# OrchestrAI — Build Log

This is the running build log for OrchestrAI. Each step from `PLAN.md` §5 adds one entry at the bottom when it is finished: what was done, which files changed, how to verify, decisions made, and notes for later steps. It is append-only. Do not rewrite or delete earlier entries. To find the next step, read the last entry and take the next step number from `PLAN.md`.

## Entry template

```markdown
## Step NN — <title>  ·  <YYYY-MM-DD>
**Status:** done | partial (why)
**What I did**
- …
**Files**
- added: …
- changed: …
**How to verify**
- `command` → expected result
**Decisions / trade-offs**
- …
**Notes for later**
- …
**Suggested commit:** `type(scope): message`
```

---

## Step 01 — Repo scaffold  ·  2026-11-06
**Status:** done
**What I did**
- Created the monorepo layout from PLAN.md §3 (`apps/web`, `apps/api/app/{engines,agents,workflows}`, `infra`, `docs`). Empty folders are kept with `.gitkeep`.
- Replaced the README stub with the project name, one-line pitch, team and links to PLAN.md and the build log.
- Added `.gitignore` (Python, Node, env files, IDE/OS), `.editorconfig`, and `.env.example` with every variable from CLAUDE.md "Environment" plus the `POSTGRES_*` variables used by compose.
- Added a `Makefile` with targets `db-up`, `db-down` (working), plus `seed`, `demo`, `api`, `web`, `test`, `lint` (each echoes the step that implements it).
- Added `infra/docker-compose.yml` with one `db` service: `postgres:16-alpine`, named volume `db-data`, `pg_isready` healthcheck, port from `POSTGRES_PORT` (default 5432), credentials from env with defaults `orchestrai/orchestrai/orchestrai`.
**Files**
- added: `.gitignore`, `.editorconfig`, `.env.example`, `Makefile`, `infra/docker-compose.yml`, `apps/web/.gitkeep`, `apps/api/app/{engines,agents,workflows}/.gitkeep`, `docs/temp.md`
- changed: `README.md`
**How to verify**
- `docker compose -f infra/docker-compose.yml up -d db` → container `orchestrai-db-1` becomes `(healthy)` in `docker compose -f infra/docker-compose.yml ps`
- `docker compose -f infra/docker-compose.yml exec -T db psql -U orchestrai -d orchestrai -tc 'select version();'` → `PostgreSQL 16.x`
- `docker compose -f infra/docker-compose.yml down` → stops it (the volume is kept)
- `make seed` → `seed: added in step 04`
**Decisions / trade-offs**
- Host port 5432 was already taken on this machine by another project's container (`go-ride-db`). Verification ran with `POSTGRES_PORT=5433`. The container started and became healthy (PostgreSQL 16.15), then was stopped. The default stays 5432. Anyone with a clash should export `POSTGRES_PORT` and match `DATABASE_URL`.
- Used `postgres:16-alpine` because the image is smaller. Same major version as required.
- `DATABASE_URL` in `.env.example` uses the `postgresql+psycopg` driver. Step 02/03 should confirm this driver choice.
- Compose looks for `.env` next to the compose file (`infra/`), not at the repo root, so a root `.env` is not read by plain `docker compose -f infra/...`. The defaults cover the demo.
**Notes for later**
- Step 02/26: decide whether Makefile `db-up` should pass `--env-file .env` (only when it exists) so root `.env` overrides apply to compose.
- Step 13: PLAN.md puts fixtures in `apps/api/fixtures/llm/`, but CLAUDE.md layout puts them in `apps/api/app/fixtures/llm/`. Pick one.
- Remaining folders from the CLAUDE.md layout (`models/`, `schemas/`, `routers/`, `services/`, `tests/`, web `src/` tree) get created in the steps that fill them.
**Suggested commit:** `chore: scaffold monorepo and postgres compose`
