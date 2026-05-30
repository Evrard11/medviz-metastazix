FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml .
RUN uv sync --no-dev

COPY app/ .

CMD ["uv", "run", "python", "main.py"]
