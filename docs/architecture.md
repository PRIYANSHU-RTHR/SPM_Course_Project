# Architecture

## Data model

PostgreSQL 16, managed with SQLAlchemy 2 models (`apps/api/app/models/`) and Alembic migrations (`apps/api/migrations/`).

- **Keys:** every table has an integer surrogate primary key (`id`).
- **Time:** timestamps are `timestamptz` set by the database clock (UTC). Calendar values use `date`.
- **Units:** effort is in hours as `float`. Money (`budget`, `hourly_rate`, `pv`/`ev`/`ac`) is `numeric`, in INR with 2 decimal places.

```mermaid
erDiagram
    project ||--o{ epic : has
    project ||--o{ task : has
    epic ||--o{ task : groups
    task ||--o{ dependency : "pred_task_id"
    task ||--o{ dependency : "succ_task_id"
    task ||--o{ assignment : "history (1 is_current)"
    member ||--o{ assignment : "assigned to"
    member ||--o{ member_skill : has
    skill ||--o{ member_skill : "rated in"
    member ||--o{ availability : has
    project ||--o{ risk : has
    project ||--o{ snapshot : has

    project {
        int id PK
        string name
        text brief
        date start_date
        date deadline
        numeric budget
        numeric hourly_rate
    }
    epic {
        int id PK
        int project_id FK
        string title
        int position
    }
    task {
        int id PK
        int project_id FK
        int epic_id FK
        string title
        float optimistic_hours "o <= m <= p"
        float most_likely_hours
        float pessimistic_hours
        int priority "1-5"
        enum status "todo|in_progress|blocked|done"
        jsonb required_skills "[{skill, level, must}]"
        float percent_complete "0-100"
        float actual_hours
    }
    dependency {
        int id PK
        int pred_task_id FK
        int succ_task_id FK "unique(pred, succ), pred != succ"
        enum type "FS"
    }
    member {
        int id PK
        string name
        string role
        string email UK
    }
    skill {
        int id PK
        string name UK
    }
    member_skill {
        int id PK
        int member_id FK "unique(member, skill)"
        int skill_id FK
        int level "1-5"
    }
    availability {
        int id PK
        int member_id FK
        enum kind "work|leave"
        date start_date
        date end_date
        float hours_per_week "0 when leave"
    }
    assignment {
        int id PK
        int task_id FK
        int member_id FK
        jsonb score_breakdown
        enum source "ai|pm_override"
        text reason
        bool is_current "unique per task when true"
        timestamptz created_at
    }
    risk {
        int id PK
        int project_id FK "unique(project, rule_key, subject_ref)"
        string rule_key
        string subject_ref
        string title
        enum category "schedule|resource|cost|skill|technical"
        int probability "1-5"
        int impact "1-5"
        enum status "open|mitigating|closed"
        jsonb rmmm
    }
    snapshot {
        int id PK
        int project_id FK "unique(project, date)"
        date date
        numeric pv
        numeric ev
        numeric ac
    }
    audit_log {
        int id PK
        string actor
        string action
        string entity
        int entity_id
        jsonb before
        jsonb after
        text reason
        timestamptz created_at
    }
```

`audit_log` points at the changed row through `entity` + `entity_id` (no foreign key). This lets it record any table, and audit rows survive deletes.

## Disruption → approval flow

A disruption is a fact: it is written (and audited) as soon as it is posted. The PM approves or rejects only the reassignment that follows. The reallocation graph (`app/workflows/reallocate.py`) runs in a worker thread and pauses once, at `pm_approval`, with `interrupt()`. Its state is checkpointed in Postgres under `thread_id`. Every number in the proposal and in `/metrics` comes from the engines through `services/scenario.py`. Every PM request can send an `X-Actor` header (default `PM`), which becomes `audit_log.actor`.

```mermaid
sequenceDiagram
    autonumber
    actor PM
    participant UI as Web UI
    participant API as FastAPI
    participant WF as Reallocation graph
    participant ENG as Engines (scenario)
    participant DB as Postgres

    UI->>API: GET /projects/{id}/metrics
    API->>ENG: evaluate(now)
    API-->>UI: P(on time), P50/P80, SPI, CPI, risks, overloaded ("before" chips)

    PM->>UI: Disruption simulator: leave / slip / scope add
    UI->>API: POST /projects/{id}/disruptions (X-Actor)
    API->>API: check_disruption (404 / 422), one run per project (409)
    API-->>UI: 202 {thread_id}
    UI->>API: GET /workflows/{thread_id}/events (SSE)

    API->>WF: start(thread_id)
    WF->>DB: apply_event: write the fact + audit (disruption.*)
    WF->>ENG: recompute: risk register, affected tasks
    WF->>ENG: propose: optimal assignment for affected tasks, before / now / if-approved
    WF->>DB: reallocation row (pending, payload = diff)
    WF-->>WF: interrupt() at pm_approval (checkpointed)
    API-->>UI: SSE node events (start / end per node), then run: waiting

    UI->>API: GET /projects/{id}/proposals/{thread_id}
    API->>DB: reallocation row
    API-->>UI: full diff: per-task owner/score/finish, metric chips, risks close/open

    PM->>UI: Approve (or reject with reason)
    UI->>API: POST /workflows/{thread_id}/resume {action} (X-Actor)
    API->>WF: Command(resume=decision + actor)
    alt approve
        WF->>DB: row approved + audit (reallocation.approved)
        WF->>DB: new owners + one audit row per task (assignment.ai)
        WF->>ENG: recompute_final: refresh risks, outcome
    else reject
        WF->>DB: row rejected + audit (reallocation.rejected), owners unchanged
    end
    API-->>UI: SSE run: committed / rejected (stream ends)

    UI->>API: GET /projects/{id}/metrics
    API-->>UI: "after" chips (UI animates before → after)
    UI->>API: GET /projects/{id}/audit?limit&offset
    API-->>UI: newest first, each row with a readable summary
```

## Brief → plan flow

The planning graph (`app/workflows/plan.py`) drafts, estimates, schedules and staffs a WBS, then pauses once at `pm_review`. Nothing is written to the project tables until the PM approves. An edit goes back through the engines, not the model, so a revised plan never needs a new LLM call.

```mermaid
sequenceDiagram
    autonumber
    actor PM
    participant UI as Web UI
    participant API as FastAPI
    participant WF as Planning graph
    participant LLM as Gemini / fixture
    participant ENG as Engines
    participant DB as Postgres

    PM->>UI: New plan → "Use the demo brief"
    UI->>API: GET /workflows/plan/example
    PM->>UI: Generate plan
    UI->>API: POST /workflows/plan (X-Actor)
    API-->>UI: 202 {thread_id}
    UI->>API: GET /workflows/{thread_id}/events (SSE)
    API->>WF: start(thread_id)
    WF->>LLM: decompose: brief + team skills → WBS (structured output)
    WF->>WF: validate: skills to vocabulary, hours ordered, cycles broken
    WF->>ENG: estimate (PERT, COCOMO II) → schedule (CPM) → recommend (Hungarian)
    WF-->>WF: interrupt() at pm_review (checkpointed)
    API-->>UI: SSE node events, then run: waiting
    UI->>API: GET /workflows/{thread_id}/state (review payload)
    alt request changes
        PM->>UI: edit o/m/p or skills
        UI->>API: POST /workflows/{id}/resume {action: edit, changes}
        API->>API: apply_changes check (422 on a bad edit)
        WF->>ENG: estimate → schedule → recommend, back to pm_review (revision + 1)
    else approve
        UI->>API: POST /workflows/{id}/resume {action: approve}
        WF->>DB: project, epics, tasks, dependencies, assignments + audit rows
        API-->>UI: SSE run: committed → link to the project
    else reject (reason)
        WF-->>UI: run: rejected, nothing written
    end
```

## One P(on time) everywhere

`services/scenario.py` loads a project's engine inputs once and evaluates them: CPM, the baseline and remaining-work schedules, the resource-adjusted Monte Carlo forecast and the risk findings. `GET /forecast`, `GET /metrics`, the risk register and every reallocation proposal (before / now / if approved) all go through it, at the project's clock (`sim_date`, else today). So every page and every proposal shows the same probability.
