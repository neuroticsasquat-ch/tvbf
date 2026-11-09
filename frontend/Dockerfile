# syntax=docker/dockerfile:1.7
FROM node:22-alpine AS base
ENV CI=1 \
    PNPM_HOME=/root/.local/share/pnpm \
    PATH=/root/.local/share/pnpm:$PATH
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate
WORKDIR /app

FROM base AS deps
# The workspace manifest and its one member's package.json too (pnpm-workspace.yaml), or the
# frozen install finds a lockfile importer it has no package for.
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml ./
COPY tools/openapi-types/package.json tools/openapi-types/
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile || pnpm install

FROM base AS dev
COPY --from=deps /app/node_modules /app/node_modules
COPY . .
EXPOSE 5173
CMD ["pnpm", "dev", "--host", "0.0.0.0"]
