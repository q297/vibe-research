FROM ghcr.io/astral-sh/uv:0.13.4 AS uv

FROM python:3.12-slim
COPY --from=uv /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini start.sh ./
COPY migrations ./migrations
COPY app ./app

RUN useradd --system --uid 10001 app
USER app

EXPOSE 8000
CMD ["sh", "start.sh"]
