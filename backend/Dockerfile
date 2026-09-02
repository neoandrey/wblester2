# syntax=docker/dockerfile:1
#
# WBLESTER admin SPA (Flutter backend) - packaged as a self-contained image.
# Stage 1: compile the Flutter web bundle for the /admin/ base path.
# Stage 2: nginx serves the compiled bundle and proxies everything else
# (the JSON API, public website, uploads) to the webapi service, so the
# browser keeps a single origin. The web port follows the PORT env var
# (default 5454); nginx reads the webapi upstream port from the
# WBLESTER_API_PORT env var via the image's built-in envsubst templating.

FROM ghcr.io/cirruslabs/flutter:stable AS build

WORKDIR /app

COPY pubspec.yaml pubspec.lock ./
RUN flutter pub get

COPY . .

ARG ADMIN_BASE_HREF=/admin/
ARG API_BASE=
RUN flutter build web \
    --base-href=${ADMIN_BASE_HREF} \
    --dart-define=API_BASE=${API_BASE} \
    --release \
    --no-wasm-dry-run

FROM nginx:1.27-alpine

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/build/web /usr/share/nginx/html/admin

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO /dev/null http://127.0.0.1/health || exit 1