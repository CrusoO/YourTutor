FROM node:22-alpine

WORKDIR /app

# Layer 1: dependencies — only reruns when package.json changes
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm install --prefer-offline

# Layer 2: app source
COPY apps/web/ .

# Layer 3: only the one generated file the app imports from outside apps/web/
# Resolves ../../../../packages/shared/generated/locales.json from components/ui/
COPY packages/shared/generated/locales.json /packages/shared/generated/locales.json

EXPOSE 3000
CMD ["npm", "run", "dev:lan"]
