# syntax=docker/dockerfile:1

FROM node:22.23.1-bookworm-slim AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM dependencies AS development
ENV NODE_ENV=development
COPY . .
RUN install -d -o node -g node /app/.next
USER node
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=5s --start-period=45s --retries=5 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"]
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]

FROM dependencies AS builder
COPY . .
RUN mkdir -p public \
    && npm run lint \
    && npm run build

FROM node:22.23.1-bookworm-slim AS production-dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

FROM node:22.23.1-bookworm-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder --chown=node:node /app/package.json /app/package-lock.json ./
COPY --from=production-dependencies --chown=node:node /app/node_modules ./node_modules
COPY --from=builder --chown=node:node /app/.next ./.next
COPY --from=builder --chown=node:node /app/public ./public
USER node
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"]
CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "3000"]
