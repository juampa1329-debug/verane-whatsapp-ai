# Build stage
FROM node:22-bookworm-slim AS build
WORKDIR /app

# 1) Build args/env
ARG VITE_API_BASE
ENV VITE_API_BASE=$VITE_API_BASE
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Keep dev dependencies for Vite build
ENV NODE_ENV=development

# 2) Install dependencies deterministically (including optional native bindings)
COPY package.json package-lock.json ./
RUN npm ci --include=dev --include=optional --no-audit --no-fund

# 3) Copy source
COPY . .

# 4) Build frontend
RUN node -v && npm -v
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# Nginx config
RUN printf '%s\n' \
'server {' \
'  listen 80;' \
'  server_name _;' \
'  root /usr/share/nginx/html;' \
'  index index.html;' \
'  location / { try_files $uri $uri/ /index.html; }' \
'}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
