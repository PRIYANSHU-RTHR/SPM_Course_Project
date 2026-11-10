# Demo script (5 minutes)

The plan.md §4 story as a click path. All numbers were measured on `make demo` with the shipped seed (`SIM_SEED=42`) and `LLM_MODE=fixture`, on 2026-11-10. The seed is built relative to "today", so the dates move with the day you run it. The percentages and the shape of the story stay the same.

**Before you start**

- Run `make demo`. It reseeds, so it is also the reset between rehearsals. Open http://localhost:8080 at 1440 px wide.
- No API key is needed. AI steps replay recorded replies, and every number on screen comes from an engine.
- Shortcuts: `?` lists them, `g p` projects, `g o` overview, `g a` approvals, `g l` audit log.

---

## 1. Brief → plan (60 s)

1. Left rail → **Plan** (or `g n`). Click **Use the demo brief**. The form fills with "Campus Food-Ordering App v2", the brief, start next Monday, a deadline 16 weeks later and a budget of ₹9,00,000.
2. Click **Generate plan**. The run page opens.
3. Point at the **Run** timeline as it streams: *Decompose brief → Validate WBS → Estimate → Schedule → Assign owners → PM review*. Each step shows its duration and a one-line summary, e.g. "25 tasks in 5 epics drafted" and "24/25 tasks matched".

**Say:** "A LangGraph workflow, checkpointed in Postgres, streaming over SSE. It pauses for me; nothing is saved until I approve."

## 2. Review (45 s)

1. KPI row: effort **341.7 h**, cost **₹2,90,417**, COCOMO II **11.4 PM** (hover for the formula and the bottom-up comparison), the finish date, and **1 unassigned** task (amber).
2. Read the warnings: the skill names the validator normalised (`reactjs → react`), and the task nobody on the team is eligible for.
3. In **Work breakdown**, change T-001's *m* to an invalid value (e.g. above *p*): the row explains the rule `1 ≤ o ≤ m ≤ p ≤ 80`. Fix it, change a skill level, and click **Request changes (2)**. The timeline adds a second *Estimate → Schedule → Assign owners → PM review* pass, and the footer shows **Revision 1**.
4. Click **Approve plan**. The project is created, with its tasks, dependencies and owners. Each assignment is written to the audit log.

**Say:** "The model only proposed the structure and the three-point inputs. te, cost, dates and owners are engine output, and my edits are re-estimated before I approve."

## 3. Plan health (45 s)

Switch to the seeded project: project switcher → **Campus Food-Ordering App** (`g o`).

1. **Overview:**
   - P(on time) **82%**, SPI **0.94**, CPI **1.05**, 4 open risks.
   - The S-curve, and the next critical tasks.
2. **Schedule** (`g s`):
   - Network tab: the critical path in blue, with slack on each node.
   - Gantt tab: bars in owner colours, a hatched slack tail, and the today and deadline lines.
3. **Team** (`g t`): open a task to see its top three candidates with skill, capacity and balance bars, and the `Gemini · explanation` block.
   - With a key, the model's text is shown only if every number it cites is in the engine's input.
   - In fixture mode you see the deterministic template, badged *template*. Only the planning prompt has a recording.
4. **Control** (`g c`): the finish-date histogram and CDF with P50 / P80 / P95.

**Say:** "P(on time) is a 5,000-run Monte Carlo, adjusted for who owns what and who is away, the same number on every page."

## 4. Disruption (60 s)

1. **Approvals** (`g a`). The metrics strip shows **82%**, P80 **04 Dec**.
2. In the **Disruption simulator**, Leave tab:
   - Member **Aarav Mehta · Backend lead**.
   - Keep the default dates: tomorrow, for one week.
   - Reason "Family emergency".
3. Click **Record leave**.
4. The **Reallocation run** streams: *Record disruption → Recompute risks → Propose owners → PM approval*.
5. The proposal card appears. The KPI strip drops to **0%**, P80 **11 Dec**, and open risks go up.
6. Walk the card:
   - **Before disruption 82%** (P80 04 Dec) → **Now 0%** (P80 11 Dec) → **If approved 58% (+58 pts)** (P80 07 Dec).
   - The diff table, 6 tasks: T-012 *Payment gateway integration* moves from Aarav (struck through, on leave) to Diya Nair, with score 60 → 52 and finish 24 Nov → 17 Nov. Five unowned critical tasks get owners.
   - **Risks that would open:** a new bus-factor risk on Diya.

**Say:** "The engines re-plan only the affected tasks against everyone's other work. Every number here is engine output; the summary sentence is a template, not the model."

## 5. Approve (30 s)

1. Click **Approve 6 reassignments**.
2. Watch the KPI strip ease from **0% → 58%** (P80 11 Dec → 07 Dec).
3. The proposal moves to **Decided · approved · PM**.
4. **Audit** (`g l`): entries grouped by day, for example:
   - "PM recorded leave for Aarav Mehta …"
   - "PM approved reallocation proposal #…"
   - one "PM reassigned T-012 'Payment gateway integration' from Aarav Mehta to Diya Nair (AI recommendation)" line per task
   - the risk engine's opened and closed risks

**Say:** "Every PM action writes the audit log with actor, before, after and reason. That's our change-control trail."

## 6. Control (30 s)

1. Approvals → simulator → **Clock** tab → **+7 days**. The result line reads about: *5 working days, SPI 0.80, CPI 1.03, P(on time) 0%*.
2. **Control** (`g c`): the S-curve now runs a week further, with EV below PV.
3. **Risks** (`g r`): open the top risk. **Generate plan** adds an RMMM plan (mitigation, monitoring trigger, contingency, owner role), labelled `Gemini · RMMM plan` with a grounded / template badge (template in fixture mode).

**Say:** "A week at SPI 0.8 uses up the one day of buffer the 80% forecast had, so P(on time) falls. The risk register flags SPI and the deadline, and the risk agent drafts the response."

---

## If something goes wrong

| Symptom | Fix |
|---|---|
| Port 5432 / 8000 / 8080 in use | `POSTGRES_PORT=5433 make demo API_PORT=8001 WEB_PORT=8081` |
| "No LLM fixture for prompt 'planning'" | The brief was edited: click **Use the demo brief** again (only that brief is recorded) |
| A proposal is already waiting | Approve or reject it first; one reallocation per project at a time |
| Numbers differ from this script | Run `make demo` again to reseed, then repeat from step 1 |
