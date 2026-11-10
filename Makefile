# Compose reads the repo-root .env when there is one (a fresh clone has none: defaults apply).
COMPOSE ?= docker compose $(if $(wildcard .env),--env-file .env) -f infra/docker-compose.yml
API_DIR := apps/api
WEB_DIR := apps/web
# Host ports for the demo: command line / shell, else .env, else these defaults.
API_PORT ?= $(or $(shell sed -n 's/^API_PORT=//p' .env 2>/dev/null),8000)
WEB_PORT ?= $(or $(shell sed -n 's/^WEB_PORT=//p' .env 2>/dev/null),8080)
# Model for record-fixtures when GEMINI_MODEL is unset (same default as .env.example).
GEMINI_MODEL_DEFAULT := gemini-3.8-flash

.PHONY: help db-up db-down migrate seed demo demo-down record-fixtures api web test cov lint evaluate

help:
	@echo "Targets: db-up db-down migrate seed demo demo-down record-fixtures api web test cov lint evaluate"

db-up:
	$(COMPOSE) up -d db

db-down:
	$(COMPOSE) down

migrate:
	cd $(API_DIR) && uv run alembic upgrade head

seed: migrate  ## wipes the database in DATABASE_URL and recreates the demo data
	cd $(API_DIR) && uv run python -m app.seed

demo:  ## whole stack in Docker, fixture LLM (no API key), fresh demo data; prints the URLs
	LLM_MODE=fixture API_PORT=$(API_PORT) WEB_PORT=$(WEB_PORT) $(COMPOSE) up --detach --build --wait
	$(COMPOSE) exec -T api alembic upgrade head
	$(COMPOSE) exec -T api python -m app.seed
	@echo ""
	@echo "OrchestrAI is running (LLM_MODE=fixture):"
	@echo "  web       http://localhost:$(WEB_PORT)"
	@echo "  api       http://localhost:$(API_PORT)"
	@echo "  api docs  http://localhost:$(API_PORT)/docs"
	@echo "Stop with: make demo-down"

demo-down:  ## stop the demo stack (keeps the database volume)
	$(COMPOSE) down

# Needs GEMINI_API_KEY in the shell or in the repo-root .env. Seeds the demo team (the prompt
# includes its skill vocabulary), runs the demo brief through the planning workflow with
# LLM_MODE=record and writes apps/api/fixtures/llm/*.json; commit those files.
record-fixtures: export GEMINI_API_KEY ?= $(shell sed -n 's/^GEMINI_API_KEY=//p' .env 2>/dev/null)
record-fixtures: export GEMINI_MODEL ?= $(or $(shell sed -n 's/^GEMINI_MODEL=//p' .env 2>/dev/null),$(GEMINI_MODEL_DEFAULT))
record-fixtures:
	@test -n "$$GEMINI_API_KEY" || { echo "GEMINI_API_KEY is not set (shell or .env); recording needs a live model" >&2; exit 1; }
	LLM_MODE=fixture API_PORT=$(API_PORT) $(COMPOSE) up --detach --build --wait db api
	$(COMPOSE) exec -T api python -m app.seed
	$(COMPOSE) run --rm --no-deps --user "$$(id -u):$$(id -g)" \
		-e LLM_MODE=record -e GEMINI_API_KEY -e GEMINI_MODEL \
		-v "$(CURDIR)/apps/api/fixtures:/srv/orchestrai/api/fixtures" \
		api python -m scripts.record_fixtures
	@git status --short apps/api/fixtures

api:
	cd $(API_DIR) && uv run uvicorn app.main:app --reload

web:
	cd $(WEB_DIR) && pnpm dev

test:  ## api and web tests
	cd $(API_DIR) && uv run pytest -q
	cd $(WEB_DIR) && pnpm test

cov:  ## api tests with coverage; fails if engines/ is under 80% (same check as CI)
	cd $(API_DIR) && uv run pytest -q --cov --cov-report=term
	cd $(API_DIR) && uv run coverage report --include='app/engines/*' --fail-under=80

lint:  ## api lint, web type-check and lint
	cd $(API_DIR) && uv run ruff check . && uv run ruff format --check .
	cd $(WEB_DIR) && pnpm typecheck && pnpm lint

evaluate:  ## assignment strategy comparison -> docs/evaluation.md (no database needed)
	cd $(API_DIR) && uv run python -m scripts.evaluate
