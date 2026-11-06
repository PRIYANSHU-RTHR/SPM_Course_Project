from typing import Self

from pydantic import BaseModel, model_validator

from app.models.enums import DependencyType
from app.schemas.common import Page, ReadModel


class DependencyCreate(BaseModel):
    """`pred_task_id` must finish before `succ_task_id` starts (finish-to-start)."""

    pred_task_id: int
    succ_task_id: int

    @model_validator(mode="after")
    def _not_self(self) -> Self:
        if self.pred_task_id == self.succ_task_id:
            raise ValueError("a task cannot depend on itself")
        return self


class DependencyRead(ReadModel):
    id: int
    pred_task_id: int
    succ_task_id: int
    type: DependencyType


class DependencyPage(Page[DependencyRead]):
    pass
