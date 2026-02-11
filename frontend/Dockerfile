# Build (usar Debian/glibc para evitar el bug de bindings en Alpine/musl)
FROM node:20-bookworm-slim AS build
WORKDIR /app

COPY package*.json ./

# Importante: asegurar optional deps (rolldown bindings) en Linux
RUN npm ci --include=optional

COPY . .
RUN npm run build

# Serve
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
