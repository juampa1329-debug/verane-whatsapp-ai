# Build Stage
FROM node:20-bookworm-slim AS build
WORKDIR /app

# Aumentamos la memoria de Node para evitar fallos
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Copiamos package.json
COPY package*.json ./

# IMPORTANTE: Usamos 'npm install' en lugar de 'npm ci' para corregir el error de Linux/Windows
RUN npm install

# Copiamos el resto del código
COPY . .

# Ejecutamos el build
RUN npm run build

# Serve Stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# Configuración Nginx para que funcione la navegación de la app
RUN printf '%s\n' \
'server {' \
'  listen 80;' \
'  server_name _;' \
'  root /usr/share/nginx/html;' \
'  index index.html;' \
'  location / { try_files $uri $uri/ /index.html; }' \
'}' > /etc/nginx/conf.d/default.conf

EXPOSE 80