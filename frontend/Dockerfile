FROM node:22-bookworm-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

# Railway variables used by Vite must be declared in the build stage.
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build


FROM node:22-bookworm-slim AS runtime

ENV NODE_ENV=production
WORKDIR /app

COPY --from=build --chown=node:node /app/dist ./dist
COPY --chown=node:node package.json server.js ./

USER node
EXPOSE 4173

CMD ["node", "server.js"]
