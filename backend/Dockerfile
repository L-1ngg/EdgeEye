# EdgeEye backend image (member 4 deliverable).
# Uses uv for dependency management to match the local dev workflow.
FROM python:3.11-slim

# Install uv (fast Python package manager).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first for better layer caching. The app is copied below,
# so dependency sync should not try to install the local project package here.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source.
COPY app ./app

# Persisted data, uploads and reports live under these dirs;
# mount them as volumes in docker-compose to keep data across restarts.
ENV EDGEEYE_DATABASE_PATH=data/edgeeye.db \
    EDGEEYE_UPLOADS_DIR=uploads \
    EDGEEYE_REPORTS_DIR=reports

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
