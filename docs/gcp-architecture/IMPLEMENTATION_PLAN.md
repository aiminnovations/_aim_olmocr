# olmOCR GCP Implementation Plan

## Overview

This document provides a detailed, step-by-step implementation guide for deploying olmOCR on Google Cloud Platform with a React frontend.

---

## Phase 1: GCP Project Setup

### 1.1 Create and Configure GCP Project

```bash
# Set project variables
export PROJECT_ID="olmocr-prod"
export REGION="us-central1"
export ZONE="us-central1-a"

# Create project
gcloud projects create $PROJECT_ID --name="olmOCR Production"
gcloud config set project $PROJECT_ID

# Link billing account
gcloud beta billing projects link $PROJECT_ID \
  --billing-account=BILLING_ACCOUNT_ID

# Enable required APIs
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

### 1.2 Create Service Accounts

```bash
# Backend API service account
gcloud iam service-accounts create olmocr-backend \
  --display-name="olmOCR Backend API"

# Worker service account
gcloud iam service-accounts create olmocr-worker \
  --display-name="olmOCR Processing Worker"

# Grant permissions to backend
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:olmocr-backend@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:olmocr-backend@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:olmocr-backend@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

# Grant permissions to worker
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:olmocr-worker@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:olmocr-worker@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/pubsub.subscriber"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:olmocr-worker@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

### 1.3 Create Storage Bucket

```bash
# Create main storage bucket
gsutil mb -l $REGION gs://olmocr-$PROJECT_ID

# Set lifecycle policy for temp files
cat > /tmp/lifecycle.json << 'EOF'
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {
        "age": 7,
        "matchesPrefix": ["temp/"]
      }
    }
  ]
}
EOF

gsutil lifecycle set /tmp/lifecycle.json gs://olmocr-$PROJECT_ID

# Enable CORS for direct uploads
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
```

### 1.4 Set Up Firestore

```bash
# Create Firestore database in Native mode
gcloud firestore databases create \
  --location=$REGION \
  --type=firestore-native
```

### 1.5 Create Pub/Sub Resources

```bash
# Create job processing topic
gcloud pubsub topics create olmocr-jobs

# Create subscription for workers
gcloud pubsub subscriptions create olmocr-jobs-sub \
  --topic=olmocr-jobs \
  --ack-deadline=600 \
  --message-retention-duration=1h

# Create notifications topic
gcloud pubsub topics create olmocr-notifications
```

---

## Phase 2: Firebase Authentication Setup

### 2.1 Create Firebase Project

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login to Firebase
firebase login

# Add Firebase to existing GCP project
firebase projects:addfirebase $PROJECT_ID

# Initialize Firebase
cd /path/to/project
firebase init
```

### 2.2 Configure Authentication Providers

1. Go to Firebase Console > Authentication > Sign-in method
2. Enable the following providers:
   - Email/Password
   - Google
   - (Optional) GitHub, Microsoft

### 2.3 Generate Firebase Config

```javascript
// Save this configuration for frontend
const firebaseConfig = {
  apiKey: "AIzaSy...",
  authDomain: "$PROJECT_ID.firebaseapp.com",
  projectId: "$PROJECT_ID",
  storageBucket: "$PROJECT_ID.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abc123"
};
```

---

## Phase 3: Backend API Implementation

### 3.1 Project Structure

```
gcp-backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── browse.py
│   │   ├── upload.py
│   │   ├── processing.py
│   │   ├── download.py
│   │   └── settings.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── storage.py
│   │   ├── firestore.py
│   │   ├── pubsub.py
│   │   └── auth.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── file.py
│   │   ├── job.py
│   │   └── user.py
│   └── utils/
│       └── helpers.py
├── tests/
├── requirements.txt
├── Dockerfile
└── cloudbuild.yaml
```

### 3.2 Requirements

```txt
# requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
pydantic==2.5.3
google-cloud-storage==2.14.0
google-cloud-firestore==2.14.0
google-cloud-pubsub==2.19.0
firebase-admin==6.3.0
python-jose[cryptography]==3.3.0
aiofiles==23.2.1
httpx==0.26.0
structlog==24.1.0
```

### 3.3 Core Implementation Files

See the `gcp-backend/` directory for complete implementation.

---

## Phase 4: Processing Worker Implementation

### 4.1 Worker Structure

```
gcp-worker/
├── worker/
│   ├── __init__.py
│   ├── main.py
│   ├── processor.py
│   ├── vllm_client.py
│   └── config.py
├── requirements.txt
├── Dockerfile
└── kubernetes/
    ├── deployment.yaml
    ├── hpa.yaml
    └── service.yaml
```

### 4.2 Worker Dockerfile

```dockerfile
# Dockerfile
FROM vllm/vllm-openai:v0.11.0

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    fonts-liberation \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy olmocr package
COPY olmocr/ ./olmocr/

# Copy worker code
COPY worker/ ./worker/

# Pre-download model (optional, increases image size)
# RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('allenai/olmOCR-2-7B-1025-FP8')"

ENV PYTHONPATH=/app
ENV VLLM_PORT=30024

# Start worker
CMD ["python", "-m", "worker.main"]
```

---

## Phase 5: Frontend Implementation

### 5.1 Create React Project

```bash
# Create new Vite project
npm create vite@latest olmocr-frontend -- --template react-ts

cd olmocr-frontend

# Install dependencies
npm install \
  @tanstack/react-query \
  axios \
  zustand \
  react-dropzone \
  react-router-dom \
  firebase \
  tailwindcss \
  @headlessui/react \
  @heroicons/react \
  lucide-react \
  clsx \
  date-fns

# Install dev dependencies
npm install -D \
  @types/node \
  postcss \
  autoprefixer \
  typescript \
  @types/react \
  @types/react-dom
```

### 5.2 Configure Tailwind

```bash
npx tailwindcss init -p
```

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### 5.3 Frontend Structure

```
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Layout.tsx
│   │   ├── upload/
│   │   │   ├── DropZone.tsx
│   │   │   └── UploadProgress.tsx
│   │   ├── browser/
│   │   │   ├── FileBrowser.tsx
│   │   │   ├── FolderTree.tsx
│   │   │   ├── FileList.tsx
│   │   │   ├── PathBreadcrumb.tsx
│   │   │   └── OutputSelector.tsx
│   │   ├── processing/
│   │   │   ├── JobQueue.tsx
│   │   │   ├── JobCard.tsx
│   │   │   └── JobHistory.tsx
│   │   └── common/
│   │       ├── Button.tsx
│   │       ├── Modal.tsx
│   │       └── Loading.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useFileBrowser.ts
│   │   ├── useUpload.ts
│   │   ├── useJobs.ts
│   │   └── useWebSocket.ts
│   ├── services/
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   └── storage.ts
│   ├── store/
│   │   ├── authStore.ts
│   │   ├── fileStore.ts
│   │   └── jobStore.ts
│   ├── types/
│   │   ├── file.ts
│   │   ├── job.ts
│   │   └── user.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── Dockerfile
```

---

## Phase 6: GKE Cluster Setup

### 6.1 Create GKE Cluster

```bash
# Create cluster with GPU support
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

### 6.2 Deploy Workers

```bash
# Apply Kubernetes manifests
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/hpa.yaml
kubectl apply -f kubernetes/service.yaml
```

---

## Phase 7: Cloud Build & CI/CD

### 7.1 Connect Repository

```bash
# Connect GitHub repository
gcloud builds connections create github-connection \
  --region=$REGION

# Create build trigger for main branch
gcloud builds triggers create github \
  --name="olmocr-deploy" \
  --repo-name="olmocr-gcp" \
  --repo-owner="your-org" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml"
```

### 7.2 Cloud Build Configuration

```yaml
# cloudbuild.yaml
steps:
  # Build and push frontend
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/olmocr-frontend:$SHORT_SHA', './frontend']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/olmocr-frontend:$SHORT_SHA']

  # Build and push backend
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/olmocr-api:$SHORT_SHA', './gcp-backend']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/olmocr-api:$SHORT_SHA']

  # Build and push worker
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/olmocr-worker:$SHORT_SHA', './gcp-worker']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/olmocr-worker:$SHORT_SHA']

  # Deploy frontend to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'olmocr-frontend'
      - '--image=gcr.io/$PROJECT_ID/olmocr-frontend:$SHORT_SHA'
      - '--region=${_REGION}'
      - '--platform=managed'
      - '--allow-unauthenticated'

  # Deploy backend to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'olmocr-api'
      - '--image=gcr.io/$PROJECT_ID/olmocr-api:$SHORT_SHA'
      - '--region=${_REGION}'
      - '--platform=managed'
      - '--service-account=olmocr-backend@$PROJECT_ID.iam.gserviceaccount.com'

  # Update GKE worker deployment
  - name: 'gcr.io/cloud-builders/kubectl'
    args:
      - 'set'
      - 'image'
      - 'deployment/olmocr-worker'
      - 'worker=gcr.io/$PROJECT_ID/olmocr-worker:$SHORT_SHA'
      - '-n'
      - 'olmocr'
    env:
      - 'CLOUDSDK_COMPUTE_ZONE=${_ZONE}'
      - 'CLOUDSDK_CONTAINER_CLUSTER=olmocr-cluster'

substitutions:
  _REGION: us-central1
  _ZONE: us-central1-a

images:
  - 'gcr.io/$PROJECT_ID/olmocr-frontend:$SHORT_SHA'
  - 'gcr.io/$PROJECT_ID/olmocr-api:$SHORT_SHA'
  - 'gcr.io/$PROJECT_ID/olmocr-worker:$SHORT_SHA'
```

---

## Phase 8: Monitoring & Observability

### 8.1 Cloud Monitoring Setup

```bash
# Create uptime check for API
gcloud monitoring uptime-check-configs create olmocr-api-health \
  --display-name="olmOCR API Health" \
  --monitored-resource-type=cloud-run-revision \
  --http-check-path=/health \
  --period=60s

# Create alerting policy
gcloud monitoring policies create \
  --display-name="High Error Rate" \
  --condition-filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count" AND metric.labels.response_code_class="5xx"' \
  --condition-threshold-value=10 \
  --condition-threshold-duration=60s \
  --notification-channels=CHANNEL_ID
```

### 8.2 Logging Configuration

```python
# Structured logging setup
import structlog
from google.cloud import logging as cloud_logging

def setup_logging():
    client = cloud_logging.Client()
    client.setup_logging()

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

---

## Phase 9: Security Hardening

### 9.1 VPC Service Controls

```bash
# Create access policy
gcloud access-context-manager policies create \
  --organization=ORG_ID \
  --title="olmOCR Access Policy"

# Create service perimeter
gcloud access-context-manager perimeters create olmocr-perimeter \
  --policy=POLICY_ID \
  --title="olmOCR Service Perimeter" \
  --resources="projects/$PROJECT_ID" \
  --restricted-services="storage.googleapis.com,firestore.googleapis.com"
```

### 9.2 Secret Management

```bash
# Store sensitive configuration in Secret Manager
echo -n "your-firebase-service-account-key" | \
  gcloud secrets create firebase-admin-key \
  --data-file=- \
  --replication-policy="automatic"

# Grant access to service accounts
gcloud secrets add-iam-policy-binding firebase-admin-key \
  --member="serviceAccount:olmocr-backend@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Verification Checklist

### Infrastructure
- [ ] GCP project created and configured
- [ ] All required APIs enabled
- [ ] Service accounts created with correct permissions
- [ ] Cloud Storage bucket created with lifecycle policies
- [ ] Firestore database initialized
- [ ] Pub/Sub topics and subscriptions created
- [ ] GKE cluster with GPU node pool created

### Authentication
- [ ] Firebase project linked
- [ ] Authentication providers configured
- [ ] Firebase Admin SDK configured in backend

### Backend
- [ ] FastAPI application running locally
- [ ] All API endpoints tested
- [ ] Docker image builds successfully
- [ ] Cloud Run deployment successful

### Frontend
- [ ] React application running locally
- [ ] Firebase Auth integration working
- [ ] File upload working
- [ ] File browser component working
- [ ] Real-time updates via WebSocket working

### Workers
- [ ] Worker Docker image builds successfully
- [ ] vLLM server starts correctly
- [ ] PDF processing pipeline working
- [ ] GKE deployment successful
- [ ] Autoscaling tested

### CI/CD
- [ ] Cloud Build triggers configured
- [ ] Automated deployments working
- [ ] All environments (dev, staging, prod) configured

### Monitoring
- [ ] Cloud Monitoring dashboards created
- [ ] Alerting policies configured
- [ ] Logging working correctly
- [ ] Uptime checks configured

---

## Troubleshooting

### Common Issues

**1. GPU not available in GKE**
```bash
# Check GPU driver installation
kubectl get pods -n kube-system -l k8s-app=nvidia-driver-installer

# Check node GPU availability
kubectl describe nodes | grep -A 5 "nvidia.com/gpu"
```

**2. Pub/Sub message acknowledgment timeout**
```bash
# Increase acknowledgment deadline
gcloud pubsub subscriptions update olmocr-jobs-sub \
  --ack-deadline=600
```

**3. Cloud Run cold start issues**
```bash
# Set minimum instances
gcloud run services update olmocr-api \
  --min-instances=1
```

**4. Storage permission errors**
```bash
# Verify service account permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --format='table(bindings.role)' \
  --filter="bindings.members:olmocr-backend"
```
