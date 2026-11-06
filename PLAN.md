# OrchestrAI — Build Plan

> Smart Project Management with Auto‑Assigning Tasks
> SPM Course · Group 5 · Manveer Anand · Priyanshu Rathore · Ravi Kumawat

This file is the single source of truth for **what** to build and **in what order**.
`CLAUDE.md` says **how** to build it. `docs/temp.md` is the running log of what has been done.

---

## 1. What we are building (one paragraph)

OrchestrAI turns a plain‑English project brief into a **Work Breakdown Structure**, estimates it with **PERT and COCOMO II**, schedules it with the **Critical Path Method**, assigns every task to the best‑fit team member with an **explainable, optimal assignment engine**, forecasts the delivery date with **Monte Carlo simulation**, tracks health with **Earned Value Management**, keeps a live **risk register (RMMM)**, and — when something goes wrong (someone goes on leave, a task slips) — **proposes a re‑allocation that the PM approves or rejects** through a LangGraph human‑in‑the‑loop workflow. The LLM plans and explains; deterministic code calculates every number.

### Why this version (changes from the intro deck)

| Intro deck had | This plan adds | Why |
|---|---|---|
| Skill/capacity/load scoring | Same 60/25/15 score **plus** optimal batch assignment (Hungarian algorithm) and a greedy‑vs‑optimal comparison | Shows real algorithmic depth; directly cites assignment‑problem literature |
| "Dependency validation, critical‑path rules" | Full CPM: forward/backward pass, slack, critical path, resource‑constrained schedule, Gantt | CPM/PERT is in every SPM syllabus |
| "Monitor delays and risks" | EVM (PV, EV, AC, SPI, CPI, EAC, ETC, TCPI) + Monte Carlo P(on‑time) + risk register with P×I matrix | EVM, Monte Carlo and RMMM are core SPM units — examiners look for them |
| Effort is implicit | PERT three‑point estimates per task + COCOMO II project estimate | Estimation is its own SPM unit |
| Reallocation with approval | A **Disruption Simulator** that triggers it live in the demo | Makes the demo memorable |
| Gemini always required | **Fixture mode**: recorded LLM responses so the demo never fails on stage | Rate limits / Wi‑Fi in the lab |

Small fixes for the deck: slide 11 is blank; the architecture image says "CatsAPI" (should be Core API); double‑check that references [1], [2] and [5] exist exactly as cited before submission.

---

## 2. SPM syllabus → feature mapping (put this table in the report)

| SPM topic | Where it lives in OrchestrAI |
|---|---|
| Project planning, scope, WBS | Planning agent → editable WBS tree (Epic → Task) |
| Effort/cost estimation (PERT, COCOMO II) | Estimation engine; per‑task `o/m/p`, project‑level COCOMO II effort & duration |
| Activity network, CPM, PERT, slack | Dependency engine; network graph with critical path highlighted |
| Gantt chart, scheduling | Resource‑constrained scheduler → Gantt view |
| Resource allocation & levelling | Assignment engine (score + Hungarian), capacity heatmap |
| Risk identification, assessment, RMMM | Risk engine (rule detectors) + risk agent (mitigation/monitoring/management plan), P×I matrix |
| Monte Carlo schedule risk | 5,000‑run simulation → completion CDF, P50/P80/P95, task criticality index |
| Monitoring & control, EVM | EVM engine + S‑curve (PV/EV/AC), SPI/CPI KPIs |
| Change control / configuration mgmt | Reallocation proposals with approve/reject + immutable audit log |
| Team organisation | Team page: skills matrix, availability, bus‑factor warnings |

---

## 3. Architecture

```
apps/
  web/        React + TypeScript + Vite + Tailwind + shadcn/ui  (Ravi)
  api/        FastAPI + SQLAlchemy 2 + Alembic + LangGraph        (Priyanshu)
    app/engines/   pure-Python deterministic engines             (Manveer)
    app/agents/    Gemini calls + prompts + fixtures              (Manveer)
    app/workflows/ LangGraph graphs (plan, reallocate)            (Priyanshu)
infra/        docker-compose, Dockerfiles
docs/         temp.md (build log), architecture.md, demo-script.md, report assets
```

- **Postgres** is the source of truth and also the LangGraph checkpointer store (`langgraph-checkpoint-postgres`).
- **SSE** (`text/event-stream`) streams workflow node events to the UI so the PM watches the agent think.
- **OpenAPI → TypeScript types** (`openapi-typescript`) keeps frontend and backend in sync.
- **Rule:** the LLM never produces a number that is shown as a metric. It produces structure (WBS, skills, three‑point estimates as *inputs*) and prose (explanations, mitigations). Engines compute everything else.

### Assignment score (from the deck, now precise)

```
score = 100 × (0.60·skill_fit + 0.25·capacity_fit + 0.15·balance)
skill_fit    = Σ_s w_s · min(level_member_s / level_required_s, 1)        (levels 1–5)
capacity_fit = clamp(free_hours_in_task_window / task_hours, 0, 1)
balance      = 1 − (member_utilisation / max_team_utilisation)
eligible     = has every "must" skill at ≥ required level − 1 AND not on leave for >50% of window
```
Batch mode builds the task × member cost matrix (`100 − score`, ineligible = large) and solves it with `scipy.optimize.linear_sum_assignment`, repeating per scheduling wave so one person can take several tasks over time.

---

## 4. Demo story (what the 5‑minute demo must show)

1. **Brief → plan (60s).** Paste a brief for "Campus Food‑Ordering App". The timeline streams: *Decompose → Validate → Estimate → Schedule → Assign → Awaiting PM review*. A WBS of ~25 tasks appears.
2. **Review (45s).** PM edits one estimate, opens a recommendation: Bob 91 · Eva 82 · Alice 63, bars show skill/capacity/balance, the AI explanation cites those exact numbers. Approve.
3. **Plan health (45s).** Dashboard: critical path on the network graph, Gantt, Monte Carlo says **P(on time) = 81%**, COCOMO II vs bottom‑up estimate compared.
4. **Disruption (60s).** Disruption Simulator → "Bob on leave 10 days". Risk register lights up, P(on time) drops to **47%**, two critical tasks flagged. A reallocation proposal appears as a diff (before/after owner, Δ finish date, Δ probability).
5. **Approve (30s).** PM approves; numbers recover to ~74%; audit log records who/what/why.
6. **Control (30s).** Advance simulated time 2 weeks → EVM S‑curve, SPI 0.92 / CPI 1.04, risk agent's mitigation plan.

Seed data must make these numbers land roughly where described (tune seed, not code).

---

## 5. Step‑by‑step build (one step = one commit)

Each step is small enough for one reviewable commit. **Claude implements exactly one step, logs it in `docs/temp.md`, suggests a commit message, and stops.** You review, then commit yourself.

Owner key: **R** = Ravi (frontend, seed, docs), **P** = Priyanshu (backend, workflows, infra), **M** = Manveer (engines, AI agents).

Rough timeline — Week 1: P 01→02→03→05 · M 06, 07 (after 01) · R 18 (mocked data). Week 2: P 13, 12 · M 08–11 · R 04 (after 03), 19, 21. Week 3: P 15, 17 · M 14, 16 · R 20, 22, 23. Week 4: 24 (R+P), 25, 26, 27, rehearsal.

Git: one branch per step (`feat/NN-short-name`), PR reviewed by one other member. Pull `main` before starting a step. Ready-to-paste Claude Code prompts for every step are in `prompts.md`.

### Phase 0 — Foundation

**Step 01 · Repo scaffold** (P)
- Monorepo folders above, root `README.md` stub, `.gitignore`, `.editorconfig`, `.env.example`, `Makefile` with placeholder targets, `docs/temp.md` with the log template from CLAUDE.md, `infra/docker-compose.yml` with only Postgres 16.
- Done when: `docker compose -f infra/docker-compose.yml up -d db` works.
- Commit: `chore: scaffold monorepo and postgres compose`

**Step 02 · API skeleton** (P)
- `apps/api` with `uv`, FastAPI app factory, `pydantic-settings` config, CORS, `/health`, ruff + pytest config, one passing test.
- Commit: `feat(api): fastapi skeleton with settings and health check`

**Step 03 · Data model + migrations** (P)
- SQLAlchemy 2 models: `member`, `skill`, `member_skill(level 1–5)`, `availability(leave ranges, hours/week)`, `project(deadline, budget, hourly_rate)`, `epic`, `task(o/m/p hours, priority, status, required skills JSON, percent_complete, actual_hours)`, `dependency(pred, succ, type FS)`, `assignment(task, member, score breakdown JSON, source=ai|pm_override)`, `risk(prob, impact, category, status, rmmm JSON)`, `snapshot(date, pv, ev, ac)`, `audit_log`.
- Alembic initial migration.
- Commit: `feat(api): core domain models and initial migration`

**Step 04 · Seed data** (R)
- `make seed`: 8 members with realistic, uneven skills; one reference project ("Campus Food‑Ordering App") with ~25 tasks, dependencies, two weeks of progress snapshots. Deterministic (fixed RNG seed).
- Commit: `feat(api): deterministic demo seed data`

**Step 05 · CRUD APIs** (P)
- Routers for projects, epics, tasks, dependencies, members, skills. Pydantic v2 schemas, pagination, 404/422 handling. Tests.
- Commit: `feat(api): crud endpoints for projects, tasks and team`

### Phase 1 — Deterministic engines (the SPM core; pure functions, heavy tests)

**Step 06 · Estimation engine** (M)
- PERT: `te = (o + 4m + p)/6`, `σ² = ((p − o)/6)²`, project σ along critical path.
- COCOMO II post‑architecture (nominal multipliers, scale factors configurable): effort PM, duration TDEV, team size.
- `GET /projects/{id}/estimate`. Unit tests with textbook values.
- Commit: `feat(engines): pert and cocomo ii estimation`

**Step 07 · Dependency & CPM engine** (M)
- Cycle detection (Kahn topo sort, returns the cycle), forward/backward pass, ES/EF/LS/LF, total & free slack, critical path(s).
- `GET /projects/{id}/cpm`. Tests incl. a textbook network and a cycle case.
- Commit: `feat(engines): cpm with slack and critical path`

**Step 08 · Assignment engine** (M)
- Eligibility, score with breakdown (formula §3), greedy ranking per task, optimal batch via Hungarian. Returns top‑3 candidates + breakdown.
- `POST /projects/{id}/assignments/recommend?mode=greedy|optimal`. Tests incl. a case where greedy is worse than optimal.
- Commit: `feat(engines): explainable scoring and hungarian batch assignment`

**Step 09 · Resource‑constrained scheduler** (M)
- Serial schedule generation: walk tasks in priority/topo order, place each at the earliest date where predecessors are done and the assignee has capacity (hours/week, leave). Outputs start/end per task and per‑member weekly load.
- `GET /projects/{id}/schedule`. Tests.
- Commit: `feat(engines): resource-constrained scheduling`

**Step 10 · Monte Carlo engine** (M)
- Vectorised NumPy: sample each task from Beta‑PERT(o, m, p), N = 5,000, compute project finish per run over the dependency network. Output P(finish ≤ deadline), P50/P80/P95, histogram bins, CDF points, per‑task criticality index. Seeded for reproducibility. Must run < 1s for 50 tasks.
- `GET /projects/{id}/forecast`.
- Commit: `feat(engines): monte carlo completion forecast`

**Step 11 · EVM engine** (M)
- From baseline schedule + snapshots: PV, EV, AC, SV, CV, SPI, CPI, EAC (= BAC/CPI), ETC, VAC, TCPI; time‑series for the S‑curve.
- `GET /projects/{id}/evm`. Tests with worked example.
- Commit: `feat(engines): earned value management metrics`

**Step 12 · Risk engine** (P)
- Rule detectors → risk records with probability × impact (1–5) and category: member over 100% utilisation, critical task with bus factor 1, SPI < 0.9 or CPI < 0.9, P(on time) < 60%, task blocked by late predecessor, skill gap (no eligible member).
- Upserts into risk register (idempotent per rule + subject). `GET /projects/{id}/risks`.
- Commit: `feat(engines): rule-based risk detection and register`

### Phase 2 — AI + workflows

**Step 13 · LLM client + fixture mode** (P)
- Wrapper over the `google-genai` SDK with Pydantic structured output, timeout, retry, token logging. Model from `GEMINI_MODEL` env (check current model list first — Gemini 2.5 was shut down Oct 2026).
- `LLM_MODE=live|record|fixture`: record writes responses to `apps/api/fixtures/llm/*.json` keyed by prompt hash; fixture replays them; demo defaults to fixture.
- Commit: `feat(agents): gemini client with structured output and fixture mode`

**Step 14 · Planning agent** (M)
- Prompt + schema: brief → epics → tasks (title, description, required skills from the allowed vocabulary, o/m/p hours, predecessors by local id). Post‑validation: unknown skills mapped/rejected, cycles removed with a warning, hours clamped.
- Unit test with fixture.
- Commit: `feat(agents): planning agent producing validated wbs`

**Step 15 · Planning workflow (LangGraph)** (P)
- Graph: `decompose → validate → estimate → schedule → recommend → interrupt(pm_review) → commit`. `PostgresSaver` checkpointer, `thread_id` per run.
- Endpoints: `POST /workflows/plan` (start), `GET /workflows/{thread}/events` (SSE of node start/finish + payload summaries), `POST /workflows/{thread}/resume` (approve / edit / reject using `Command(resume=…)`), `GET /workflows/{thread}/state`.
- Commit: `feat(workflows): langgraph planning workflow with human review`

**Step 16 · Explanation & risk agents** (M)
- Explanation agent: input is the score breakdown + member/task facts only; output 2–3 sentences that may only cite provided numbers. Add a check that every number in the output exists in the input; otherwise fall back to a template.
- Risk agent: for each open risk produce an RMMM entry (mitigation, monitoring trigger, contingency).
- Commit: `feat(agents): grounded assignment explanations and rmmm risk plans`

**Step 17 · Reallocation workflow + disruption API** (P)
- `POST /projects/{id}/disruptions` with type `leave|slip|scope_add`. Graph: `apply_event → recompute (cpm, schedule, forecast, risks) → propose (re‑run optimal assignment only for affected tasks) → interrupt(pm_approval) → apply + audit_log`. Proposal payload: per‑task before/after owner, Δ finish, Δ P(on time).
- `POST /projects/{id}/simulate/advance?days=N` moves the simulated clock and generates snapshots.
- Commit: `feat(workflows): disruption-driven reallocation with approval`

### Phase 3 — Frontend

**Step 18 · Web scaffold + design system** (R)
- Vite + React + TS, Tailwind, `shadcn` init, Geist Sans/Mono, design tokens from CLAUDE.md, app shell (left rail, top bar with project switcher, `⌘K` command palette via `cmdk`), TanStack Query, router, generated API types (`pnpm gen:api`).
- Commit: `feat(web): app shell, design tokens and api client`

**Step 19 · Projects list + project overview** (R)
- KPI strip (P(on time), SPI, CPI, critical tasks, overloaded members, open risks), mini burn/S‑curve, upcoming critical tasks table.
- Commit: `feat(web): project overview dashboard`

**Step 20 · New project flow** (R)
- Brief textarea + deadline/budget → start workflow → live vertical run timeline from SSE (node, duration, short summary) → WBS tree review with inline‑editable o/m/p and skills → Approve / Request changes.
- Commit: `feat(web): brief-to-plan flow with live workflow timeline`

**Step 21 · Network graph + Gantt** (R)
- `@xyflow/react` dependency graph (auto‑layout with `dagre`/`elkjs`), critical path in accent, slack shown on nodes. Gantt (custom, SVG/CSS grid): bars by owner colour, slack as hatched tail, today line, dependency lines on hover.
- Commit: `feat(web): dependency network and gantt views`

**Step 22 · Team & assignment views** (R)
- Skills matrix, capacity heatmap (member × week, % load), recommendation side sheet: top‑3 candidates, stacked score bars, AI explanation, Approve / Override (pick another member + reason). Toggle greedy vs optimal with total‑score delta.
- Commit: `feat(web): team capacity and explainable assignment review`

**Step 23 · Risk, EVM & forecast views** (R)
- Risk register table + 5×5 P×I matrix (click cell filters table), RMMM detail panel. EVM S‑curve (PV/EV/AC) + KPI cards with formula tooltips. Monte Carlo histogram + CDF with deadline marker and P50/P80/P95.
- Commit: `feat(web): risk register, evm and monte carlo views`

**Step 24 · Disruption simulator + approvals inbox + audit log** (R + P)
- Simulator panel (leave / slip / scope add, advance clock). Approvals inbox with proposal diff table and before→after metric chips; numbers transition smoothly after approval. Audit log timeline.
- Commit: `feat(web): disruption simulator, approvals and audit trail`

### Phase 4 — Ship

**Step 25 · Tests & CI** (P)
- Backend coverage ≥ 80% on `engines/`; a frontend smoke test (Vitest + Testing Library) for the overview; GitHub Actions: ruff, pytest, tsc, eslint, web build.
- Commit: `ci: lint, type-check and test workflows`

**Step 26 · Docker & one‑command demo** (P)
- Dockerfiles (api, web), full compose, `make demo` = up + migrate + seed + `LLM_MODE=fixture`. Record fixtures for the demo brief with `LLM_MODE=record`.
- Commit: `build: dockerised stack and one-command demo`

**Step 27 · Docs, polish, deploy** (R lead, all)
- README: what/why, screenshots/GIF, architecture (Mermaid), SPM mapping table, formulas, how to run. `docs/demo-script.md` (the §4 script with click path). Optional deploy (API + DB on Render/Railway, web on Vercel). Final UI pass against the anti‑AI checklist.
- Commit: `docs: readme, architecture, demo script`

---

## 6. Evaluation (for the report)

- **Assignment quality:** on seed + 3 synthetic teams, compare random / round‑robin / greedy / optimal on total score, utilisation std‑dev, and makespan.
- **Forecast sanity:** Monte Carlo P50 vs CPM deterministic finish; show σ from PERT vs simulation spread.
- **Disruption recovery:** P(on time) before disruption → after → after approved reallocation.
- **Explanation grounding:** % of explanations passing the numbers‑must‑exist check.

## 7. Resume bullets (once it is built — edit numbers to what you actually measure)

- Built OrchestrAI, an AI‑assisted project‑planning system (FastAPI, LangGraph, Gemini, PostgreSQL, React/TS) that converts a project brief into a scheduled, staffed plan with PM approval via LangGraph human‑in‑the‑loop interrupts and Postgres checkpointing.
- Implemented CPM, resource‑constrained scheduling, Hungarian‑algorithm task assignment and a vectorised Monte Carlo forecaster (5k runs < 1s), improving total assignment score by X% over greedy on benchmark teams.
- Streamed multi‑step agent execution to the UI over SSE and kept LLM output grounded: all metrics computed deterministically, explanations validated against source numbers.