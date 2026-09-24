# Dockerfile
# Purpose: Container image for the CloudDesk Next.js frontend (Phase 10, spec section 27/31 —
#          added this phase; none existed before). Multi-stage: dependencies + production build in
#          a throwaway builder stage, then only the `output: "standalone"` trace (see
#          next.config.ts) copied into a minimal runtime stage — no dev dependencies, no full
#          node_modules, and a non-root runtime user.
# Author: CloudDesk Team
# Date: 2026-09-24

FROM node:22-slim AS deps

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci


FROM node:22-slim AS builder

WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# The API base URL is a public, build-time-inlined value (see lib/api/client.ts); the real
# runtime value for a given deployment is passed as a build arg, defaulting to the docker-compose
# service name so `docker compose up` works out of the box.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
RUN npm run build


FROM node:22-slim AS runtime

RUN groupadd --system clouddesk && useradd --system --gid clouddesk --create-home clouddesk

WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

RUN chown -R clouddesk:clouddesk /app
USER clouddesk

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "fetch('http://localhost:3000/login').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
