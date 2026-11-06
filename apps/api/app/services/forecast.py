"""Monte Carlo forecast for a project, on the shared working calendar."""

import math
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.engines.calendar import HOURS_PER_DAY, add_working_days, working_days_between
from app.engines.cpm import CycleError
from app.engines.montecarlo import forecast
from app.engines.types import ForecastResult, TaskInput
from app.errors import ConflictError
from app.models import Project
from app.schemas.forecast import CdfPoint, HistogramBin, Percentile, ProjectForecast
from app.services.inputs import get_project, load_tasks


def _on_day(start: date, hours: float) -> Percentile:
    return Percentile(
        hours=hours,
        on=add_working_days(start, max(math.ceil(hours / HOURS_PER_DAY - 1e-9) - 1, 0)),
    )


def deadline_hours(project: Project) -> float:
    """Working hours from project start to the end of the deadline day (inclusive)."""
    return (
        working_days_between(project.start_date, project.deadline + timedelta(days=1))
        * HOURS_PER_DAY
    )


def build_forecast(
    session: Session, project: Project, runs: int, seed: int, tasks: list[TaskInput] | None = None
) -> ForecastResult:
    """Raw engine result (used by the forecast endpoint and the risk service)."""
    try:
        return forecast(
            tasks if tasks is not None else load_tasks(session, project.id),
            deadline_hours(project),
            runs,
            seed,
        )
    except CycleError as exc:
        raise ConflictError(str(exc), details={"cycle": exc.cycle}) from exc


def project_forecast(session: Session, project_id: int, runs: int, seed: int) -> ProjectForecast:
    project = get_project(session, project_id)
    result = build_forecast(session, project, runs, seed)

    start = project.start_date
    return ProjectForecast(
        project_id=project_id,
        runs=result.runs,
        seed=result.seed,
        deadline=project.deadline,
        deadline_hours=deadline_hours(project),
        p_on_time=result.p_on_time or 0.0,
        mean_hours=result.mean,
        p50=_on_day(start, result.p50),
        p80=_on_day(start, result.p80),
        p95=_on_day(start, result.p95),
        histogram=[HistogramBin(start_hours=h, runs=c) for h, c in result.histogram],
        cdf=[CdfPoint(hours=h, probability=p) for h, p in result.cdf],
        criticality=result.criticality,
    )
