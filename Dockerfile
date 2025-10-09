# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .

# Environment variables (pass these at runtime)
# API Keys
ENV SYNC_API_KEY=${SYNC_API_KEY}
ENV ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
ENV GCS_BUCKET_NAME=${GCS_BUCKET_NAME:-vidsimplify}

# GCS Credentials - supports multiple methods:
# 1. GOOGLE_APPLICATION_CREDENTIALS (file path - for local/volume mount)
# 2. GCS_CREDENTIALS_BASE64 (base64 encoded JSON - for cloud deployments)
# 3. GCS_CREDENTIALS_JSON (raw JSON string - for cloud deployments)
ENV GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS}
ENV GCS_CREDENTIALS_BASE64=${GCS_CREDENTIALS_BASE64}
ENV GCS_CREDENTIALS_JSON=${GCS_CREDENTIALS_JSON}

ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

