COMPOSE := docker compose -f infra/docker-compose.yml
API_DIR := apps/api

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
	@echo "web: added in step 18"

test:  ## api tests (web tests join in step 18)
	cd $(API_DIR) && uv run pytest -q

lint:  ## api lint (web lint joins in step 18)
	cd $(API_DIR) && uv run ruff check . && uv run ruff format --check .
