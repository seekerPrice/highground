# Build from web context: docker build -f web/Dockerfile -t highground-web web
FROM node:24.14.0-bookworm-slim@sha256:d8e448a56fc63242f70026718378bd4b00f8c82e78d20eefb199224a4d8e33d8 AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# HIGHGROUND_API_ORIGIN is deliberately absent during build; server reads it at runtime.
RUN npm run build && npm prune --omit=dev

FROM node:24.14.0-bookworm-slim@sha256:d8e448a56fc63242f70026718378bd4b00f8c82e78d20eefb199224a4d8e33d8
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=8080
WORKDIR /app
COPY --from=build --chown=node:node /app/package.json ./package.json
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/.next ./.next
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD node -e "fetch('http://127.0.0.1:'+process.env.PORT+'/',{signal:AbortSignal.timeout(3000)}).then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"
CMD ["sh", "-c", "exec node node_modules/next/dist/bin/next start --hostname 0.0.0.0 --port \"${PORT:-8080}\""]
