FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GICS_STATIC_MAP_PATH=/app/data/throatscan-gics-cache.json \
    GICS_SEED_PATH=/app/gics_seed.json

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY api_server.py db.py gics_api_helpers.py gics_seed.json export_for_throatscan.py ./
COPY data/throatscan-gics-cache.json ./data/throatscan-gics-cache.json
COPY workflows ./workflows

EXPOSE 8001

CMD ["sh", "-c", "uvicorn api_server:app --host 0.0.0.0 --port ${PORT:-8001}"]
