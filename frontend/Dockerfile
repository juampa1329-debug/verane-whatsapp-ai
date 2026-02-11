# Build Stage
FROM node:20-bookworm-slim AS build
WORKDIR /app

# Necesario para que se instalen devDependencies (vite) durante el build
ENV NODE_ENV=development
# Evita que npm omita optional deps (rolldown bindings)
ENV npm_config_optional=true
# Memoria extra por si el bundle crece
ENV NODE_OPTIONS="--max-old-space-size=4096"

COPY package*.json ./

# Fuerza dev + optional (bindings nativos)
RUN npm ci --include=dev --include=optional

COPY . .

RUN npm run build

# Serve Stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# SPA fallback
RUN printf '%s\n' \
'server {' \
'  listen 80;' \
'  server_name _;' \
'  root /usr/share/nginx/html;' \
'  index index.html;' \
'  location / { try_files $uri $uri/ /index.html; }' \
'}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
