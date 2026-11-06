COMPOSE := docker compose -f infra/docker-compose.yml

.PHONY: help db-up db-down seed demo api web test lint

help:
	@echo "Targets: db-up db-down seed demo api web test lint"

db-up:
	$(COMPOSE) up -d db

db-down:
	$(COMPOSE) down

seed:
	@echo "seed: added in step 04"

demo:
	@echo "demo: added in step 26"

api:
	@echo "api: added in step 02"

web:
	@echo "web: added in step 18"

test:
	@echo "test: added in step 02"

lint:
	@echo "lint: added in step 02"
