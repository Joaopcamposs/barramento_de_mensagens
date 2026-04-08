FROM python:3.11.9-slim

WORKDIR /barramento_de_mensagens

ENV PATH="/barramento_de_mensagens/.venv/bin:$PATH" \
    PYTHONPATH=/barramento_de_mensagens \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && pip install --no-cache-dir --upgrade pip uv \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN uv sync --no-dev

COPY . .

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /barramento_de_mensagens

USER appuser

CMD ["sh", "-c", "uvicorn business_contexts.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
