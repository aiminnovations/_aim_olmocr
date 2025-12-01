# olmOCR Batch Processor v2.0

A high-performance web app for batch PDF-to-Markdown conversion using olmOCR via Parasail API.

## Features

- **5-10x Faster Processing** - Parallel page processing with configurable concurrency
- **Persistent Jobs** - Jobs survive page refresh, browser close, and server restarts (via Google Cloud Firestore)
- **Folder Uploads** - Upload entire folders with automatic structure preservation
- **Batch Organization** - Group files into batches with separate output configurations
- **Configurable Output** - Choose where processed files are saved
- **No Document Limits** - Process as many PDFs as you want

---

## Quick Deploy to Google Cloud Run

### Prerequisites

1. A Google Cloud account with billing enabled
2. [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed
3. A [Parasail API key](https://parasail.io)

### One-Command Deploy

```bash
cd simple-ocr-app
chmod +x deploy.sh
./deploy.sh
```

The script will:
- Enable required GCP APIs (Cloud Run, Firestore, Storage)
- Create a Firestore database (if needed)
- Create a GCS bucket for PDF storage (if needed)
- Build and deploy the app to Cloud Run
- Output your live URL

### Environment Variables (Optional)

Set these before running `deploy.sh`:

```bash
export GCP_PROJECT_ID="your-project-id"    # Default: juniper-core
export GCP_REGION="us-central1"             # Default: us-central1
export PARASAIL_API_KEY="your-api-key"      # Your Parasail key
export GCS_BUCKET="your-bucket-name"        # Default: {project}-olmocr-pdfs
```

---

## Manual Deployment

### Cloud Run with gcloud

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable APIs
gcloud services enable run.googleapis.com firestore.googleapis.com storage.googleapis.com

# Create Firestore database
gcloud firestore databases create --location=us-central1

# Create storage bucket
gcloud storage buckets create gs://YOUR_PROJECT-olmocr-pdfs --location=us-central1

# Deploy
gcloud run deploy olmocr-simple \
    --source ./simple-ocr-app \
    --region us-central1 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 600 \
    --allow-unauthenticated \
    --set-env-vars "PARASAIL_API_KEY=your-key,GCP_PROJECT_ID=YOUR_PROJECT_ID,GCS_BUCKET=YOUR_PROJECT-olmocr-pdfs"
```

### Docker (Local Testing)

```bash
cd simple-ocr-app

# Build
docker build -t olmocr-batch .

# Run (requires GCP credentials for Firestore)
docker run -p 8080:8080 \
    -e PARASAIL_API_KEY="your-key" \
    -e GCP_PROJECT_ID="your-project" \
    -e GOOGLE_APPLICATION_CREDENTIALS="/creds/key.json" \
    -v /path/to/service-account.json:/creds/key.json \
    olmocr-batch
```

---

## Local Development

```bash
# Install dependencies
cd simple-ocr-app
pip install -r requirements.txt

# Authenticate with GCP (for Firestore access)
gcloud auth application-default login

# Set environment variables
export PARASAIL_API_KEY="your-key"
export GCP_PROJECT_ID="your-project"
export GCS_BUCKET="your-bucket"  # Optional

# Run
python app.py
```

Open http://localhost:8080

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PARASAIL_API_KEY` | Yes | - | Your Parasail API key for olmOCR |
| `GCP_PROJECT_ID` | Yes | - | Google Cloud project ID |
| `GCS_BUCKET` | No | - | GCS bucket for PDF storage (falls back to Firestore) |
| `PORT` | No | `8080` | Server port |
| `MAX_CONCURRENT_PAGES` | No | `5` | Max pages processed in parallel per job |
| `MAX_CONCURRENT_JOBS` | No | `3` | Max jobs processed simultaneously |
| `RENDER_DPI` | No | `120` | DPI for PDF rendering |
| `IMAGE_QUALITY` | No | `85` | JPEG quality (1-100) |

---

## GCP Services Used

| Service | Purpose | Pricing |
|---------|---------|---------|
| **Cloud Run** | Runs the app | Pay per request |
| **Firestore** | Stores job state, results | Free tier: 1GB storage, 50k reads/day |
| **Cloud Storage** | Stores uploaded PDFs | Free tier: 5GB |

For most use cases, this stays within the free tier.

---

## API Reference

### Upload Single PDF
```
POST /api/upload
Content-Type: multipart/form-data

file: <PDF file>
batch_id: (optional) existing batch ID
relative_path: (optional) path for folder structure
```

### Upload Multiple PDFs
```
POST /api/upload-multiple
Content-Type: multipart/form-data

files: <PDF files>
batch_name: (optional) name for the batch
output_path: (optional) where to save outputs
relative_paths: (optional) JSON array of paths
```

### Get Batch Status
```
GET /api/batch/{batch_id}
```

### Get Job Output
```
GET /api/jobs/{job_id}/output
```

### List All Batches
```
GET /api/batches
```

### Delete Batch
```
DELETE /api/batch/{batch_id}
```

---

## Performance Tuning

For large documents or high-volume processing:

- **Increase `MAX_CONCURRENT_PAGES`** to 8-10 if your Parasail API plan supports higher rate limits
- **Increase `MAX_CONCURRENT_JOBS`** if you have multiple users or want faster batch processing
- **Lower `RENDER_DPI`** to 100 for faster rendering (slightly lower quality)
- **Lower `IMAGE_QUALITY`** to 70-75 for smaller API payloads

---

## Get a Parasail API Key

1. Go to [parasail.io](https://parasail.io)
2. Sign up and create an API key
3. Use model: `allenai/olmOCR-2-7B-1025`
