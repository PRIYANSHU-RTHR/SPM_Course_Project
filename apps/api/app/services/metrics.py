"""The project's headline numbers from one scenario evaluation (services/scenario.py), so
they agree with the risk register and the reallocation proposal's `now` chips."""

from sqlalchemy.orm import Session

from app.schemas.metrics import ProjectMetrics
from app.services.inputs import get_project, project_today
from app.services.scenario import load_scenario

OVERLOAD_RULE = "member_overload"


def project_metrics(session: Session, project_id: int, seed: int) -> ProjectMetrics:
    project = get_project(session, project_id)
    as_of = project_today(project)
    scenario = load_scenario(session, project, as_of, seed)
    if not scenario.tasks:
        return ProjectMetrics(
            project_id=project.id,
            as_of=as_of,
            deadline=project.deadline,
            p_on_time=None,
            p50=None,
            p80=None,
            spi=None,
            cpi=None,
            open_risks=0,
            overloaded_members=0,
        )
    outcome = scenario.evaluate()
    m, findings, evm = outcome.metrics(), outcome.findings(), scenario.evm
    return ProjectMetrics(
        project_id=project.id,
        as_of=as_of,
        deadline=project.deadline,
        p_on_time=m.p_on_time,
        p50=m.p50,
        p80=m.p80,
        spi=evm.spi if evm else None,
        cpi=evm.cpi if evm else None,
        open_risks=len(findings),
        overloaded_members=len({f.subject_ref for f in findings if f.rule_key == OVERLOAD_RULE}),
    )
