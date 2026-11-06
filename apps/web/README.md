# OrchestrAI web

React, TypeScript, Vite, Tailwind and shadcn/ui.

```bash
pnpm i
pnpm dev:mock   # no API needed: serves mock data from the browser
pnpm dev        # uses VITE_API_URL
pnpm gen:api    # regenerate src/lib/api/types.ts from a running API
pnpm typecheck && pnpm lint && pnpm test && pnpm build
```

- `VITE_*` settings are read from the repo-root `.env`.
- In Tailwind classes, `brand` is the blue `--accent` token. `accent` is shadcn's hover surface.
- `/styleguide` shows the tokens and shared components.
