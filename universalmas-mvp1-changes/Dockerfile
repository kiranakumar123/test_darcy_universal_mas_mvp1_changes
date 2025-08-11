# --- Builder Stage ---
FROM python:3.11-slim as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r universalframework && \
    useradd -r -g universalframework -d /app -s /sbin/nologin universalframework

WORKDIR /app

COPY requirements.txt .
# Install packages with network resilience and retry logic
RUN pip install --upgrade pip && \
    pip install --retries 5 --timeout 300 -r requirements.txt

COPY . .

RUN pip install -e .

# --- Production Stage ---
FROM python:3.11-slim as production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.local/bin:$PATH"

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r universalframework && \
    useradd -r -g universalframework -d /app -s /sbin/nologin universalframework

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

WORKDIR /app

USER universalframework

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "universal_framework.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
