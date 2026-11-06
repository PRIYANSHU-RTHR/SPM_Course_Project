# Ravi's work log

Ravi Kumawat's steps on OrchestrAI (frontend, seed data, docs): what is done, what is next, and what each step is waiting for.

Update this file at the end of every step. `docs/temp.md` stays the detailed, local build log.

**Last updated:** 2026-11-06

## Where things stand

| Step | Work | Status | Waiting for |
|---|---|---|---|
| 18 | Web scaffold and design system | Done, in [PR #1](https://github.com/PRIYANSHU-RTHR/SPM_Course_Project/pull/1), not merged | PR review by a teammate |
| 04 | Seed data | Done, on `feat/04-seed-data`, no PR yet | PR and review |
| 19 | Projects list and overview | Next after 18 merges | 18 merged. Real data needs 05–11; mocks until then |
| 21 | Network graph and Gantt | Not started | 19. Real data needs 07, 09 |
| 20 | New project flow | Not started | Mock SSE until 15 merges |
| 22 | Team and assignment views | Not started | Mocks until 08, 09, 16 merge |
| 23 | Risk, EVM and forecast views | Not started | Mocks until 10, 11, 12, 16 merge |
| 24 (UI) | Disruption simulator, approvals, audit | Blocked | 17 and Priyanshu's Step 24 API work merged |
| 27 | Docs, polish, deploy | Blocked | 26 merged |

**Team progress on 2026-11-06**

- On `main`: Steps 01, 02, 03.
- Pushed by Manveer, not merged: Steps 06 to 11. They do not overlap with Step 18, and the Step 04 changes apply cleanly on them.
- Not started on GitHub: Step 05 (CRUD APIs).

## Next actions

1. Get Step 18 reviewed and merged.
2. Open a PR for Step 04. Priyanshu's Step 05 can use the seed for manual testing.
3. Raise the two engine problems under "Questions for the team". They affect the demo story.
4. Do Step 19 on `feat/19-overview`, branched from `main` after Step 18 merges.

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
- `src/lib/api/provisional.ts` holds temporary hand-written types until Step 05 exists.
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

## Future requirements

### For my next steps

- **Step 19:** build the projects table and overview with skeleton, empty and error states. Check at 1440px and 390px.
- **Step 19:** update `src/lib/api/mocks/data.ts` to match the seed: hours, statuses, skills, assignments and budget.
- **After Step 17:** retune the seed so "Bob on leave" lands near the plan.md §4 numbers: 47%, then about 74% after approval.
- **Step 23:** add `/projects/:id/control` and decide where it sits in the left rail.
- **Step 27:** add the `g p` and `?` shortcuts, and fix the 520 kB main JS chunk with route-level code splitting.
- **After Step 05 merges:** run `pnpm gen:api`, delete `provisional.ts`, and remove mocks for endpoints that now exist.

### Questions for the team

- [ ] **Priyanshu, Manveer:** agree one `risk.rmmm` format before Step 23. The Step 03 model says `mitigation, monitoring, management`; the Step 16 prompt says `mitigation, monitoring_trigger, contingency, owner_role`.
- [ ] **Priyanshu:** confirm Step 05 list responses are `{items, total, limit, offset}`, money is a string, and `/members` includes `skills` and `availability`. The mocks assume all three.
- [ ] **Manveer, Priyanshu:** `forecast()` reads only tasks, so it ignores members, leave and progress. "Bob on leave" cannot drop P(on time) from 81% to 47% until Step 17 feeds leave into it.
- [ ] **Manveer:** Monte Carlo gives 82% on time for a 2026-12-01 deadline, but the scheduler finishes on 2026-12-07 because it rounds tasks to whole days. Which number should the demo show?
- [ ] **Priyanshu:** does a newer `docs/temp.md` exist? The copy in git history stops at Step 02.

### Setup notes

- On Node 26, corepack's pnpm crashes. Install pnpm with `npm i -g pnpm`.
- Port 5432 is used by my `agentos` containers, so OrchestrAI's database runs on 5433. Export `POSTGRES_PORT=5433` and a matching `DATABASE_URL` before `make db-up` or `make seed`.
- `make seed` wipes every OrchestrAI table in the database at `DATABASE_URL`.
- Without a backend, run `pnpm dev:mock`, or copy `.env.example` to `.env` before `pnpm dev` or `make web`.
- `PLAN.md`, `prompts.md` and `docs/temp.md` stay out of git. The team removed the plan and build log from the repo on purpose.
