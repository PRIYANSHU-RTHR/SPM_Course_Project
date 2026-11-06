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

## Step 02 — API skeleton  ·  2026-11-06
**Status:** done
**What I did**
- Set up a `uv` project in `apps/api`, pinned to Python 3.12 (`.python-version`, `requires-python = ">=3.12,<3.13"`). Set `package = false`, so it runs as an app from source with no build backend or `src/` layout.
- Runtime deps: `fastapi`, `uvicorn[standard]`, `pydantic-settings`. Dev deps: `pytest`, `httpx` (needed by FastAPI's `TestClient`), `ruff`. All of these are named in the Step 02 brief.
- `app/config.py`: `Settings` (pydantic-settings) with `DATABASE_URL`, `CORS_ORIGINS` (comma-separated string or list), `LLM_MODE` (`live|record|fixture`, default `fixture`), `GEMINI_MODEL`, `GEMINI_API_KEY` (optional `SecretStr`), `SIM_SEED`. Empty Gemini values count as unset. Reads the repo-root `.env` if it exists. `get_settings()` is cached.
- `app/errors.py`: `DomainError` base (class-level `status_code` + `code`), subclasses `NotFoundError` 404, `ConflictError` 409, `ValidationFailedError` 422, and one `register_exception_handlers(app)`. Body shape: `{"error": {"code", "message", "details"}}`.
- `app/main.py`: `create_app(settings=None)` factory with CORS middleware and the exception handlers. `GET /health` returns `{"status": "ok", "version": "0.1.0"}` and has a typed response model. A module-level `app` is kept for uvicorn.
- Ruff: line length 100, rules `E W F I B UP SIM C4 RUF`. Pytest: `testpaths=tests`, `pythonpath=.`.
- Makefile: `api` runs uvicorn with reload. `test` and `lint` now run the API checks (Step 01 had them echo "added in step 02"). Web checks get added to both in Step 18.
**Files**
- added: `apps/api/pyproject.toml`, `apps/api/uv.lock`, `apps/api/.python-version`, `apps/api/app/__init__.py`, `apps/api/app/config.py`, `apps/api/app/errors.py`, `apps/api/app/main.py`, `apps/api/tests/__init__.py`, `apps/api/tests/test_health.py`
- changed: `Makefile`
**How to verify**
- `cd apps/api && uv sync` → creates `.venv`
- `make lint` → `All checks passed!` / `6 files already formatted`
- `make test` → `5 passed`
- `make api`, then `curl localhost:8000/health` → `{"status":"ok","version":"0.1.0"}`. `/docs` shows the OpenAPI UI.
**Decisions / trade-offs**
- `uv init` created a packaged `src/orchestrai_api` stub. I removed it so the `app/` layout in CLAUDE.md is used as-is.
- Tests build `Settings(_env_file=None)` so a developer's local `.env` can't change test results.
- The CORS origins field uses `NoDecode`, so `CORS_ORIGINS=a,b` works. Without it pydantic-settings expects JSON.
**Notes for later**
- Starlette prints a deprecation warning: "Using `httpx` with `starlette.testclient` is deprecated; install `httpx2`". The tests still pass. Switch the dev dep to `httpx2` in Step 25 (or sooner if it breaks).
- The `DATABASE_URL` default uses `postgresql+psycopg`, so Step 03 should add `psycopg[binary]` to match.
- Step 13 (LLM_MODE=live): the settings should refuse to start when `GEMINI_API_KEY`/`GEMINI_MODEL` are missing. Today they are optional.
**Suggested commit:** `feat(api): fastapi skeleton with settings and health check`
