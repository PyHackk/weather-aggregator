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

  api:
    image: cmppcia-docker.artifactory.cib.echonet:443/qdi/api:latest
    command: >
      gunicorn src.core.config:app
      --workers 4
      --worker-class uvicorn.workers.UvicornWorker
      --bind 0.0.0.0:8888
      --timeout 120
      --keep-alive 5
    ports:
      - "8888:8888"
    volumes:
      - /mnt/shared/api/codebase/api/:/app:rw
    networks:
      - api-net
    environment:
      - EXPOSED_PORT=8888
      - PYTHONUNBUFFERED=1
      - PYTHONDONTWRITEBYTECODE=1
      - PYTHONPATH=/app
      - CELERY_BROKER_URL=redis://:redispass@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:redispass@redis:6379/1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8888/api/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      replicas: 3
      placement:
        preferences:
          - spread: node.id
      update_config:
        parallelism: 1
        delay: 15s
        order: start-first
        failure_action: rollback
      rollback_config:
        parallelism: 1
        delay: 10s
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
    volumes:
      - /mnt/shared/api/codebase/api/:/app:rw
    networks:
      - api-net
    environment:
      - PYTHONUNBUFFERED=1
      - PYTHONDONTWRITEBYTECODE=1
      - PYTHONPATH=/app
      - CELERY_BROKER_URL=redis://:redispass@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:redispass@redis:6379/1
    # Workers don't expose HTTP, so we ping the celery app directly instead
    healthcheck:
      test: ["CMD-SHELL", "celery -A src.core.celery_app inspect ping -d celery@$$HOSTNAME || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    deploy:
      replicas: 3
      placement:
        preferences:
          - spread: node.id
      update_config:
        parallelism: 1
        delay: 15s
        order: start-first
        failure_action: rollback
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
      - api-net
    volumes:
      - api_redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "redispass", "ping"]
      interval: 15s
      timeout: 5s
      retries: 3
    # Redis is stateful with a local volume, so we pin it to one node.
    # Spreading would lose data on container migration.
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.hostname == eurvlii120783
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
  api-net:
    external: true

volumes:
  api_redis-data:
    external: true
