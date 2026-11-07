# OrchestrAI web

React, TypeScript, Vite, Tailwind and shadcn/ui.

```bash
pnpm i
pnpm dev        # needs the API on VITE_API_URL, seeded with `make seed`
pnpm dev:mock   # same, plus browser mocks for endpoints the API lacks
pnpm gen:api    # regenerate src/lib/api/types.ts from a running API
pnpm typecheck && pnpm lint && pnpm test && pnpm build
```

- `VITE_*` settings are read from the repo-root `.env`.
- In Tailwind classes, `brand` is the blue `--accent` token. `accent` is shadcn's hover surface.
- `/styleguide` shows the tokens and shared components.
