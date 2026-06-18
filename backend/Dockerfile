FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    g++ \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN uv sync --no-dev

COPY app/ ./app/    
COPY segmentation/ ./segmentation/

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
