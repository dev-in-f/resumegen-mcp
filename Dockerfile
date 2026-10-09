FROM python:3.14-slim-trixie
COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    shared-mime-info \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN useradd -m mcp
RUN mkdir -p /data
RUN chown -R mcp:mcp /data
USER mcp
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project --group mcp

COPY src/ src/
COPY examples/ src/resumegen/examples/
RUN uv sync --frozen --no-dev --group mcp

ENV RESUMEGEN_DATA_DIR=/data
EXPOSE 8000
ENTRYPOINT ["/app/.venv/bin/python", "src/resumegen/mcp_server.py"]
