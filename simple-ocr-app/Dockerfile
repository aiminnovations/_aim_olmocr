FROM python:3.11-slim

WORKDIR /app

# Install poppler for PDF rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app.py .

# Environment
ENV PORT=8080
ENV PARASAIL_API_KEY=""

EXPOSE 8080

CMD ["python", "app.py"]
