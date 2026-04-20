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