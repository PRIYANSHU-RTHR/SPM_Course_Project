"""Domain exceptions and the single place that maps them to HTTP responses.

Services raise `DomainError` subclasses; routers never build error responses themselves.
Response body shape: `{"error": {"code": str, "message": str, "details": dict}}`.
"""

from typing import Any, ClassVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base class for expected, user-facing errors raised by services."""

    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "domain_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class ValidationFailedError(DomainError):
    status_code = 422
    code = "validation_failed"


async def _handle_domain_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_domain_error)
