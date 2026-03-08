# Multi-stage build for minimal production image
# Based on https://docs.astral.sh/uv/guides/integration/docker/

# Build stage: install dependencies and build the package
FROM python:3.13-alpine AS builder

# Install uv
RUN pip install --no-cache-dir uv==0.10.9

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1

# Disable dev dependencies and cache for smaller image
ENV UV_NO_DEV=1
ENV UV_NO_CACHE=1

# Set up working directory
WORKDIR /app

# Copy the project files needed for building
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src

# Build and install the package
RUN uv sync --locked --no-editable

# Final stage: minimal Alpine runtime image
FROM python:3.13-alpine

# Copy only the virtual environment from builder (no source code)
COPY --from=builder /app/.venv /app/.venv

# Activate the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Set entrypoint for CLI
ENTRYPOINT ["grokipedia"]
CMD ["--help"]
