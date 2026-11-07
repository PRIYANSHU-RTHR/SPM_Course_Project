"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from pydantic import BaseModel

from app import __version__
from app.config import Settings, get_settings
from app.errors import register_exception_handlers
from app.routers import ROUTERS


class HealthResponse(BaseModel):
    status: str
    version: str


def operation_id(route: APIRoute) -> str:
    """`<tag>_<route name>`, e.g. `projects_list`, so generated TS clients get clean names."""
    return f"{route.tags[0]}_{route.name}" if route.tags else route.name


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    # The planning workflow runner is created lazily (routers/workflows.py); stop it if used.
    workflows = getattr(app.state, "plan_workflows", None)
    if workflows is not None:
        workflows.shutdown()
    pool = getattr(app.state, "plan_workflows_pool", None)
    if pool is not None:
        pool.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title="OrchestrAI API",
        version=__version__,
        generate_unique_id_function=operation_id,
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)

    @app.get("/health", name="health", response_model=HealthResponse, tags=["meta"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    for router in ROUTERS:
        app.include_router(router)

    return app


app = create_app()
