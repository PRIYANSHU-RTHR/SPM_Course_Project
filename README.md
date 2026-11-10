# OrchestrAI

[![CI](https://github.com/PRIYANSHU-RTHR/SPM_Course_Project/actions/workflows/ci.yml/badge.svg)](https://github.com/PRIYANSHU-RTHR/SPM_Course_Project/actions/workflows/ci.yml)

AI-assisted software project management: brief → WBS → PERT/COCOMO estimates → CPM schedule → explainable assignment → Monte Carlo forecast → EVM and risk register → disruption-driven reallocation with PM approval.

## Run

You need Docker with Compose v2.17 or newer, and `make`. You don't need an API key, a `.env` file, Python or Node.

```bash
git clone https://github.com/PRIYANSHU-RTHR/SPM_Course_Project.git
cd SPM_Course_Project
make demo
```

`make demo` builds the images and starts Postgres, the API and the web app. It waits until all three are healthy, then runs the migrations and loads the demo project, "Campus Food-Ordering App". When it's done it prints the URLs:

| What     | URL                         |
|----------|-----------------------------|
| Web app  | http://localhost:8080       |
| API      | http://localhost:8000       |
| API docs | http://localhost:8000/docs  |

The demo runs with `LLM_MODE=fixture`: AI steps replay recorded model replies from `apps/api/fixtures/llm/`, so they need no key and give the same output every time. Every number on screen comes from the engines, not the model.

- **Reset:** run `make demo` again. It reloads the demo data, which wipes the demo database.
- **Stop:** `make demo-down`. The database volume is kept.
- **Port in use?** Override the ports, e.g. `POSTGRES_PORT=5433 make demo API_PORT=8001 WEB_PORT=8081`. The web app picks up the new API URL when its container starts.

### Local development

```bash
cp .env.example .env              # then edit if needed
make db-up && make seed           # Postgres in Docker, demo data
make api                          # API with reload on :8000 (needs uv)
make web                          # Vite dev server on :5173 (needs Node 22 + pnpm)
make lint && make test            # same checks as CI; `make cov` adds the coverage gate
```

### Recording LLM fixtures

Only needed after a prompt, a schema or the demo brief changes, because the old recording then no longer matches.

```bash
export GEMINI_API_KEY=...          # or put it in .env
make record-fixtures
```

This seeds the demo team and runs the demo brief through the planning workflow with `LLM_MODE=record`. It writes the reply to `apps/api/fixtures/llm/`; commit the new file. The model comes from `GEMINI_MODEL`, default `gemini-3.8-flash`.

