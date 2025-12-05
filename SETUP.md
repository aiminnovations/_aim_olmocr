# olmOCR Setup Guide

Convert PDFs to Markdown using AI-powered OCR. This guide covers installation from simple local usage to full cloud deployment.

## Table of Contents

- [Quick Start (Easiest)](#quick-start-easiest)
- [Manual Installation](#manual-installation)
- [Cloud Deployment](#cloud-deployment)
- [Configuration Options](#configuration-options)
- [Troubleshooting](#troubleshooting)

---

## Quick Start (Easiest)

The simplest way to get started - works locally without any cloud services.

### Prerequisites

- **Python 3.9+** - [Download](https://python.org)
- **Parasail API Key** - [Get free key](https://parasail.io) (required for OCR)
- **poppler-utils** - PDF rendering library

### One-Command Install

```bash
# Clone or download the repository
git clone https://github.com/aiminnovations/_aim_olmocr.git
cd _aim_olmocr

# Run installer
chmod +x install.sh
./install.sh
```

### Start the App

```bash
# Set your API key
export PARASAIL_API_KEY='psk-your-key-here'

# Run
./run.sh
```

Then open **http://localhost:8080** in your browser.

---

## Manual Installation

If the installer doesn't work for your system, follow these steps:

### Step 1: Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install poppler-utils python3 python3-pip python3-venv
```

**macOS:**
```bash
brew install poppler python3
```

**Windows:**
1. Install [Python 3.9+](https://python.org)
2. Download [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases)
3. Extract and add `poppler/bin` to your PATH

### Step 2: Set Up Python Environment

```bash
cd simple-ocr-app

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure API Key

```bash
export PARASAIL_API_KEY='psk-your-key-here'
```

Or create a `.env` file in `simple-ocr-app/`:
```
PARASAIL_API_KEY=psk-your-key-here
```

### Step 4: Run

```bash
python app.py
```

Open **http://localhost:8080**

---

## Cloud Deployment

For production use with persistent storage and scalability.

### Option A: Simple Cloud Run Deploy

Deploy the simple-ocr-app to Google Cloud Run:

```bash
cd simple-ocr-app

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Deploy
gcloud run deploy olmocr \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --set-env-vars "PARASAIL_API_KEY=your-key,GCP_PROJECT_ID=YOUR_PROJECT_ID"
```

### Option B: Full Stack (Frontend + Backend + Worker)

For enterprise deployments with Firebase authentication:

```bash
# From the root directory
./deploy.sh
```

This deploys:
- React frontend
- FastAPI backend
- PDF processing workers
- Firebase authentication
- Firestore database
- Cloud Storage for files

See `docs/gcp-architecture/` for full architecture documentation.

---

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PARASAIL_API_KEY` | (required) | Your Parasail API key |
| `PORT` | `8080` | Server port |
| `STORAGE_MODE` | `local` | `local` or `cloud` |
| `MAX_CONCURRENT_PAGES` | `5` | Pages processed in parallel |
| `MAX_CONCURRENT_JOBS` | `3` | Jobs processed simultaneously |
| `RENDER_DPI` | `120` | PDF rendering quality |
| `IMAGE_QUALITY` | `85` | JPEG compression (1-100) |
| `DATA_DIR` | `./data` | Local storage directory |

### Cloud Mode Variables

| Variable | Description |
|----------|-------------|
| `GCP_PROJECT_ID` | Google Cloud project ID |
| `GCS_BUCKET` | Cloud Storage bucket name |

### Storage Modes

**Local Mode (default):**
- Uses SQLite database
- Files stored on local filesystem
- Data persists in `./data/` directory
- No cloud services required

**Cloud Mode:**
- Uses Google Cloud Firestore
- Files stored in Cloud Storage
- Requires GCP project setup

---

## Using the Application

### Upload Files

1. **Single files:** Click "Upload Files" and select PDFs
2. **Folders:** Click "Upload Folder" to process entire directories
3. **Drag & drop:** Drag PDFs directly onto the upload area

### Processing

- Files are processed in parallel for speed
- Progress is shown in real-time
- Jobs persist even if you close the browser

### Download Results

- Click **View** to see rendered markdown
- Click **.md** to download individual files
- Click **Download All** for a ZIP of all files

### Where Are My Files?

In local mode, processed files are saved to:
```
simple-ocr-app/data/outputs/
```

Each file is saved as `{job_id}.md`.

---

## Performance Tuning

### For Large Documents

Increase concurrent page processing:
```bash
export MAX_CONCURRENT_PAGES=10
```

### For Many Files

Increase concurrent jobs:
```bash
export MAX_CONCURRENT_JOBS=5
```

### For Better Quality

Increase rendering quality (slower):
```bash
export RENDER_DPI=200
export IMAGE_QUALITY=95
```

### For Faster Processing

Decrease quality (faster):
```bash
export RENDER_DPI=100
export IMAGE_QUALITY=75
```

---

## API Reference

The application exposes a REST API:

### Upload PDF
```
POST /api/upload
Content-Type: multipart/form-data
file: <PDF file>
```

### Upload Multiple PDFs
```
POST /api/upload-multiple
Content-Type: multipart/form-data
files: <PDF files>
batch_name: "My Batch" (optional)
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

### Health Check
```
GET /health
```

---

## Troubleshooting

### "PARASAIL_API_KEY not configured"

Set your API key:
```bash
export PARASAIL_API_KEY='psk-your-key-here'
```

Get a key from [parasail.io](https://parasail.io)

### "poppler not found" or "pdf2image error"

Install poppler-utils:
```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils

# macOS
brew install poppler

# Windows: Download from GitHub releases
```

### "ModuleNotFoundError"

Activate the virtual environment:
```bash
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate      # Windows
```

Then reinstall dependencies:
```bash
pip install -r requirements.txt
```

### Slow Processing

- Reduce `RENDER_DPI` to 100
- Reduce `IMAGE_QUALITY` to 75
- Check your internet connection (API calls require network)

### Port Already in Use

Change the port:
```bash
export PORT=8081
python app.py
```

### Database Errors (Local Mode)

Reset the database:
```bash
rm -rf simple-ocr-app/data/
python app.py
```

---

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/aiminnovations/_aim_olmocr/issues)
- **Documentation:** See `docs/` folder
- **API Docs:** Visit `/docs` when running the app (e.g., http://localhost:8080/docs)

---

## License

Apache 2.0 - See LICENSE file.
