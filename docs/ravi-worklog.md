# Ravi's work log

Ravi Kumawat's steps on OrchestrAI (frontend, seed data, docs): what is done, what is next, and what each step is waiting for.

Update this file at the end of every step. `docs/temp.md` stays the detailed, local build log.

**Last updated:** 2026-11-06

## Where things stand

| Step | Work | Status | Waiting for |
|---|---|---|---|
| 18 | Web scaffold and design system | Done, on `feat/18-web-scaffold`, not merged | PR review by a teammate |
| 04 | Seed data | Ready to start | Docker running on my machine |
| 19 | Projects list and overview | Next after 18 merges | 18 merged. Real data needs 05–11; mocks until then |
| 21 | Network graph and Gantt | Not started | 19. Real data needs 07, 09 |
| 20 | New project flow | Not started | Mock SSE until 15 merges |
| 22 | Team and assignment views | Not started | Mocks until 08, 09, 16 merge |
| 23 | Risk, EVM and forecast views | Not started | Mocks until 10, 11, 12, 16 merge |
| 24 (UI) | Disruption simulator, approvals, audit | Blocked | 17 and Priyanshu's Step 24 API work merged |
| 27 | Docs, polish, deploy | Blocked | 26 merged |

**Team progress on 2026-11-06**

- On `main`: Steps 01, 02, 03.
- Pushed by Manveer, not merged: Steps 06, 07, 08. They touch only API files, so they do not overlap with Step 18.
- Not started on GitHub: Step 05 (CRUD APIs).

## Next actions

1. Get Step 18 reviewed and merged.
2. Start Docker Desktop, then do Step 04 on `feat/04-seed-data`, branched from `main`. Priyanshu's Step 05 can use it for manual testing.
3. Do Step 19 on `feat/19-overview`, branched from `main` after Step 18 merges.

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

## Future requirements

### For my next steps

- **Step 04:** reuse the mock member names and tasks in the seed, or update `src/lib/api/mocks/data.ts`, so screens and demos match. Seed numbers must land near the plan.md §4 demo story: P(on time) about 81%, SPI just below 1.
- **Step 19:** build the projects table and overview with skeleton, empty and error states. Check at 1440px and 390px.
- **Step 23:** add `/projects/:id/control` and decide where it sits in the left rail.
- **Step 27:** add the `g p` and `?` shortcuts, and fix the 520 kB main JS chunk with route-level code splitting.
- **After Step 05 merges:** run `pnpm gen:api`, delete `provisional.ts`, and remove mocks for endpoints that now exist.

### Questions for the team

- [ ] **Priyanshu, Manveer:** agree one `risk.rmmm` format before Step 23. The Step 03 model says `mitigation, monitoring, management`; the Step 16 prompt says `mitigation, monitoring_trigger, contingency, owner_role`.
- [ ] **Priyanshu:** confirm Step 05 list responses are `{items, total, limit, offset}`, money is a string, and `/members` includes `skills` and `availability`. The mocks assume all three.
- [ ] **Priyanshu:** does a newer `docs/temp.md` exist? The copy in git history stops at Step 02.

### Setup notes

- On Node 26, corepack's pnpm crashes. Install pnpm with `npm i -g pnpm`.
- Without a backend, run `pnpm dev:mock`, or copy `.env.example` to `.env` before `pnpm dev` or `make web`.
- `PLAN.md`, `prompts.md` and `docs/temp.md` stay out of git. The team removed the plan and build log from the repo on purpose.
