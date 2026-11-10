# syntax=docker/dockerfile:1
# OrchestrAI API: FastAPI + engines + LangGraph. Multi-stage: uv builds the venv, the runtime
# stage copies it and runs as a non-root user. On start: alembic upgrade head, then uvicorn.

# The app lives at /srv/orchestrai/api (the record-fixtures bind mount uses this path). There
# is no repo-root .env in the image; settings come from the environment.
ARG APP_DIR=/srv/orchestrai/api

FROM ghcr.io/astral-sh/uv:0.12.15 AS uv

FROM python:3.12-slim AS build
ARG APP_DIR
COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=${APP_DIR}/.venv
WORKDIR ${APP_DIR}
# Dependencies first, so code changes don't reinstall them.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project
COPY alembic.ini ./
COPY migrations ./migrations
COPY fixtures ./fixtures
COPY scripts ./scripts
COPY app ./app

FROM python:3.12-slim AS runtime
ARG APP_DIR
RUN groupadd --system --gid 10001 orchestrai \
    && useradd --system --uid 10001 --gid orchestrai --home-dir ${APP_DIR} --no-create-home orchestrai
WORKDIR ${APP_DIR}
COPY --from=build --chown=orchestrai:orchestrai ${APP_DIR} ${APP_DIR}
ENV PATH="${APP_DIR}/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LLM_MODE=fixture
USER orchestrai
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --start-period=20s --retries=12 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
