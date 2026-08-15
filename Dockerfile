FROM ghcr.io/astral-sh/uv:0.11.32-python3.13-trixie-slim
LABEL authors="sepinetam"

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN uv sync --no-dev

EXPOSE 5090

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD ["/app/.venv/bin/python", "-c", "import socket; socket.create_connection(('127.0.0.1', 5090), timeout=2).close()"]

ENTRYPOINT ["/app/.venv/bin/nber-cli", "mcp-server", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "5090"]
