.PHONY: install dev-api dev-web test lint contracts contracts-check up down \
	prod-up prod-down prod-logs backup notices

PROD = docker compose -f docker-compose.yml -f docker-compose.prod.yml

install:
	cd backend && uv sync
	cd frontend && npm ci

dev-api:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

dev-web:
	cd frontend && npm run dev

test:
	cd backend && uv run pytest -q

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npm run typecheck

# Regenerate OpenAPI, JSON Schemas and frontend types from the Pydantic models
contracts:
	cd backend && uv run python -m scripts.export_contracts
	cd frontend && npm run gen:api

contracts-check:
	cd backend && uv run python -m scripts.export_contracts --check

up:
	docker compose up --build -d

down:
	docker compose down

# Public stand behind Caddy with HTTPS, see docs/deploy.md
prod-up:
	$(PROD) up --build -d

prod-down:
	$(PROD) down

prod-logs:
	$(PROD) logs -f --tail=100

# Compressed SQL dump of the whole database into backups/
backup:
	mkdir -p backups
	$(PROD) exec -T db sh -c 'pg_dump -U "$$POSTGRES_USER" "$$POSTGRES_DB"' \
		| gzip > backups/alfa_news_$$(date +%Y%m%d_%H%M%S).sql.gz
	ls -lh backups | tail -3

# Regenerate THIRD_PARTY_NOTICES.md from the lock files, the manual section is kept
notices:
	uv run --project backend python scripts/third_party_notices.py
