# Worker Dockerfile - GPU-enabled
FROM vllm/vllm-openai:v0.11.0

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHON_VERSION=3.12

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    fonts-liberation \
    fonts-dejavu \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy olmocr package from parent (assumes build context is repo root)
COPY olmocr/ ./olmocr/

# Copy worker code
COPY gcp-worker/worker/ ./worker/

# Set Python path
ENV PYTHONPATH=/app

# Default environment variables
ENV GCP_PROJECT_ID=""
ENV GCS_BUCKET=""
ENV PUBSUB_SUBSCRIPTION="olmocr-jobs-sub"
ENV MODEL_NAME="allenai/olmOCR-2-7B-1025-FP8"
ENV VLLM_PORT=30024

# Run the worker
CMD ["python", "-m", "worker.main"]
