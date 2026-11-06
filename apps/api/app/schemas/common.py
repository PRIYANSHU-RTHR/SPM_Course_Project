"""Shared API schemas: error body, pagination envelope, PATCH base."""

from typing import Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict, model_validator


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any]


class ErrorResponse(BaseModel):
    """Body of every DomainError response (see `app/errors.py`)."""

    error: ErrorBody


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PatchModel(BaseModel):
    """PATCH body: omitted fields stay unchanged; explicit `null` only for nullable columns."""

    nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _reject_null_for_required_columns(self) -> Self:
        for name in self.model_fields_set:
            if getattr(self, name) is None and name not in self.nullable_fields:
                raise ValueError(f"{name} cannot be null")
        return self

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


# 404/409 documented with the real error body so generated TS types are accurate.
NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Not found"}
}
CONFLICT: dict[int | str, dict[str, Any]] = {
    409: {"model": ErrorResponse, "description": "Conflict"}
}
