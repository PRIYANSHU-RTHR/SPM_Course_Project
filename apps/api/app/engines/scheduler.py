"""Resource-constrained scheduling: serial schedule generation scheme (SSGS). Pure.

Tasks are taken in topological order, ties broken by priority (1 first), then CPM-critical
first, then id. Each task starts on the first working day after all predecessors end on
which its assignee has free hours, and its work is spread over the following working
days at whatever capacity the member has left (hours_per_week / 5, 0 on leave).
Unassigned tasks use the plain project calendar (8 h/day, no contention).
Granularity is one day: a successor starts the working day after its predecessor ends.

With `as_of`, only the remaining work ((1 - percent/100) x hours) is planned, from `as_of`
on. Finished tasks keep their baseline window (cut off before `as_of`); started tasks keep
their baseline start. Without `as_of` the result is the baseline that EVM measures against.
"""

import heapq
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date, timedelta

from app.engines import calendar
from app.engines.cpm import cpm
from app.engines.estimation import pert
from app.engines.types import (
    CPMResult,
    MemberInput,
    MemberWeekLoad,
    ScheduledTask,
    ScheduleResult,
    TaskInput,
)

_EPS = 1e-9
MAX_DAYS = 5 * 365  # a task that cannot finish within this is a data problem, not a schedule


class ScheduleError(ValueError):
    """The plan cannot be scheduled (e.g. work assigned to someone with no capacity)."""


def _order(tasks: Sequence[TaskInput], critical: set[int]) -> list[int]:
    by_id = {t.id: t for t in tasks}
    succ: dict[int, list[int]] = defaultdict(list)
    indegree = {t.id: len(set(t.predecessors)) for t in tasks}
    for t in tasks:
        for p in set(t.predecessors):
            succ[p].append(t.id)

    def key(i: int) -> tuple[int, bool, int]:
        return (by_id[i].priority, i not in critical, i)

    ready = [key(i) for i, d in indegree.items() if d == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        i = heapq.heappop(ready)[2]
        order.append(i)
        for s in succ[i]:
            indegree[s] -= 1
            if indegree[s] == 0:
                heapq.heappush(ready, key(s))
    return order


def _previous_working_day(d: date) -> date:
    d -= timedelta(days=1)
    while not calendar.is_working_day(d):
        d -= timedelta(days=1)
    return d


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def schedule(
    tasks: Sequence[TaskInput],
    assignments: Mapping[int, int | None],
    members: Sequence[MemberInput],
    project_start: date,
    durations: Mapping[int, float] | None = None,
    cpm_result: CPMResult | None = None,
    progress: Mapping[int, float] | None = None,
    as_of: date | None = None,
) -> ScheduleResult:
    """Place every task; `assignments` maps task id -> member id (missing/None = unassigned).

    `progress` maps task id -> percent complete; it is only used together with `as_of`.
    """
    hours = {t.id: (durations[t.id] if durations else pert(t).te) for t in tasks}
    plan = cpm_result or cpm(tasks, hours)  # also validates the graph (cycles, unknown ids)
    rows = {r.task_id: r for r in plan.tasks}
    by_member = {m.id: m for m in members}
    by_id = {t.id: t for t in tasks}

    for task_id, member_id in assignments.items():
        if member_id is None or hours.get(task_id, 0) <= 0:
            continue
        member = by_member.get(member_id)
        if member is None:
            raise ScheduleError(f"task {task_id} is assigned to unknown member {member_id}")
        if member.hours_per_week <= 0:
            raise ScheduleError(
                f"member {member_id} has no working capacity but is assigned task {task_id}"
            )

    start = calendar.next_working_day(project_start)
    today = start
    base: dict[int, ScheduledTask] = {}
    if as_of is not None:
        today = calendar.next_working_day(max(as_of, project_start))
        baseline = schedule(tasks, assignments, members, project_start, durations, plan)
        base = {t.task_id: t for t in baseline.tasks}
    done = {i: min(max(v, 0.0), 100.0) for i, v in (progress or {}).items()} if base else {}
    booked: dict[int, dict[date, float]] = defaultdict(lambda: defaultdict(float))
    end_of: dict[int, date] = {}
    placed: list[ScheduledTask] = []

    for i in _order(tasks, {r.task_id for r in plan.tasks if r.critical}):
        member_id = assignments.get(i)
        member = by_member.get(member_id) if member_id is not None else None
        day = max(
            (calendar.add_working_days(end_of[p], 1) for p in by_id[i].predecessors),
            default=start,
        )
        day = max(day, today)

        def free(d: date, member: MemberInput | None = member) -> float:
            if member is None:
                return calendar.HOURS_PER_DAY if calendar.is_working_day(d) else 0.0
            return calendar.daily_capacity(member, d) - booked[member.id][d]

        pct = done.get(i, 0.0)
        remaining = hours[i] * (1 - pct / 100)
        first = last = None
        for _ in range(MAX_DAYS):
            if remaining <= _EPS:
                break
            take = min(max(free(day), 0.0), remaining)
            if take > _EPS:
                if member is not None:
                    booked[member.id][day] += take
                remaining -= take
                first = first or day
                last = day
            day = calendar.next_working_day(day + timedelta(days=1))
        else:
            raise ScheduleError(f"task {i} cannot be finished within {MAX_DAYS} days")

        if pct > 0 and first is None:  # finished: keep its baseline window, ended before today
            last = min(base[i].end, _previous_working_day(today))
            first = min(base[i].start, last)
        elif pct > 0 and first is not None:  # started: it began on its baseline start
            first = min(base[i].start, first)
        if first is None or last is None:  # zero-hour task: a milestone on its earliest day
            first = last = calendar.next_working_day(day)
        end_of[i] = last
        early = calendar.hours_to_window(start, rows[i].es, rows[i].ef)[0]
        placed.append(
            ScheduledTask(
                task_id=i,
                member_id=member_id if member is not None else None,
                start=first,
                end=last,
                hours=hours[i],
                early_start=early,
                resource_delay_days=calendar.working_days_between(early, first),
            )
        )

    finish = max(end_of.values(), default=start)
    loads = []
    week = _monday(today)
    while week <= finish:
        days = calendar.working_days(week, week + timedelta(days=4))
        for m in members:
            cap = sum(calendar.daily_capacity(m, d) for d in days)
            used = sum(booked[m.id].get(d, 0.0) for d in days)
            loads.append(MemberWeekLoad(m.id, week, used, cap, used / cap if cap else 0.0))
        week += timedelta(days=7)

    return ScheduleResult(
        tasks=tuple(placed),
        loads=tuple(loads),
        finish=finish,
        delayed=tuple(t.task_id for t in placed if t.resource_delay_days > 0),
    )
