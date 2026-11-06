COMPOSE := docker compose -f infra/docker-compose.yml
API_DIR := apps/api
WEB_DIR := apps/web

.PHONY: help db-up db-down migrate seed demo api web test lint

help:
	@echo "Targets: db-up db-down migrate seed demo api web test lint"

db-up:
	$(COMPOSE) up -d db

db-down:
	$(COMPOSE) down

migrate:
	cd $(API_DIR) && uv run alembic upgrade head

seed: migrate  ## wipes the database in DATABASE_URL and recreates the demo data
	cd $(API_DIR) && uv run python -m app.seed

demo:
	@echo "demo: added in step 26"

api:
	cd $(API_DIR) && uv run uvicorn app.main:app --reload

web:
	cd $(WEB_DIR) && pnpm dev

test:  ## api and web tests
	cd $(API_DIR) && uv run pytest -q
	cd $(WEB_DIR) && pnpm test

lint:  ## api lint, web type-check and lint
	cd $(API_DIR) && uv run ruff check . && uv run ruff format --check .
	cd $(WEB_DIR) && pnpm typecheck && pnpm lint
