# Build Stage
FROM node:20-bookworm-slim AS build
WORKDIR /app

# Aumentamos la memoria para evitar fallos
ENV NODE_OPTIONS="--max-old-space-size=4096"

# IMPORTANTE: Forzamos entorno de desarrollo para instalar devDependencies (Vite)
ENV NODE_ENV=development

COPY package*.json ./
RUN npm ci

# Copiamos el código fuente (el .dockerignore evitará copiar node_modules)
COPY . .

# Construimos la aplicación
RUN npm run build

# Serve Stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# Configuración Nginx para SPA
RUN printf '%s\n' \
'server {' \
'  listen 80;' \
'  server_name _;' \
'  root /usr/share/nginx/html;' \
'  index index.html;' \
'  location / { try_files $uri $uri/ /index.html; }' \
'}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
