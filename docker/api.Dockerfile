# Stage 1: UI build
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Stage 2: TauricResearch/TradingAgents (pinned tag + commit check) in its own venv
FROM python:3.11-slim AS ta
RUN apt-get update && apt-get install -y --no-install-recommends git
RUN git clone -q --depth 1 --branch v0.7.1 https://github.com/TauricResearch/TradingAgents.git /src/ta \
 && test "$(git -C /src/ta rev-parse HEAD)" = "3e44faafa042daf953f6ec2422ae36bb1fd4f50f" \
 && python -m venv /opt/ta && /opt/ta/bin/pip install -q /src/ta

# Stage 3: API (+ worker uses the same image)
FROM python:3.11-slim
RUN useradd -m paytience
WORKDIR /app/backend
COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
RUN pip install -q --no-cache-dir .
COPY config /app/config
COPY --from=web /web/dist /app/web
COPY --from=ta /opt/ta /opt/ta
USER paytience
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000"]
