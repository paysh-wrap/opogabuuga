# Paytience — common tasks. Run `make help`.
SHELL := /bin/bash
PY := .venv/bin/python
TA_TAG := v0.7.1
TA_COMMIT := 3e44faafa042daf953f6ec2422ae36bb1fd4f50f

.PHONY: server-setup server-up server-update server-logs server-backup server-down help start install tradingagents vibetrading tradingr1 keys create-admin migrate dev web test test-backend test-frontend lint typecheck e2e e2e-live build up down check

help:
	@grep -E '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-16s %s\n", $$1, $$2}'

start: ## One command: install if needed, keys, database, login, build, run + open the browser
	python3 start.py

install: ## Python venv + frontend packages + TradingAgents
	python3 -m venv .venv && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -e "backend[dev]"
	cd frontend && npm ci --no-audit --no-fund
	$(MAKE) tradingagents
	$(MAKE) vibetrading

tradingagents: ## Install TauricResearch/TradingAgents at the pinned tag into its own venv (.venv-ta)
	@if [ ! -d vendor/TradingAgents ]; then git clone -q --depth 1 --branch $(TA_TAG) https://github.com/TauricResearch/TradingAgents.git vendor/TradingAgents; fi
	@test "$$(git -C vendor/TradingAgents rev-parse HEAD)" = "$(TA_COMMIT)" || (echo "TradingAgents commit mismatch — refusing to install"; exit 1)
	python3 -m venv .venv-ta && .venv-ta/bin/pip install -q --upgrade pip && .venv-ta/bin/pip install -q ./vendor/TradingAgents
	.venv-ta/bin/python -c "import tradingagents; print('TradingAgents', tradingagents.__version__)"

vibetrading: ## Install HKUDS/Vibe-Trading (pinned PyPI release) into its own venv (.venv-vt) — D53 second AI opinion
	python3 -m venv .venv-vt && .venv-vt/bin/pip install -q --upgrade pip && .venv-vt/bin/pip install -q "vibe-trading-ai[anthropic]==0.1.19"
	.venv-vt/bin/vibe-trading --version

tradingr1: ## Optional: TauricResearch/Trading-R1 (pinned PyPI, Apache-2.0, ~400 MB) into .venv-tr1 — D94 info-only card
	python3 -m venv .venv-tr1 && .venv-tr1/bin/pip install -q --upgrade pip && .venv-tr1/bin/pip install -q "trading-r1==0.1.1"
	.venv-tr1/bin/trading-r1 --help >/dev/null && echo "Trading-R1 0.1.1 installed (.venv-tr1)"

keys: ## Print a new master key + webhook secret (paste into .env)
	cd backend && ../$(PY) -m app.cli keys

create-admin: ## Create the dashboard login (prompts for password; stored as Argon2 hash only)
	cd backend && ../$(PY) -m app.cli create-admin PayDay

migrate: ## Apply database migrations
	mkdir -p data && cd backend && ../$(PY) -m alembic upgrade head

dev: migrate ## Run API on 127.0.0.1:8000 (also serves the built UI)
	cd backend && ../$(PY) -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000

web: ## Vite dev server on 127.0.0.1:5173 (proxies /api and /ws)
	cd frontend && npm run dev

build: ## Build the UI into frontend/dist
	cd frontend && npm run build

test: test-backend test-frontend ## All unit + integration tests

test-backend: ## Backend tests; risk/management/phases must stay at 100% coverage (§9)
	cd backend && ../$(PY) -m pytest -q --cov=app/risk --cov=app/management --cov=app/phases --cov-report=term-missing:skip-covered --cov-fail-under=100

test-frontend:
	cd frontend && npx vitest run

lint:
	cd backend && ../.venv/bin/ruff check app tests && ../.venv/bin/ruff format --check app tests
	cd frontend && npx eslint src --max-warnings 0

typecheck:
	cd backend && ../.venv/bin/mypy app
	cd frontend && npx tsc -b --noEmit

e2e: build ## §21 browser E2E: real server on a throwaway scratch DB + temp test admin (never data/paytience.db)
	node frontend/e2e/full.mjs

e2e-live: build ## Smoke E2E against an already running server (E2E_PASSWORD=…)
	node frontend/e2e/run.mjs

check: lint typecheck test e2e ## Everything

up: ## Docker: api + worker + redis
	docker compose up -d --build

down:
	docker compose down

# ---------- web server with your own domain (docs/DEPLOY.md) ----------
PROD := docker compose -f docker-compose.prod.yml

server-setup: ## Cloud server first-time setup: Docker, firewall, .env, keys, logins, HTTPS on your domain
	sudo bash deploy/setup.sh

server-up: ## Start / rebuild the web server (Caddy HTTPS + API + worker + Redis)
	$(PROD) up -d --build

server-update: ## Pull the latest code and rebuild (flatten + disarm first; restart recovery covers the rest)
	git pull --ff-only && $(PROD) up -d --build

server-logs: ## Follow the server logs
	$(PROD) logs -f --tail 100

server-backup: ## Back up the database now (also runs daily via cron)
	bash deploy/backup.sh

server-down: ## Stop the web server (data and certificates are kept)
	$(PROD) down
