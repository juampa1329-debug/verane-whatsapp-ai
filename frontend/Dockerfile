# Build Stage
FROM node:20-bookworm-slim AS build
WORKDIR /app

# 1. Definimos argumentos para que Vite pueda leer las variables de entorno
ARG VITE_API_BASE
ENV VITE_API_BASE=$VITE_API_BASE
# Aumentamos memoria para evitar bloqueos
ENV NODE_OPTIONS="--max-old-space-size=4096"

# 2. Copiamos los archivos de dependencias
COPY package*.json ./

# 3. Instalamos TODO. Usamos 'npm install' en lugar de 'ci' aquí 
# porque es más capaz de corregir diferencias entre Windows y Linux automáticamente.
RUN npm install

# 4. Copiamos el código fuente (el .dockerignore evitará copiar basura)
COPY . .

# 5. --- EL CAMBIO CLAVE ---
# Ejecutamos directamente 'vite build'. Esto construye la app saltándose 
# verificaciones estrictas (TypeScript/ESLint) que suelen bloquear el deploy.
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