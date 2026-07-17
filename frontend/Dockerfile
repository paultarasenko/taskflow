# syntax=docker/dockerfile:1

# ---------- Build ----------
FROM node:22-alpine AS build

WORKDIR /app

# Кэш npm-слоя не инвалидируется при изменении исходников, только при
# изменении package*.json.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# ВАЖНО: Vite встраивает import.meta.env.VITE_* в бандл на этапе build,
# а не читает их в рантайме контейнера. Поэтому "передача API base URL
# через env" здесь реализована как build-arg — один образ соответствует
# одному API-URL. Раннтайм-инъекция через entrypoint (envsubst в index.html
# + window.__ENV__) позволила бы переиспользовать один образ для нескольких
# окружений, но это лишняя сложность для портфолио-масштаба — сознательно
# не реализовано, см. Roadmap в docs/01-architecture-and-design.md.
ARG VITE_API_URL=http://localhost:8000/api/v1
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ---------- Runtime ----------
FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# nginx:alpine основан на busybox — wget есть из коробки, curl ставить не нужно.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
