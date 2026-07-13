FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY package*.json ./
RUN npm ci --omit=dev
RUN addgroup --system --gid 1001 agentco && adduser --system --uid 1001 agentco
COPY --from=builder --chown=agentco:agentco /app/dist ./dist
COPY --from=builder --chown=agentco:agentco /app/src/db/migrations ./src/db/migrations
USER agentco
EXPOSE 3001
CMD ["node", "dist/server.js"]
