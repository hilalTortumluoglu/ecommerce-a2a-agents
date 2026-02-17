# ─────────────────────────────────────────────────────────────────────────────
# Base stage
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        "a2a-sdk[http-server]>=0.3.22" \
        "langgraph>=0.2.60" \
        "langchain>=0.3.0" \
        "langchain-openai>=0.3.0" \
        "langchain-core>=0.3.0" \
        "fastapi>=0.115.0" \
        "uvicorn[standard]>=0.32.0" \
        "httpx>=0.28.0" \
        "pydantic>=2.10.0" \
        "pydantic-settings>=2.6.0" \
        "mcp>=1.3.0" \
        "tavily-python>=0.5.0" \
        "structlog>=24.4.0" \
        "python-dotenv>=1.0.0" \
        "starlette>=0.41.0" \
        "typing-extensions>=4.12.0"

# Copy source code
COPY utils/ ./utils/
COPY data/ ./data/
COPY agents/ ./agents/
COPY mcp_server/ ./mcp_server/

# Create data directory
RUN mkdir -p /app/data

# Non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ─────────────────────────────────────────────────────────────────────────────
# MCP Server target
# ─────────────────────────────────────────────────────────────────────────────
FROM base AS mcp_server

EXPOSE 8090
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8090/health || exit 1

CMD ["python", "-m", "mcp_server.server"]

# ─────────────────────────────────────────────────────────────────────────────
# Generic agent target (CMD overridden per-service in docker-compose)
# ─────────────────────────────────────────────────────────────────────────────
FROM base AS agent

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=10s --retries=5 \
    CMD curl -f http://localhost:${AGENT_PORT:-8000}/.well-known/agent.json || exit 1

# Default: orchestrator (overridden in docker-compose)
CMD ["python", "-m", "agents.orchestrator.server"]
