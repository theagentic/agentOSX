# Multi-stage build for AgentOSX
FROM python:3.10-slim as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Production stage
FROM python:3.10-slim

# Set labels
LABEL maintainer="AgentOSX Team <team@agentosx.dev>"
LABEL version="0.1.0"
LABEL description="AgentOSX - Production-ready MCP-native agent framework"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AGENTOSX_ENV=production

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash agentosx

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/agentosx/.local

# Copy application code
COPY --chown=agentosx:agentosx . .

# Create necessary directories
RUN mkdir -p /app/agents /app/data /app/logs && \
    chown -R agentosx:agentosx /app

# Switch to non-root user
USER agentosx

# Add local bin to PATH
ENV PATH=/home/agentosx/.local/bin:$PATH

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health/live')" || exit 1

# Default command (can be overridden)
CMD ["python", "-m", "agentosx.mcp.server", "--transport", "sse", "--port", "8080"]
