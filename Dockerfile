# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SOCCERDATA_LOGLEVEL=INFO

WORKDIR /app

# Install runtime deps and Poetry
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir poetry

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    POETRY_NO_ANSI=1

# Install deps first (layer caching)
COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --no-root

# Copy source and install project
COPY scouting scouting
RUN poetry install

# Create scripts directory and make scripts executable
COPY scripts scripts
RUN chmod +x scripts/*.sh scripts/*.py

# Create soccerdata config directory and copy league config in root and tmp (debug railway)
RUN mkdir -p /root/soccerdata/config
COPY config/league_dict.json /root/soccerdata/config/league_dict.json

EXPOSE 8000

CMD ["uvicorn", "scouting.api.main:app", "--host", "::", "--port", "8000", "--workers", "2", "--log-level", "info"]
