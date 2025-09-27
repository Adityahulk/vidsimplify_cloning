# Dockerfile for Real-time Video Dubbing Streaming API
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for streaming
RUN pip install --no-cache-dir \
    websockets \
    pyaudio \
    python-multipart

# Clone and setup Wav2Lip
RUN git clone https://github.com/Rudrabha/Wav2Lip.git && \
    cd Wav2Lip && \
    pip install --no-cache-dir -r requirements.txt && \
    mkdir -p checkpoints && \
    wget https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth -O checkpoints/wav2lip_gan.pth && \
    cp inference.py .. && \
    cd .. && \
    mkdir -p models && \
    cp Wav2Lip/checkpoints/wav2lip_gan.pth models/

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p temp output static models

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the streaming API
CMD ["python", "streaming_api.py"]
