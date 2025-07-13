# Multi-stage Docker build for Local AI Agent Enterprise System
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --upgrade pip

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install additional development tools
RUN pip install pytest pytest-asyncio black flake8 mypy

# Copy source code
COPY . .

# Expose development ports
EXPOSE 8000 8001 8080

# Development command
CMD ["python", "examples/api_gateway_demo.py"]

# Production build stage
FROM base as builder

# Install build dependencies
RUN pip install --upgrade pip build wheel

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Copy source code and build package
COPY . .
RUN python -m build --wheel

# Production stage
FROM python:3.11-slim as production

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH" \
    ENVIRONMENT=production

# Create non-root user
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --home-dir /home/appuser --create-home appuser

# Install production system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Switch to non-root user
USER appuser
WORKDIR /home/appuser

# Copy installed packages from builder
COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appgroup . /home/appuser/app
WORKDIR /home/appuser/app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports
EXPOSE 8000

# Production command
CMD ["python", "-m", "uvicorn", "src.agent.api.gateway:create_api_gateway", "--host", "0.0.0.0", "--port", "8000", "--factory"]

# Monitoring stage (includes observability tools)
FROM production as monitoring

USER root

# Install monitoring dependencies
RUN apt-get update && apt-get install -y \
    prometheus-node-exporter \
    && rm -rf /var/lib/apt/lists/*

# Install Python monitoring packages
RUN pip install --user prometheus-client opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi

USER appuser

# Expose monitoring ports
EXPOSE 8000 9090 9464

# Monitoring command with metrics
CMD ["python", "-m", "uvicorn", "src.agent.api.gateway:create_api_gateway", "--host", "0.0.0.0", "--port", "8000", "--factory", "--access-log"]