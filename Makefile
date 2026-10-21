.PHONY: install dev-api dev-web test lint contracts contracts-check up down

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
