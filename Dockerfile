# === Build stage ===
FROM python:3.12-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libxml2-dev \
        libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install dependencies first (layer caching)
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

# Copy source and install the project
COPY . .
RUN pip install --no-cache-dir --prefix=/install .


# === Runtime stage ===
FROM python:3.12-slim

# Runtime libraries for lxml
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libxml2 \
        libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash mcpuser

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create directories for data mounts
RUN mkdir -p /data/platform /data/json && \
    chown -R mcpuser:mcpuser /data

USER mcpuser
WORKDIR /home/mcpuser

# Default environment variables for Docker (Streamable HTTP mode)
ENV MCP_BSL_MODE=streamable-http
ENV MCP_BSL_PORT=8080
ENV MCP_BSL_DATA_SOURCE=hbk
ENV MCP_BSL_PLATFORM_PATH=/data/platform
ENV MCP_BSL_JSON_PATH=/data/json

EXPOSE 8080

# Health check: verify the server port is accepting connections
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import socket; s=socket.create_connection(('localhost', 8080), timeout=5); s.close()"

ENTRYPOINT ["mcp-bsl-context"]
