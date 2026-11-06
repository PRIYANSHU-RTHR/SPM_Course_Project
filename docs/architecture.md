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
