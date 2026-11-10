# Production image: build once, then `next start`. Build context is the repository root
# (docker-compose.yml: build.context ".", dockerfile apps/web/Dockerfile).
#
# NEXT_PUBLIC_* values are compiled into the browser bundle by `next build`, so they are build
# arguments here, not run-time environment. Change one and the image must be rebuilt.

# ---- deps: install from the lock file, so every build gets the same versions ----
FROM node:22-alpine AS deps
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

# ---- build ----
FROM node:22-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/ .
# The one generated file the app imports from outside apps/web/
# (../../../../packages/shared/generated/locales.json, resolved from components/ui/).
COPY packages/shared/generated/locales.json /packages/shared/generated/locales.json

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_DEV_TOOLS=false
ARG NEXT_PUBLIC_PILOT_KEY=dev-pilot
ARG NEXT_PUBLIC_SKIP_LOGIN=false
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_DEV_TOOLS=$NEXT_PUBLIC_DEV_TOOLS \
    NEXT_PUBLIC_PILOT_KEY=$NEXT_PUBLIC_PILOT_KEY \
    NEXT_PUBLIC_SKIP_LOGIN=$NEXT_PUBLIC_SKIP_LOGIN \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---- run: only what `next start` needs, as a non-root user ----
FROM node:22-alpine AS run
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=build --chown=node:node /app/package.json ./
COPY --from=build --chown=node:node /app/next.config.ts ./
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/.next ./.next
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
CMD ["npm", "run", "start"]
