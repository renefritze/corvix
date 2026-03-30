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

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uvicorn", "corvix.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
