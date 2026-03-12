# syntax=docker/dockerfile:1.4
FROM python:3.13-slim AS builder
 
# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9.18 /uv /uvx /bin/
 
WORKDIR /application
ENV PYTHONPATH=/application
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
 
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
 
 
# Includes dev dependencies (pytest, etc.)
FROM builder AS test
 
COPY --from=ghcr.io/astral-sh/uv:0.9.18 /uv /uvx /bin/
 
# Install all deps including dev
RUN uv sync --dev --frozen
 
COPY tests /tests
WORKDIR /application
CMD ["/application/.venv/bin/pytest", \
     "/tests/", \
     "-v", \
     "-c", "/application/pyproject.toml"]

FROM python:3.13-slim AS production
 
WORKDIR /application
COPY --from=builder /application /application
ENV PYTHONPATH=/application
EXPOSE 8000
 
CMD ["/application/.venv/bin/fastapi", "run", "application/app/main.py", "--port", "8000", "--host", "0.0.0.0"]
