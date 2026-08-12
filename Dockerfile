FROM ghcr.io/astral-sh/uv:0.11.32-python3.13-trixie-slim
LABEL authors="sepinetam"

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN uv sync --no-dev

EXPOSE 8000

ENTRYPOINT ["uv", "run", "nber-cli", "mcp-server", "--transport", "streamable-http", "--port", "8000"]
