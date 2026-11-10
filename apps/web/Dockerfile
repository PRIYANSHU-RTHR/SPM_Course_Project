# syntax=docker/dockerfile:1
# OrchestrAI web: pnpm build, then nginx (non-root) serves the static files.
# The API URL is a runtime setting: API_URL becomes /config.js when the container starts.

FROM node:22-slim AS build
# Same pnpm as "packageManager" in package.json.
RUN npm install --global pnpm@12.18.0
WORKDIR /web
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,id=pnpm-store,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM nginxinc/nginx-unprivileged:1.30-alpine AS runtime
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --chmod=0755 docker/40-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
COPY --from=build /web/dist /usr/share/nginx/html
ENV API_URL=http://localhost:8000
EXPOSE 8080
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=12 \
    CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
