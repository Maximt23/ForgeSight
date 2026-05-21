# syntax=docker/dockerfile:1.6
# ----------------------------------------------------------------------
# CadOwl API — Production-grade multi-stage Dockerfile
#
# Stage 1 (builder): install Python deps in a virtualenv
# Stage 2 (runtime): copy venv + source, run as non-root user
#
# Build:    docker build -t cadowl-api:latest .
# Run:      docker run -p 9010:9010 --env-file .env cadowl-api:latest
# ----------------------------------------------------------------------

# ─── Build args ─────────────────────────────────────────────────────────
ARG PYTHON_VERSION=3.11-slim-bookworm

# ─── Stage 1: builder ──────────────────────────────────────────────────
FROM python:${PYTHON_VERSION} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps needed to build some Python packages (gdal for geopandas later,
# build-essential for cffi, etc.). Keep minimal.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only requirements first to maximize layer cache
COPY requirements.txt requirements.txt

# Create virtualenv and install deps
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

# ─── Stage 2: runtime ──────────────────────────────────────────────────
FROM python:${PYTHON_VERSION} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_HOME=/app \
    CADOWL_DATA_DIR=/data

# Runtime deps only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (security best practice — never run as root in prod)
RUN groupadd --system --gid 1001 cadowl \
    && useradd --system --uid 1001 --gid cadowl --home-dir /app --shell /bin/false cadowl

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
WORKDIR ${APP_HOME}
COPY --chown=cadowl:cadowl apps/ ./apps/
COPY --chown=cadowl:cadowl packages/ ./packages/
COPY --chown=cadowl:cadowl data/schemas/ ./data/schemas/
COPY --chown=cadowl:cadowl LICENSE AUTHORS.md README.md ./

# Create data directory (mounted as volume in production)
RUN mkdir -p ${CADOWL_DATA_DIR}/jsondb \
    && chown -R cadowl:cadowl ${CADOWL_DATA_DIR}

USER cadowl
EXPOSE 9010

# Health check — used by container orchestrator (k8s/ECS/etc.)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:9010/api/v1/health || exit 1

# Run with uvicorn directly. In production, you'd run multiple workers
# behind gunicorn — see docker-compose.yml for that pattern.
CMD ["uvicorn", "apps.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "9010", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
