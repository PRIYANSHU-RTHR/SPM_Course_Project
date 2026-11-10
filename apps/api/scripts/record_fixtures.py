"""Record the LLM fixtures the demo replays: the demo brief through the planning workflow.

Run by `make record-fixtures` inside the api container, with LLM_MODE=record and a Gemini key.
The workflow runs up to the PM review interrupt and stops there: nothing is written to the
database. The reply is saved to fixtures/llm/<prompt>__<hash>.json; the hash covers the brief
and the team's skill vocabulary, so the database must hold the demo seed (`make demo`).
"""

import sys
import time
from datetime import date

from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import func, select

from app.agents.llm import FIXTURES_DIR, LLMClient
from app.agents.planning import DEMO_BRIEF
from app.config import get_settings
from app.db import get_session_factory
from app.models import Skill
from app.schemas.workflow import PlanStart
from app.services.workflows import build_workflows

# Only the brief and the skill vocabulary go into the prompt (and its fixture key); these
# other fields just have to be valid.
DEMO_PLAN = PlanStart(
    brief=DEMO_BRIEF.read_text(encoding="utf-8"),
    project_name="Campus Food-Ordering App v2",
    start_date=date(2026, 11, 9),
    deadline=date(2027, 2, 26),
    budget="900000.00",  # type: ignore[arg-type]
)
TIMEOUT_SECONDS = 180


def main() -> int:
    settings = get_settings()
    if settings.llm_mode != "record":
        print(f"LLM_MODE must be 'record' (is {settings.llm_mode!r})", file=sys.stderr)
        return 2
    session_factory = get_session_factory()
    with session_factory() as session:
        if not session.scalar(select(func.count()).select_from(Skill)):
            print("No skills in the database: run `make demo` (it seeds) first", file=sys.stderr)
            return 2

    started = time.time()
    runners = build_workflows(
        InMemorySaver(), session_factory, LLMClient(settings), seed=settings.sim_seed
    )
    try:
        thread_id = runners.plan.start(DEMO_PLAN)
        runners.plan.wait(thread_id, TIMEOUT_SECONDS)
        state = runners.plan.state(thread_id)
    finally:
        runners.shutdown()

    if state.status != "waiting" or state.review is None:
        print(f"Planning run ended as {state.status!r}, not at PM review", file=sys.stderr)
        return 1
    written = sorted(p.name for p in FIXTURES_DIR.glob("*.json") if p.stat().st_mtime >= started)
    tasks = sum(len(epic.tasks) for epic in state.review.wbs.epics)
    warnings = len(state.review.warnings)
    print(f"Planning workflow reached PM review: {tasks} tasks, {warnings} warnings")
    for name in written:
        print(f"recorded fixtures/llm/{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
