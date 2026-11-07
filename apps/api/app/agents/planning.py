"""Planning agent: project brief -> validated work breakdown structure.

The model proposes structure and three-point hours only. Everything is then checked in plain
Python: skills mapped to the team vocabulary, hours put in order and clamped, broken or
cyclic dependencies removed, stable ids T-001... assigned. Each fix adds a warning.
"""

import re
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, Field

from app.agents.llm import LLMClient
from app.agents.prompts import load_prompt
from app.engines.cpm import CycleError, topo_sort
from app.engines.types import TaskInput

PROMPT_NAME = "planning"
DEMO_BRIEF = Path(__file__).resolve().parents[2] / "fixtures" / "briefs" / "campus_food.md"

MIN_HOURS, MAX_HOURS = 1.0, 80.0  # hard bounds; the prompt asks for 4-40 h per task
MIN_TASKS, MAX_TASKS = 15, 35

# Common ways a model (or a person) names the skills in the seed vocabulary.
SYNONYMS = {
    "reactjs": "react",
    "nextjs": "react",
    "frontend": "react",
    "ts": "typescript",
    "javascript": "typescript",
    "js": "typescript",
    "node": "nodejs",
    "express": "nodejs",
    "backend": "fastapi",
    "py": "python",
    "postgresql": "postgres",
    "sql": "postgres",
    "database": "postgres",
    "mongo": "mongodb",
    "qa": "testing",
    "test": "testing",
    "tests": "testing",
    "ui": "ui-design",
    "ux": "ui-design",
    "uiux": "ui-design",
    "design": "ui-design",
    "cicd": "devops",
    "deployment": "devops",
    "kubernetes": "devops",
    "k8s": "devops",
    "kotlin": "android",
    "mobile": "android",
    "payment": "payments",
    "upi": "payments",
    "auth": "security",
    "authentication": "security",
}


class SkillReq(BaseModel):
    skill: str
    level: int = Field(description="1-5; 3 = can do it alone, 5 = expert")
    must: bool = True


class PlannedTask(BaseModel):
    local_id: str
    title: str
    description: str = ""
    required_skills: list[SkillReq] = Field(default_factory=list)
    o: float = Field(description="optimistic hours")
    m: float = Field(description="most likely hours")
    p: float = Field(description="pessimistic hours")
    predecessors: list[str] = Field(default_factory=list)


class PlannedEpic(BaseModel):
    local_id: str
    title: str
    tasks: list[PlannedTask]


class WBSPlan(BaseModel):
    epics: list[PlannedEpic]
    assumptions: list[str] = Field(default_factory=list)


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def match_skill(name: str, vocabulary: Iterable[str]) -> str | None:
    """Exact, then punctuation/case-insensitive, then synonym match; None if unknown."""
    by_key = {_key(v): v for v in vocabulary}
    k = _key(name)
    if k in by_key:
        return by_key[k]
    synonym = SYNONYMS.get(k)
    return synonym if synonym in by_key.values() else None


def build_prompt(brief: str, vocabulary: Iterable[str]) -> str:
    return load_prompt(PROMPT_NAME, brief=brief.strip(), skills=", ".join(sorted(vocabulary)))


def _fix_skills(task: PlannedTask, label: str, vocab: list[str], warnings: list[str]) -> None:
    kept: dict[str, SkillReq] = {}
    for req in task.required_skills:
        name = match_skill(req.skill, vocab)
        if name is None:
            warnings.append(f"{label}: dropped unknown skill {req.skill!r}")
            continue
        if name != req.skill:
            warnings.append(f"{label}: skill {req.skill!r} mapped to {name!r}")
        level = min(max(req.level, 1), 5)
        if level != req.level:
            warnings.append(f"{label}: skill {name} level {req.level} clamped to {level}")
        if name in kept:  # duplicate after mapping: keep the stricter requirement
            prev = kept[name]
            level, must = max(level, prev.level), prev.must or req.must
        else:
            must = req.must
        kept[name] = SkillReq(skill=name, level=level, must=must)
    task.required_skills = list(kept.values())
    if not kept:
        warnings.append(f"{label}: no skill from the vocabulary")


def _fix_hours(task: PlannedTask, label: str, warnings: list[str]) -> None:
    hours = sorted((task.o, task.m, task.p))
    if hours != [task.o, task.m, task.p]:
        warnings.append(f"{label}: o/m/p {task.o}/{task.m}/{task.p} reordered")
    clamped = [min(max(h, MIN_HOURS), MAX_HOURS) for h in hours]
    if clamped != hours:
        warnings.append(f"{label}: hours clamped to {MIN_HOURS:g}-{MAX_HOURS:g}")
    task.o, task.m, task.p = clamped


def validate_plan(plan: WBSPlan, vocabulary: Iterable[str]) -> tuple[WBSPlan, list[str]]:
    """Repair the model's plan in place (on a copy); return it with one warning per fix."""
    plan = plan.model_copy(deep=True)
    vocab = sorted(vocabulary)
    warnings: list[str] = []

    for epic in list(plan.epics):
        if not epic.tasks:
            warnings.append(f"epic {epic.title!r} has no tasks and was dropped")
            plan.epics.remove(epic)

    tasks = [t for e in plan.epics for t in e.tasks]
    new_id: dict[str, str] = {}
    for n, task in enumerate(tasks, start=1):
        tid = f"T-{n:03d}"
        if task.local_id in new_id:
            warnings.append(
                f"{tid}: duplicate local_id {task.local_id!r}, first one wins as a link"
            )
        else:
            new_id[task.local_id] = tid
        task.local_id = tid
    label = {t.local_id: f"{t.local_id} {t.title!r}" for t in tasks}

    for task in tasks:
        _fix_skills(task, label[task.local_id], vocab, warnings)
        _fix_hours(task, label[task.local_id], warnings)
        preds = []
        for ref in task.predecessors:
            pred = new_id.get(ref)
            if pred is None:
                warnings.append(f"{label[task.local_id]}: unknown predecessor {ref!r} removed")
            elif pred == task.local_id:
                warnings.append(f"{label[task.local_id]}: depends on itself, link removed")
            elif pred not in preds:
                preds.append(pred)
        task.predecessors = preds

    by_id = {t.local_id: t for t in tasks}
    num = {tid: k for k, tid in enumerate(by_id)}
    while True:
        try:
            topo_sort(
                [
                    TaskInput(
                        id=num[t.local_id],
                        o=0,
                        m=0,
                        p=0,
                        predecessors=tuple(num[p] for p in t.predecessors),
                    )
                    for t in tasks
                ]
            )
            break
        except CycleError as exc:
            ids = list(by_id)
            pred, succ = ids[exc.cycle[-2]], ids[exc.cycle[-1]]
            by_id[succ].predecessors.remove(pred)
            loop = " -> ".join(ids[i] for i in exc.cycle)
            warnings.append(f"cycle {loop}: removed link {pred} -> {succ}")

    if not MIN_TASKS <= len(tasks) <= MAX_TASKS:
        warnings.append(f"{len(tasks)} tasks; the prompt asks for {MIN_TASKS}-{MAX_TASKS}")
    return plan, warnings


def generate_plan(
    client: LLMClient, brief: str, vocabulary: Iterable[str]
) -> tuple[WBSPlan, list[str]]:
    vocab = list(vocabulary)
    raw = client.generate_structured(PROMPT_NAME, build_prompt(brief, vocab), WBSPlan)
    return validate_plan(raw, vocab)
