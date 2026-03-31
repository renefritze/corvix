FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json /frontend/
RUN npm ci

COPY frontend /frontend
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

ENV UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SETUPTOOLS_SCM_PRETEND_VERSION_FOR_CORVIX=0.0.0 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md LICENSE /app/
COPY src /app/src
COPY config/corvix.example.yaml /app/config/corvix.example.yaml
COPY --from=frontend-builder /src/corvix/web/static/assets /app/src/corvix/web/static/assets

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uvicorn", "corvix.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
