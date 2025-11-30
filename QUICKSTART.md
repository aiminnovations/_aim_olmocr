# olmOCR Quick Start Guide

Deploy olmOCR to Google Cloud Platform in minutes.

## Prerequisites

1. **Google Cloud SDK** - [Install gcloud](https://cloud.google.com/sdk/docs/install)
2. **GCP Project** - Create or have access to a GCP project
3. **Parasail API Key** - Get from [parasail.io](https://parasail.io)

## Deployment Steps

### Step 1: Authenticate with GCP

```bash
gcloud auth login
gcloud config set project juniper-core
```

### Step 2: Set Environment Variables

```bash
export GCP_PROJECT_ID="juniper-core"
export PARASAIL_API_KEY="psk-aimiwsstmt1A-JBSW3y4jAxHjEvwMvScP"
```

### Step 3: Run Deployment

```bash
./deploy.sh
```

This script will:
- Enable required GCP APIs
- Create Cloud Storage bucket
- Create Firestore database
- Create Pub/Sub topic
- Store API key in Secret Manager
- Build and deploy all services to Cloud Run

### Step 4: Set Up Firebase Authentication

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project" and select your GCP project
3. Go to **Authentication** > **Sign-in method**
4. Enable **Email/Password** provider
5. (Optional) Enable **Google** provider
6. Go to **Project Settings** > **Your apps**
7. Click the web icon (`</>`) to add a web app
8. Copy the Firebase configuration values

### Step 5: Configure Frontend

```bash
./configure-frontend.sh
```

Enter your Firebase configuration when prompted:
- API Key
- Auth Domain
- Project ID
- Storage Bucket
- Messaging Sender ID
- App ID

### Step 6: Access Your Application

After configuration completes, your application URLs will be displayed:

```
Frontend URL: https://olmocr-frontend-xxxxx-uc.a.run.app
Backend URL:  https://olmocr-backend-xxxxx-uc.a.run.app
```

Open the Frontend URL in your browser to start using olmOCR!

## Using olmOCR

1. **Create Account** - Sign up with email or Google
2. **Upload PDFs** - Drag & drop or click to upload
3. **Process** - Select output format and start processing
4. **Download** - Get your converted documents

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend    │────▶│    Worker    │
│  Cloud Run   │     │  Cloud Run   │     │  Cloud Run   │
└──────────────┘     └──────┬───────┘     └───────┬──────┘
                            │                     │
                            ▼                     ▼
                     ┌──────────────┐      ┌──────────────┐
                     │   Pub/Sub    │─────▶│   Parasail   │
                     │ olmocr-jobs  │      │ olmOCR API   │
                     └──────────────┘      └──────────────┘
```

## Troubleshooting

### Build fails
```bash
# Check Cloud Build logs
gcloud builds list --limit=5
gcloud builds log <BUILD_ID>
```

### Service not responding
```bash
# Check service status
gcloud run services describe olmocr-frontend --region us-central1
gcloud run services describe olmocr-backend --region us-central1
gcloud run services describe olmocr-worker --region us-central1
```

### View logs
```bash
# Frontend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=olmocr-frontend" --limit=50

# Backend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=olmocr-backend" --limit=50

# Worker logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=olmocr-worker" --limit=50
```

## Cost Estimate

With Cloud Run's pay-per-use model and Parasail API:

| Usage Level | Est. Monthly Cost |
|-------------|-------------------|
| Light (100 PDFs/month) | $5-15 |
| Medium (1000 PDFs/month) | $30-80 |
| Heavy (10000 PDFs/month) | $200-500 |

Costs depend on PDF complexity and page count.

## Support

- Documentation: `docs/gcp-architecture/USER_GUIDE.md`
- Issues: https://github.com/aiminnovations/_aim_olmocr/issues
