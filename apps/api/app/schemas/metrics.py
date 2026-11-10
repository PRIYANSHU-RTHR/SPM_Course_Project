"""One compact, engine-made status object per project (KPI chips, before -> after)."""

from datetime import date

from pydantic import BaseModel, Field


class ProjectMetrics(BaseModel):
    project_id: int
    as_of: date = Field(description="The project's clock (`sim_date`, else today)")
    deadline: date
    p_on_time: float | None = Field(
        description="Resource-adjusted Monte Carlo P(finish <= deadline), 0..1; "
        "same computation as the reallocation proposal's `now` / `if_approved`"
    )
    p50: date | None = Field(description="Median finish date (Monte Carlo)")
    p80: date | None = Field(description="80th-percentile finish date (Monte Carlo)")
    spi: float | None = Field(description="Schedule performance index EV / PV")
    cpi: float | None = Field(description="Cost performance index EV / AC")
    open_risks: int = Field(description="Risks the rules raise right now (open register rows)")
    overloaded_members: int = Field(
        description="Members booked above capacity in at least one week (member_overload rule)"
    )
