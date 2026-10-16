FROM node:22-alpine

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
EXPOSE 3000
# Inside the container the dev server must listen on every interface or the published port would not
# reach it; docker-compose.yml publishes it on 127.0.0.1 of the host only.
CMD ["npm", "run", "dev:lan"]
