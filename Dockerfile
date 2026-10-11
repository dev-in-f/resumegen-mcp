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

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

USER root

COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY main.py ./
RUN uv sync --frozen --no-dev && chown -R mcp:mcp /app

USER mcp

ENTRYPOINT ["/app/.venv/bin/python", "main.py"]
