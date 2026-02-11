# Build Stage (Debian/glibc para evitar bindings musl)
FROM node:20-bookworm-slim AS build
WORKDIR /app

ENV NODE_OPTIONS="--max-old-space-size=4096"

COPY package*.json ./
RUN npm ci

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
