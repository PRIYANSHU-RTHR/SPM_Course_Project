"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import __version__
from app.config import Settings, get_settings
from app.errors import register_exception_handlers
from app.routers import assignment, cpm, estimate


class HealthResponse(BaseModel):
    status: str
    version: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(title="OrchestrAI API", version=__version__)
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(estimate.router)
    app.include_router(cpm.router)
    app.include_router(assignment.router)

    @app.get("/health", response_model=HealthResponse, tags=["meta"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    return app


app = create_app()
