# olmOCR GCP Web Application - User Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Detailed Installation](#detailed-installation)
5. [Configuration](#configuration)
6. [Deployment](#deployment)
7. [Accessing the Application](#accessing-the-application)
8. [Using the Application](#using-the-application)
9. [Administration](#administration)
10. [Troubleshooting](#troubleshooting)
11. [Cost Management](#cost-management)

---

## Overview

The olmOCR GCP Web Application provides a user-friendly interface for converting PDF documents to clean markdown text using AI-powered OCR. The system consists of:

- **Web Frontend**: React-based interface with file browser and drag-and-drop upload
- **Backend API**: FastAPI service handling file management and job orchestration
- **GPU Workers**: Kubernetes-based workers running the olmOCR model

### Key Features

- 📁 Windows Explorer-like file browser
- 🖱️ Drag-and-drop PDF upload
- 📊 Multiple output formats (Markdown, JSON, HTML, Dolma)
- 🔄 Real-time processing status
- 💾 Persistent storage with Google Cloud Storage
- 🔐 Secure authentication with Firebase

---

## Prerequisites

### Required Accounts

1. **Google Cloud Platform Account** with billing enabled
   - Sign up at: https://cloud.google.com/
   - Free tier provides $300 credit for new users

2. **GitHub Account** (for CI/CD)
   - Sign up at: https://github.com/

### Required Tools

Install the following on your local machine:

```bash
# Google Cloud SDK
# macOS
brew install google-cloud-sdk

# Ubuntu/Debian
curl https://sdk.cloud.google.com | bash

# Windows - Download from:
# https://cloud.google.com/sdk/docs/install

# Verify installation
gcloud --version
```

```bash
# Docker (for local testing)
# macOS
brew install docker

# Ubuntu
sudo apt-get update
sudo apt-get install docker.io docker-compose

# Verify installation
docker --version
```

```bash
# Node.js 18+ (for frontend development)
# Using nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# Verify installation
node --version
npm --version
```

```bash
# Python 3.11+ (for backend development)
# Using pyenv (recommended)
curl https://pyenv.run | bash
pyenv install 3.11
pyenv global 3.11

# Verify installation
python --version
```

```bash
# kubectl (for Kubernetes management)
# macOS
brew install kubectl

# Ubuntu
sudo apt-get install kubectl

# Verify installation
kubectl version --client
```

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Development Machine | 8GB RAM, 50GB disk | 16GB RAM, 100GB SSD |
| GKE GPU Nodes | T4 GPU, 8 vCPU, 32GB RAM | L4/A100 GPU, 16 vCPU, 64GB RAM |

---

## Quick Start

For experienced users who want to get up and running quickly:

```bash
# 1. Clone the repository
git clone https://github.com/your-org/olmocr.git
cd olmocr

# 2. Set up GCP project
export PROJECT_ID="olmocr-$(date +%s)"
export REGION="us-central1"

gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# 3. Enable APIs and create resources
./scripts/setup-gcp.sh

# 4. Deploy all services
gcloud builds submit --config gcp-deployment/cloudbuild.yaml

# 5. Get the frontend URL
gcloud run services describe olmocr-frontend --region=$REGION --format='value(status.url)'
```

---

## Detailed Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/olmocr.git
cd olmocr
```

### Step 2: GCP Project Setup

```bash
# Set your project ID (use a unique name)
export PROJECT_ID="olmocr-production"
export REGION="us-central1"
export ZONE="us-central1-a"

# Create the project
gcloud projects create $PROJECT_ID --name="olmOCR Production"

# Set as active project
gcloud config set project $PROJECT_ID

# Link billing account (required for resources)
# List your billing accounts
gcloud billing accounts list

# Link billing (replace BILLING_ACCOUNT_ID)
gcloud billing projects link $PROJECT_ID \
  --billing-account=BILLING_ACCOUNT_ID
```

### Step 3: Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  container.googleapis.com \
  containerregistry.googleapis.com \
  storage.googleapis.com \
  firestore.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com \
  compute.googleapis.com
```

### Step 4: Create Service Accounts

```bash
# Backend API service account
gcloud iam service-accounts create olmocr-backend \
  --display-name="olmOCR Backend API"

# Worker service account
gcloud iam service-accounts create olmocr-worker \
  --display-name="olmOCR Processing Worker"

# Grant permissions to backend
for role in storage.objectAdmin pubsub.publisher datastore.user; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:olmocr-backend@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/$role"
done

# Grant permissions to worker
for role in storage.objectAdmin pubsub.subscriber datastore.user; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:olmocr-worker@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/$role"
done
```

### Step 5: Create Storage Bucket

```bash
# Create main storage bucket
gsutil mb -l $REGION gs://olmocr-$PROJECT_ID

# Set CORS for direct uploads from browser
cat > /tmp/cors.json << 'EOF'
[
  {
    "origin": ["*"],
    "method": ["GET", "PUT", "POST", "DELETE", "HEAD"],
    "responseHeader": ["Content-Type", "Content-Length", "Content-Range"],
    "maxAgeSeconds": 3600
  }
]
EOF
gsutil cors set /tmp/cors.json gs://olmocr-$PROJECT_ID

# Set lifecycle policy for temp files (auto-delete after 7 days)
cat > /tmp/lifecycle.json << 'EOF'
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {"age": 7, "matchesPrefix": ["users/*/temp/"]}
    }
  ]
}
EOF
gsutil lifecycle set /tmp/lifecycle.json gs://olmocr-$PROJECT_ID
```

### Step 6: Create Firestore Database

```bash
gcloud firestore databases create \
  --location=$REGION \
  --type=firestore-native
```

### Step 7: Create Pub/Sub Resources

```bash
# Create job processing topic
gcloud pubsub topics create olmocr-jobs

# Create subscription for workers
gcloud pubsub subscriptions create olmocr-jobs-sub \
  --topic=olmocr-jobs \
  --ack-deadline=600 \
  --message-retention-duration=1h
```

### Step 8: Set Up Firebase Authentication

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login to Firebase
firebase login

# Add Firebase to your GCP project
firebase projects:addfirebase $PROJECT_ID
```

Then configure authentication in the Firebase Console:

1. Go to https://console.firebase.google.com/
2. Select your project
3. Navigate to **Authentication** → **Sign-in method**
4. Enable the following providers:
   - **Email/Password**: Click enable
   - **Google**: Click enable, add your domain to authorized domains

5. Get your Firebase config:
   - Go to **Project Settings** → **General**
   - Scroll to "Your apps" section
   - Click **Add app** → **Web**
   - Copy the configuration object

### Step 9: Create GKE Cluster (for GPU workers)

```bash
# Create cluster
gcloud container clusters create olmocr-cluster \
  --zone=$ZONE \
  --num-nodes=1 \
  --machine-type=n1-standard-4 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=3

# Create GPU node pool
gcloud container node-pools create gpu-pool \
  --cluster=olmocr-cluster \
  --zone=$ZONE \
  --machine-type=n1-standard-8 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --num-nodes=0 \
  --enable-autoscaling \
  --min-nodes=0 \
  --max-nodes=5 \
  --node-taints=nvidia.com/gpu=present:NoSchedule

# Install NVIDIA GPU drivers
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded.yaml

# Get cluster credentials
gcloud container clusters get-credentials olmocr-cluster --zone=$ZONE
```

---

## Configuration

### Environment Variables

Create a `.env` file for local development:

```bash
# .env.local (Frontend)
VITE_API_URL=http://localhost:8080/api/v1
VITE_FIREBASE_API_KEY=your-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=123456789
VITE_FIREBASE_APP_ID=1:123456789:web:abc123
```

```bash
# .env (Backend)
ENVIRONMENT=development
GCP_PROJECT_ID=your-project-id
GCS_BUCKET=olmocr-your-project-id
PUBSUB_TOPIC=olmocr-jobs
FIREBASE_CREDENTIALS_PATH=/path/to/firebase-adminsdk.json
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

### Firebase Admin Credentials

1. Go to Firebase Console → Project Settings → Service Accounts
2. Click "Generate new private key"
3. Save the JSON file securely
4. Set the path in your environment:

```bash
export FIREBASE_CREDENTIALS_PATH=/path/to/firebase-adminsdk.json
```

For production, store in Secret Manager:

```bash
gcloud secrets create firebase-admin-key \
  --data-file=/path/to/firebase-adminsdk.json

gcloud secrets add-iam-policy-binding firebase-admin-key \
  --member="serviceAccount:olmocr-backend@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Deployment

### Option 1: Automated Deployment (Recommended)

Deploy all services with a single command:

```bash
# Deploy to GCP
gcloud builds submit --config gcp-deployment/cloudbuild.yaml \
  --substitutions=_REGION=$REGION,_ZONE=$ZONE

# Monitor build progress
gcloud builds list --limit=5
```

### Option 2: Manual Deployment

#### Deploy Frontend

```bash
cd gcp-frontend

# Build Docker image
docker build -t gcr.io/$PROJECT_ID/olmocr-frontend:latest \
  --build-arg VITE_API_URL=https://olmocr-api-xxx.run.app \
  --build-arg VITE_FIREBASE_API_KEY=your-key \
  .

# Push to Container Registry
docker push gcr.io/$PROJECT_ID/olmocr-frontend:latest

# Deploy to Cloud Run
gcloud run deploy olmocr-frontend \
  --image=gcr.io/$PROJECT_ID/olmocr-frontend:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080
```

#### Deploy Backend API

```bash
cd gcp-backend

# Build Docker image
docker build -t gcr.io/$PROJECT_ID/olmocr-api:latest .

# Push to Container Registry
docker push gcr.io/$PROJECT_ID/olmocr-api:latest

# Deploy to Cloud Run
gcloud run deploy olmocr-api \
  --image=gcr.io/$PROJECT_ID/olmocr-api:latest \
  --region=$REGION \
  --platform=managed \
  --service-account=olmocr-backend@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars=GCP_PROJECT_ID=$PROJECT_ID,GCS_BUCKET=olmocr-$PROJECT_ID
```

#### Deploy GPU Workers

```bash
# Apply Kubernetes configurations
kubectl apply -f gcp-deployment/kubernetes/namespace.yaml
kubectl apply -f gcp-deployment/kubernetes/configmap.yaml
kubectl apply -f gcp-deployment/kubernetes/pvc.yaml
kubectl apply -f gcp-deployment/kubernetes/worker-deployment.yaml
kubectl apply -f gcp-deployment/kubernetes/hpa.yaml

# Update configmap with your project ID
kubectl -n olmocr patch configmap olmocr-config \
  --type=merge \
  -p '{"data":{"project_id":"'$PROJECT_ID'","gcs_bucket":"olmocr-'$PROJECT_ID'"}}'

# Verify deployment
kubectl -n olmocr get pods
kubectl -n olmocr get hpa
```

---

## Accessing the Application

### Get Service URLs

```bash
# Frontend URL
echo "Frontend: $(gcloud run services describe olmocr-frontend --region=$REGION --format='value(status.url)')"

# Backend API URL
echo "API: $(gcloud run services describe olmocr-api --region=$REGION --format='value(status.url)')"
```

### First-Time Setup

1. **Open the Frontend URL** in your browser
2. **Sign Up or Sign In**:
   - Click "Sign in with Google" for quick access, OR
   - Click "Sign up" to create an account with email/password

3. **Verify Your Account** (if using email):
   - Check your email for verification link
   - Click the link to verify

### Custom Domain (Optional)

To use a custom domain:

```bash
# Add domain mapping
gcloud run domain-mappings create \
  --service=olmocr-frontend \
  --domain=ocr.yourdomain.com \
  --region=$REGION

# Get DNS records to configure
gcloud run domain-mappings describe \
  --domain=ocr.yourdomain.com \
  --region=$REGION
```

---

## Using the Application

### Dashboard Overview

After logging in, you'll see the main dashboard with:

```
┌─────────────────────────────────────────────────────────────────┐
│  olmOCR                                    [User Menu] [Logout] │
├───────────┬─────────────────────────────────────────────────────┤
│           │  📁 Home > Input > Documents                        │
│  📁 Input │  ─────────────────────────────────────────────────  │
│  📁 Output│  [List] [Grid]  [New Folder]  [Upload]  [Process]  │
│           │  ─────────────────────────────────────────────────  │
│  ─────────│  Name              Modified         Size    Type   │
│  Recent   │  ☐ 📄 report.pdf   Nov 30, 2025    2.3 MB   PDF   │
│  Shared   │  ☐ 📄 scan.pdf     Nov 29, 2025    5.1 MB   PDF   │
│           │  ☐ 📁 Archives     Nov 28, 2025    -        Folder │
│           │                                                     │
└───────────┴─────────────────────────────────────────────────────┘
```

### Uploading PDFs

#### Method 1: Drag and Drop

1. Navigate to your desired input folder
2. Drag PDF files from your computer
3. Drop them onto the upload zone
4. Watch the progress bar for each file

#### Method 2: Browse and Select

1. Click the **Upload** button in the toolbar
2. Click "Browse" or the upload zone
3. Select one or more PDF files
4. Click "Open" to start upload

### Processing PDFs

#### Single File

1. Click on a PDF to select it
2. Click the **Process** button
3. Configure output options:
   - **Output Location**: Choose folder (e.g., `output/processed`)
   - **Format**: Markdown, JSON, HTML, or Dolma
   - **Options**: Include metadata, preserve folder structure
4. Click **Start Processing**

#### Batch Processing

1. Select multiple PDFs:
   - Hold `Ctrl` (Windows) or `Cmd` (Mac) and click files
   - Or click first file, hold `Shift`, click last file
2. Click **Process (N files)**
3. Configure options as above
4. Click **Start Processing**

### Monitoring Jobs

View your processing jobs in the **Jobs** panel:

```
┌─────────────────────────────────────────────────────────────────┐
│  Processing Jobs                                                │
├─────────────────────────────────────────────────────────────────┤
│  🔄 report.pdf         Processing... [████████░░] 80%          │
│  ✓  scan.pdf           Completed     12 pages   2m 34s         │
│  ✓  document.pdf       Completed     5 pages    1m 12s         │
│  ✗  corrupted.pdf      Failed        Error: Invalid PDF        │
└─────────────────────────────────────────────────────────────────┘
```

### Downloading Results

1. Navigate to your output folder
2. Click on the processed file to preview
3. Click **Download** to save locally
4. Or right-click → "Download as ZIP" for multiple files

### File Browser Features

| Feature | How to Use |
|---------|------------|
| **Navigate** | Click folder to open, breadcrumb to go back |
| **Select** | Click file to select, Ctrl+click for multiple |
| **Sort** | Click column header (Name, Modified, Size, Type) |
| **View** | Toggle between List and Grid view |
| **Search** | Type in search box to filter |
| **New Folder** | Click folder icon in toolbar |
| **Delete** | Select files, click trash icon or press Delete |
| **Rename** | Right-click → Rename, or press F2 |
| **Move/Copy** | Drag files to new location |

---

## Administration

### User Management

Users are managed through Firebase Console:

1. Go to https://console.firebase.google.com/
2. Select your project
3. Navigate to **Authentication** → **Users**
4. Here you can:
   - View all users
   - Disable/delete accounts
   - Reset passwords
   - View sign-in activity

### Monitoring

#### Cloud Run Metrics

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=olmocr-api" --limit=50

# View metrics in console
open "https://console.cloud.google.com/run/detail/$REGION/olmocr-api/metrics?project=$PROJECT_ID"
```

#### GKE Worker Metrics

```bash
# View worker logs
kubectl -n olmocr logs -l app=olmocr-worker --tail=100

# View pod status
kubectl -n olmocr get pods -w

# View HPA status
kubectl -n olmocr get hpa
```

### Scaling

#### Automatic Scaling

The system automatically scales based on:
- **Cloud Run**: Request volume (0-20 instances)
- **GKE Workers**: Pub/Sub queue depth (0-10 pods)

#### Manual Scaling

```bash
# Scale Cloud Run
gcloud run services update olmocr-api \
  --min-instances=2 \
  --max-instances=50 \
  --region=$REGION

# Scale GKE workers
kubectl -n olmocr scale deployment olmocr-worker --replicas=3

# Update HPA limits
kubectl -n olmocr patch hpa olmocr-worker-hpa \
  -p '{"spec":{"maxReplicas":20}}'
```

### Backup and Recovery

#### Firestore Backup

```bash
# Export Firestore data
gcloud firestore export gs://olmocr-$PROJECT_ID-backups/firestore/$(date +%Y%m%d)

# Import from backup
gcloud firestore import gs://olmocr-$PROJECT_ID-backups/firestore/20251130
```

#### Storage Backup

```bash
# Sync to backup bucket
gsutil -m rsync -r gs://olmocr-$PROJECT_ID gs://olmocr-$PROJECT_ID-backup
```

---

## Troubleshooting

### Common Issues

#### "401 Unauthorized" Error

**Cause**: Firebase token expired or invalid

**Solution**:
1. Sign out and sign back in
2. Clear browser cache/cookies
3. Check Firebase project configuration

#### Upload Fails

**Cause**: File too large or wrong format

**Solution**:
1. Check file is PDF, PNG, or JPEG
2. Ensure file is under 100MB
3. Check browser console for errors

#### Processing Stuck at 0%

**Cause**: No GPU workers available

**Solution**:
```bash
# Check worker status
kubectl -n olmocr get pods

# Check for pending pods
kubectl -n olmocr describe pod -l app=olmocr-worker

# Check if GPU nodes are available
kubectl get nodes -l cloud.google.com/gke-accelerator=nvidia-tesla-t4
```

#### "Job Failed" Error

**Cause**: PDF corrupted or unsupported

**Solution**:
1. Check the error message in job details
2. Try opening PDF in another viewer
3. Re-save PDF and try again

### Debug Commands

```bash
# Check all service health
gcloud run services list --region=$REGION

# Check Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision" --limit=100 --format=json

# Check Pub/Sub queue
gcloud pubsub subscriptions pull olmocr-jobs-sub --limit=10 --auto-ack=false

# Check Firestore
gcloud firestore operations list

# Check GKE cluster
kubectl cluster-info
kubectl -n olmocr get all
```

### Getting Help

1. **Check Logs**: Always start with the logs
2. **GitHub Issues**: Report bugs at https://github.com/your-org/olmocr/issues
3. **Documentation**: Refer to `docs/gcp-architecture/ARCHITECTURE.md`

---

## Cost Management

### Estimated Costs

| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| Cloud Run (Frontend) | 0-10 instances | $5-20 |
| Cloud Run (API) | 1-20 instances | $50-150 |
| GKE Control Plane | Standard | $74.40 |
| GKE GPU Nodes | 1-5 T4 instances | $200-800 |
| Cloud Storage | 100GB | $2-5 |
| Firestore | 1M ops | $5-20 |
| Pub/Sub | 1M messages | $1-5 |
| **Total** | | **$337-1,074** |

### Cost Optimization Tips

1. **Use Preemptible GPUs**: 60-70% cheaper
   ```bash
   gcloud container node-pools update gpu-pool \
     --cluster=olmocr-cluster \
     --zone=$ZONE \
     --preemptible
   ```

2. **Scale to Zero**: Enable scale-to-zero for workers
   ```bash
   kubectl -n olmocr patch hpa olmocr-worker-hpa \
     -p '{"spec":{"minReplicas":0}}'
   ```

3. **Set Budget Alerts**:
   ```bash
   gcloud billing budgets create \
     --billing-account=BILLING_ACCOUNT_ID \
     --display-name="olmOCR Budget" \
     --budget-amount=500 \
     --threshold-rule=percent=50 \
     --threshold-rule=percent=90
   ```

4. **Monitor Usage**:
   - Check Cloud Billing → Reports
   - Set up cost anomaly detection
   - Review resource utilization weekly

---

## Appendix

### API Reference

See `docs/gcp-architecture/ARCHITECTURE.md` for full API documentation.

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + A` | Select all files |
| `Delete` | Delete selected |
| `F2` | Rename selected |
| `Ctrl/Cmd + C` | Copy selected |
| `Ctrl/Cmd + V` | Paste |
| `Ctrl/Cmd + U` | Upload files |
| `Enter` | Open selected folder |
| `Backspace` | Go to parent folder |

### Supported File Formats

**Input**:
- PDF (all versions)
- PNG images
- JPEG/JPG images

**Output**:
- Markdown (.md)
- JSON (.json)
- HTML (.html)
- Dolma JSONL (.jsonl)

---

*Last updated: November 2025*
*Version: 1.0.0*
