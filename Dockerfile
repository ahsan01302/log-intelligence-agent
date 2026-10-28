FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app
# Dependencies first so code changes don't reinstall them.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev

RUN useradd --create-home --uid 10001 app && mkdir -p /app/data && chown app /app/data
USER app

ENV PATH="/app/.venv/bin:$PATH" \
    LOGINTEL_INDEX_DIR=/app/data/index \
    LOGINTEL_UPLOAD_DIR=/app/data/uploads \
    LOGINTEL_HISTORY_PATH=/app/data/history.db

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["uvicorn", "log_intel.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
