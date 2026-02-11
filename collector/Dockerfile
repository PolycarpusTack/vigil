FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY collector/requirements.txt /app/collector-requirements.txt
RUN pip install --no-cache-dir -r /app/collector-requirements.txt

# Copy the core audit_framework library
COPY audit_framework/ /app/audit_framework/

# Copy the collector service
COPY collector/ /app/collector/

ENV PYTHONPATH=/app
ENV BIND_HOST=0.0.0.0
ENV BIND_PORT=8080

EXPOSE 8080

CMD ["uvicorn", "collector.main:app", "--host", "0.0.0.0", "--port", "8080"]
