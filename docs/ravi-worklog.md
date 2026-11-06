# Ravi's work log

Ravi Kumawat's steps on OrchestrAI (frontend, seed data, docs): what is done, what is next, and what each step is waiting for.

Update this file at the end of every step. `docs/temp.md` stays the detailed, local build log.

**Last updated:** 2026-11-06

## Where things stand

| Step | Work | Status | Waiting for |
|---|---|---|---|
| 18 | Web scaffold and design system | Merged | Nothing |
| 04 | Seed data | Merged | Nothing |
| 19 | Projects list and overview | Done, in [PR #5](https://github.com/PRIYANSHU-RTHR/SPM_Course_Project/pull/5), not merged | PR review by a teammate |
| 21 | Network graph and Gantt | Done, on `feat/21-network-gantt`, no PR yet | PR after PR #5 merges |
| 23 | Risk, EVM and forecast views | Done, on `feat/23-risk-evm-forecast`, no PR yet | PR after Step 21 merges. Generate plan needs Step 16 |
| 22 | Team and assignment views | Next | AI explanations need Step 16 merged |
| 20 | New project flow | Not started | Mock stream until Step 15 exists |
| 24 (UI) | Disruption simulator, approvals, audit | Blocked | 17 and Priyanshu's Step 24 API work merged |
| 27 | Docs, polish, deploy | Blocked | 26 merged |

**Team progress on 2026-11-06**

- On `main`: Steps 01 to 13, and 18.
- Pushed by Manveer, not merged: Steps 14 and 16, and the evaluation report.
- Not on GitHub yet: Steps 15, 17, 24 (API), 25, 26.
- Shared git history was rewritten on 2026-11-06. Old local branches must not be pushed.

## Next actions

1. Get PR #5 (Step 19) reviewed and merged.
2. Raise the open questions below. The forecast one blocks the demo story.
3. Open the Step 21 PR once Step 19 is on `main`.
4. Open the Step 23 PR once Step 21 is on `main`.
5. Start Step 22 next. Its real data is ready, apart from the AI explanations in Step 16.

## Work done

### Step 18 · Web scaffold and design system (2026-11-06)

**Built**

- `apps/web`: Vite, React, strict TypeScript, Tailwind, shadcn/ui, Geist Sans and Geist Mono.
- Design tokens in `src/styles/tokens.css`, owner colours in `src/lib/tokens.ts`, format helpers in `src/lib/format.ts`.
- App shell: left rail, top bar, project switcher, ⌘K palette, routes with placeholder pages, 404 and error pages.
- API client, `pnpm gen:api`, and MSW mocks behind `VITE_USE_MOCKS=true`: 8 members and 25 tasks of "Campus Food-Ordering App".
- `/styleguide` page for the team to judge the look.
- `make web` starts the app. `make lint` and `make test` now cover the web app.

**Checked**

- Typecheck, lint, 7 format tests and build pass from a clean install.
- Tested in a browser at 1440px and 375px.

**Decisions**

- TypeScript is pinned to 5.9, because `openapi-typescript` crashes on TypeScript 7.
- In Tailwind classes, `brand` is the blue `--accent` token. `accent` is shadcn's hover surface.
- `src/lib/api/provisional.ts` held temporary hand-written types until Step 05 existed. Step 19 deleted it.
- Added Vitest early, because the Makefile said web tests join in Step 18.

### Step 04 · Seed data (2026-11-06)

**Built**

- `apps/api/app/seed.py`, run with `make seed`: 14 skills, 8 members, 5 epics, 25 tasks, 28 dependencies, 17 assignments, 10 working-day snapshots.
- Demo roles: Bob is Aarav Mehta, Eva is Diya Nair, Alice is Kabir Singh.
- `apps/api/tests/test_seed.py`: 12 tests, including that seeding twice gives identical data.

**Checked**

- Measured with Manveer's unmerged engines: P(on time) 81.9%, SPI 0.94, CPI 1.05, critical path through Ordering & Payments.
- 26 API tests pass with Postgres. Without it, 12 pass and 6 skip.
- Running `make seed` twice gave identical task, assignment and snapshot rows.

**Decisions**

- Critical path is about 250 hours, not the mock's 155, so SPI can land just below 1 at week 3.
- T-012 is blocked at 0% but already owned by Aarav, so his leave reaches the critical path.
- Budget is ₹5,20,000, because the planned work totals about ₹4.6 lakh.
- Tuned the data only. The engines are unchanged.

### Step 19 · Projects list and overview (2026-11-06)

**Built**

- `/projects` table: deadline, progress, P(on time), SPI and open risks.
- `/projects/:id`: header, 6 KPIs with formula tooltips, S-curve, next critical tasks and top risks.
- Skeleton, empty and error states for every section.
- The app now runs on the real API with generated types. The temporary mock data is gone.
- `make seed` now runs risk detection, so the demo starts with 4 open risks.

**Checked**

- Typecheck, lint, 20 web tests and build pass. All 168 API tests pass.
- Tested on real data at 1440px and 390px, including an empty project, a missing project and the API being down.

**Decisions**

- No `owner` column, because the project table has no owner field.
- Only SPI and CPI show a change, because only they have snapshot history.
- An empty project shows no metrics. The forecast engine reports 100% on time for it, which would mislead.
- Recharts loads only on pages with a chart.

### Step 21 · Network graph and Gantt (2026-11-06)

**Built**

- `/projects/:id/schedule` with Network and Gantt tabs, on real data.
- Network: dependency graph with the critical path highlighted and a critical-only toggle.
- Gantt: grouped by epic, owner colours, hatched slack, today and deadline lines, weekend shading, Day and Week zoom, and dependency lines on hover.
- Task details open from either view.
- The header shows when the finish is past the deadline: currently 4 working days.

**Checked**

- Typecheck, lint, 45 web tests and build pass.
- Tested on real data at 1440px and 390px, including an empty project and a missing project.
- Only tested with 25 tasks, not the 50 in the brief.

**Decisions**

- Branched from Step 19, because Step 21 builds on it and PR #5 is still waiting.
- The network opens at a readable zoom instead of fitting everything.
- Added a deadline line, which the brief did not ask for, so the overrun is visible.

### Step 23 · Risk, EVM and forecast views (2026-11-06)

**Built**

- `/projects/:id/risks`: P×I matrix with click-to-filter, risk register, and a detail sheet with evidence and the RMMM plan.
- `/projects/:id/control`: 8 EVM KPIs, S-curve, P(on time), finish-date histogram, CDF with P50, P80 and P95, and the top tasks by criticality.
- Control is now in the left rail and the ⌘K palette.

**Checked**

- Typecheck, lint, tests and build pass.
- Tested on real data at 1440px and 390px, including an empty project and a missing project.
- The plan display was tested with one faked response, because the endpoint is not on `main`. The mock handler itself has not run.

**Decisions**

- Generate plan is built to the Step 16 format. On the real API it shows a clear message until Step 16 merges.
- Owner role comes from the RMMM plan, so it is empty until a plan exists.

## Future requirements

### For my next steps

- **After Step 17:** retune the seed so "Bob on leave" lands near the plan.md §4 numbers: 47%, then about 74% after approval.
- **After Step 16 merges:** run `pnpm gen:api`, test Generate plan, and delete its mock handler.
- **Step 27:** add the `g p` and `?` shortcuts, and fix the 543 kB main JS chunk with route-level code splitting.
- **After API changes:** run `pnpm gen:api` and fix any type errors.

### Questions for the team

- [ ] **Manveer:** merge Step 16, then Generate plan can be tested on the real API. The `rmmm` format is settled by that branch.
- [ ] **Team:** should projects have an owner? The Step 19 brief lists an owner column, but the project table has no such field.
- [ ] **Priyanshu:** `ruff check` fails at `app/agents/llm.py:12` (line too long), which will fail CI in Step 25.
- [ ] **Manveer, Priyanshu:** `forecast()` reads only tasks, so it ignores members, leave and progress. "Bob on leave" cannot drop P(on time) from 81% to 47% until Step 17 feeds leave into it.
- [ ] **Manveer:** Monte Carlo gives 82% on time for a 2026-12-01 deadline, but the scheduler finishes on 2026-12-07 because it rounds tasks to whole days. Which number should the demo show?
- [ ] **Manveer:** which `score_breakdown` shape should be stored? The seed follows the Step 03 model comment (`score`), but the assignment engine uses `total` and more fields.
- [ ] **Priyanshu:** does a newer `docs/temp.md` exist? The copy in git history stops at Step 02.

### Setup notes

- On Node 26, corepack's pnpm crashes. Install pnpm with `npm i -g pnpm`.
- Port 5432 is used by my `agentos` containers, so OrchestrAI's database runs on 5433. Export `POSTGRES_PORT=5433` and a matching `DATABASE_URL` before `make db-up` or `make seed`.
- `make seed` wipes every OrchestrAI table in the database at `DATABASE_URL`.
- The web app now needs the API running: `make api`, then `make web`.
- `PLAN.md`, `prompts.md` and `docs/temp.md` stay out of git. The team removed the plan and build log from the repo on purpose.
