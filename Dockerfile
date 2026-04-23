# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run migrations and start server
CMD flask db upgrade && gunicorn -b 0.0.0.0:5000 "app:create_app()"






version: "3.8"

services:
  qdi-api:
    image: cmppcia-docker.artifactory.cib.echonet:443/qdi/api:latest
    command: >
      gunicorn src.core.config:app
      --workers 4
      --worker-class uvicorn.workers.UvicornWorker
      --bind 0.0.0.0:8888
      --timeout 120
      --keep-alive 5
      --log-config /app/logging.yaml
    ports:
      - "8888:8888"
    networks:
      - qdi-api-network
    environment:
      - EXPOSED_PORT=8888
      - PYTHONUNBUFFERED=1
      - PYTHONDONTWRITEBYTECODE=1
      - PYTHONPATH=/app
      - SSL_CERT_FILE=/app/certs/CA_Bundle.pem
      - CELERY_BROKER_URL=redis://:redispass@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:redispass@redis:6379/1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8888/api/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.role == worker
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
        reservations:
          cpus: "0.25"
          memory: 256M

  celery-worker:
    image: cmppcia-docker.artifactory.cib.echonet:443/qdi/api:latest
    command: >
      celery -A src.core.celery_app worker
      --loglevel=info
      --concurrency=4
      --queues=default,heavy
      -E
    networks:
      - qdi-api-network
    environment:
      - PYTHONUNBUFFERED=1
      - PYTHONDONTWRITEBYTECODE=1
      - PYTHONPATH=/app
      - SSL_CERT_FILE=/app/certs/CA_Bundle.pem
      - CELERY_BROKER_URL=redis://:redispass@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:redispass@redis:6379/1
    deploy:
      replicas: 2
      placement:
        constraints:
          - node.role == worker
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: "2.0"
          memory: 1G
        reservations:
          cpus: "0.5"
          memory: 512M

  redis:
    image: cmppcia-docker.artifactory.cib.echonet:443/redis:8.0.1
    command: redis-server --requirepass redispass --maxmemory 512mb --maxmemory-policy allkeys-lru
    networks:
      - qdi-api-network
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "redispass", "ping"]
      interval: 15s
      timeout: 5s
      retries: 3
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.role == worker
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
        reservations:
          cpus: "0.1"
          memory: 128M

networks:
  qdi-api-network:
    driver: overlay

volumes:
  redis-data:
    driver: local