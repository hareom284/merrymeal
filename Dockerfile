# Stage 1 — Build Tailwind CSS
FROM node:20-alpine AS css-builder
WORKDIR /build
COPY package.json package-lock.json tailwind.config.js ./
COPY static/src ./static/src
COPY templates ./templates
RUN npm ci && npm run build:css

# Stage 2 — Python runtime
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.dev

# System deps: mysqlclient build chain + curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        pkg-config \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY . .

# Bring in compiled CSS from stage 1
COPY --from=css-builder /build/static/dist ./static/dist

# Entrypoint
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
