# ==============================================================================
# IPRED Chatbot UIS - Frontend Dockerfile (Multi-stage Flutter Web -> Nginx)
# ==============================================================================

# Etapa 1: Compilación de Flutter Web
FROM ghcr.io/cirruslabs/flutter:stable AS build

WORKDIR /app

# Copiar configuración de dependencias
COPY pubspec.yaml pubspec.lock ./
RUN flutter pub get

# Copiar código fuente y compilar bundle de producción
COPY . .
RUN flutter build web --release --pwa-strategy=none --web-renderer canvaskit

# Etapa 2: Servidor Nginx Alpine ultra-liviano (< 25 MB)
FROM nginx:alpine AS runtime

COPY --from=build /app/build/web /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget -q --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
