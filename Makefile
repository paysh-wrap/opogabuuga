# Paytience — common tasks. Run `make help`.
SHELL := /bin/bash
PY := .venv/bin/python
TA_TAG := v0.7.1
TA_COMMIT := 3e44faafa042daf953f6ec2422ae36bb1fd4f50f

.PHONY: help install tradingagents keys create-admin migrate dev web test test-backend test-frontend lint typecheck e2e build up down check

help:
	@grep -E '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-16s %s\n", $$1, $$2}'

install: ## Python venv + frontend packages + TradingAgents
	python3 -m venv .venv && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -e "backend[dev]"
	cd frontend && npm ci --no-audit --no-fund
	$(MAKE) tradingagents

tradingagents: ## Install TauricResearch/TradingAgents at the pinned tag into its own venv (.venv-ta)
	@if [ ! -d vendor/TradingAgents ]; then git clone -q --depth 1 --branch $(TA_TAG) https://github.com/TauricResearch/TradingAgents.git vendor/TradingAgents; fi
	@test "$$(git -C vendor/TradingAgents rev-parse HEAD)" = "$(TA_COMMIT)" || (echo "TradingAgents commit mismatch — refusing to install"; exit 1)
	python3 -m venv .venv-ta && .venv-ta/bin/pip install -q --upgrade pip && .venv-ta/bin/pip install -q ./vendor/TradingAgents
	.venv-ta/bin/python -c "import tradingagents; print('TradingAgents', tradingagents.__version__)"

keys: ## Print a new master key + webhook secret (paste into .env)
	cd backend && ../$(PY) -m app.cli keys

create-admin: ## Create the dashboard login (prompts for password; stored as Argon2 hash only)
	cd backend && ../$(PY) -m app.cli create-admin admin

migrate: ## Apply database migrations
	mkdir -p data && cd backend && ../$(PY) -m alembic upgrade head

dev: migrate ## Run API on 127.0.0.1:8000 (also serves the built UI)
	cd backend && ../$(PY) -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000

web: ## Vite dev server on 127.0.0.1:5173 (proxies /api and /ws)
	cd frontend && npm run dev

build: ## Build the UI into frontend/dist
	cd frontend && npm run build

test: test-backend test-frontend ## All unit + integration tests

test-backend:
	cd backend && ../$(PY) -m pytest -q

test-frontend:
	cd frontend && npx vitest run

lint:
	cd backend && ../.venv/bin/ruff check app tests && ../.venv/bin/ruff format --check app tests
	cd frontend && npx eslint src --max-warnings 0

typecheck:
	cd backend && ../.venv/bin/mypy app
	cd frontend && npx tsc -b --noEmit

e2e: build ## Browser tests against a real running server
	node frontend/e2e/run.mjs

check: lint typecheck test e2e ## Everything

up: ## Docker: api + worker + redis
	docker compose up -d --build

down:
	docker compose down
