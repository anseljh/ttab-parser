FROM python:3.14-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency manifest first for layer caching
COPY pyproject.toml .

# Install project dependencies (no dev extras)
RUN uv sync --no-dev

# Copy source code
COPY src/ ./src/
