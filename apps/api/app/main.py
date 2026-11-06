"""FastAPI application factory."""

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


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(
        title="OrchestrAI API", version=__version__, generate_unique_id_function=operation_id
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
