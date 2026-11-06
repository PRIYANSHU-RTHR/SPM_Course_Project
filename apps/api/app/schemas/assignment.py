from datetime import datetime
from typing import Any

from app.models.enums import AssignmentSource
from app.schemas.common import ReadModel


class AssignmentRead(ReadModel):
    id: int
    task_id: int
    member_id: int
    score_breakdown: dict[str, Any]
    source: AssignmentSource
    reason: str | None
    is_current: bool
    created_at: datetime
