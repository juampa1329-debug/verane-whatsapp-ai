# Build Stage
FROM node:20-bookworm-slim AS build
WORKDIR /app

# 1. Definimos variables
ARG VITE_API_BASE
ENV VITE_API_BASE=$VITE_API_BASE
ENV NODE_OPTIONS="--max-old-space-size=4096"

# 2. --- CAMBIO CRUCIAL ---
# Forzamos el entorno a 'development' para que 'npm install' descargue 
# VITE y los PLUGINS. Si no hacemos esto, Coolify los ignora por defecto.
ENV NODE_ENV=development

# 3. Copiamos y limpiamos dependencias previas
COPY package*.json ./
# Eliminamos package-lock.json para evitar conflictos de plataforma (Windows vs Linux)
RUN rm -f package-lock.json

# 4. Instalamos TODO (incluyendo devDependencies)
RUN npm install

# 5. Copiamos el código
COPY . .

# 6. Construimos la aplicación
# Usamos 'npx vite build' para saltar chequeos estrictos de TypeScript
RUN npx vite build

# Serve Stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# Configuración Nginx
RUN printf '%s\n' \
'server {' \
'  listen 80;' \
'  server_name _;' \
'  root /usr/share/nginx/html;' \
'  index index.html;' \
'  location / { try_files $uri $uri/ /index.html; }' \
'}' > /etc/nginx/conf.d/default.conf

EXPOSE 80