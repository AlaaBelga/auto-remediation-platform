### Multi-stage Dockerfile for P2
### Stage 1: builder - install dependencies
FROM python:3.11-slim AS builder

WORKDIR /install
COPY requirements.txt /install/requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /install/requirements.txt

### Stage 2: runtime - copy installed packages and app
FROM python:3.11-slim

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY P2 /app/P2

ENV PYTHONPATH=/app

EXPOSE 8000

# Healthcheck against the FastAPI health endpoint without requiring curl
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1

CMD ["uvicorn", "P2.api:app", "--host", "0.0.0.0", "--port", "8000"]
