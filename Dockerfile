FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# Keep base image minimal but include bash for scripts.
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry (used by this repo).
RUN pip install --no-cache-dir poetry

# Install dependencies first for better layer caching.
COPY pyproject.toml poetry.lock /app/
RUN poetry install --no-root --only main

# Copy application code + migrations.
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY docker /app/docker

EXPOSE 8000

# Railway provides PORT; default to 8000 locally.
CMD ["bash", "docker/start.sh"]

