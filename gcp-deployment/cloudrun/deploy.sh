#!/bin/bash
# olmOCR Cloud Run Deployment Script
# This script deploys all olmOCR services to Google Cloud Run

set -e

# ============================================
# Configuration
# ============================================
PROJECT_ID="${GCP_PROJECT_ID:-juniper-core}"
REGION="${GCP_REGION:-us-central1}"
BUCKET_NAME="olmocr-${PROJECT_ID}"

# Service names
FRONTEND_SERVICE="olmocr-frontend"
BACKEND_SERVICE="olmocr-backend"
WORKER_SERVICE="olmocr-worker"

# Parasail API key (required)
PARASAIL_API_KEY="${PARASAIL_API_KEY}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================
# Validation
# ============================================
echo_info "Validating configuration..."

if [ -z "$PARASAIL_API_KEY" ]; then
    echo_error "PARASAIL_API_KEY environment variable is required"
    echo "Set it with: export PARASAIL_API_KEY=psk-your-key"
    exit 1
fi

# Check gcloud is authenticated
if ! gcloud auth print-identity-token &> /dev/null; then
    echo_error "gcloud is not authenticated. Run: gcloud auth login"
    exit 1
fi

echo_info "Project: $PROJECT_ID"
echo_info "Region: $REGION"

# ============================================
# Set project
# ============================================
echo_info "Setting GCP project..."
gcloud config set project "$PROJECT_ID"

# ============================================
# Enable required APIs
# ============================================
echo_info "Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    storage.googleapis.com \
    firestore.googleapis.com \
    pubsub.googleapis.com \
    secretmanager.googleapis.com \
    --quiet

# ============================================
# Create Artifact Registry repository
# ============================================
echo_info "Creating Artifact Registry repository..."
gcloud artifacts repositories create olmocr \
    --repository-format=docker \
    --location="$REGION" \
    --description="olmOCR container images" \
    --quiet 2>/dev/null || echo_warn "Repository already exists"

# ============================================
# Create Cloud Storage bucket
# ============================================
echo_info "Creating Cloud Storage bucket..."
gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://$BUCKET_NAME" 2>/dev/null || echo_warn "Bucket already exists"

# Set CORS for frontend uploads
cat > /tmp/cors.json << 'EOF'
[
  {
    "origin": ["*"],
    "method": ["GET", "PUT", "POST", "DELETE", "OPTIONS"],
    "responseHeader": ["Content-Type", "Authorization", "Content-Length", "X-Requested-With"],
    "maxAgeSeconds": 3600
  }
]
EOF
gsutil cors set /tmp/cors.json "gs://$BUCKET_NAME"

# ============================================
# Create Pub/Sub topic and subscription
# ============================================
echo_info "Creating Pub/Sub resources..."
gcloud pubsub topics create olmocr-jobs --quiet 2>/dev/null || echo_warn "Topic already exists"
gcloud pubsub subscriptions create olmocr-jobs-sub \
    --topic=olmocr-jobs \
    --ack-deadline=600 \
    --quiet 2>/dev/null || echo_warn "Subscription already exists"

# ============================================
# Create Firestore database
# ============================================
echo_info "Creating Firestore database..."
gcloud firestore databases create --location="$REGION" --quiet 2>/dev/null || echo_warn "Firestore already exists"

# ============================================
# Store Parasail API key in Secret Manager
# ============================================
echo_info "Storing Parasail API key in Secret Manager..."
echo -n "$PARASAIL_API_KEY" | gcloud secrets create parasail-api-key \
    --data-file=- \
    --replication-policy="automatic" \
    --quiet 2>/dev/null || {
    echo_warn "Secret already exists, updating..."
    echo -n "$PARASAIL_API_KEY" | gcloud secrets versions add parasail-api-key --data-file=-
}

# ============================================
# Build and deploy services
# ============================================
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/olmocr"

# Build Frontend
echo_info "Building frontend..."
cd "$(dirname "$0")/../.."
gcloud builds submit \
    --tag "${REGISTRY}/frontend:latest" \
    --timeout=20m \
    -f gcp-frontend/Dockerfile \
    .

# Deploy Frontend
echo_info "Deploying frontend..."
gcloud run deploy "$FRONTEND_SERVICE" \
    --image "${REGISTRY}/frontend:latest" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --port 8080 \
    --memory 256Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --quiet

# Build Backend
echo_info "Building backend..."
gcloud builds submit \
    --tag "${REGISTRY}/backend:latest" \
    --timeout=20m \
    -f gcp-backend/Dockerfile \
    .

# Deploy Backend
echo_info "Deploying backend..."
gcloud run deploy "$BACKEND_SERVICE" \
    --image "${REGISTRY}/backend:latest" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 20 \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,GCS_BUCKET=$BUCKET_NAME,PUBSUB_TOPIC=olmocr-jobs" \
    --quiet

# Build Worker
echo_info "Building worker..."
gcloud builds submit \
    --tag "${REGISTRY}/worker:latest" \
    --timeout=30m \
    -f gcp-worker/Dockerfile.cloudrun \
    .

# Deploy Worker
echo_info "Deploying worker..."
gcloud run deploy "$WORKER_SERVICE" \
    --image "${REGISTRY}/worker:latest" \
    --platform managed \
    --region "$REGION" \
    --no-allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 600 \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,GCS_BUCKET=$BUCKET_NAME,PROCESSING_MODE=parasail,PARASAIL_MODEL=allenai/olmOCR-2-7B-1025" \
    --set-secrets "PARASAIL_API_KEY=parasail-api-key:latest" \
    --quiet

# ============================================
# Set up Pub/Sub push to worker
# ============================================
echo_info "Configuring Pub/Sub push subscription..."
WORKER_URL=$(gcloud run services describe "$WORKER_SERVICE" --region "$REGION" --format='value(status.url)')

# Create service account for Pub/Sub
gcloud iam service-accounts create pubsub-invoker \
    --display-name="Pub/Sub Cloud Run Invoker" \
    --quiet 2>/dev/null || echo_warn "Service account already exists"

# Grant invoker permission
gcloud run services add-iam-policy-binding "$WORKER_SERVICE" \
    --region="$REGION" \
    --member="serviceAccount:pubsub-invoker@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.invoker" \
    --quiet

# Update subscription to push mode
gcloud pubsub subscriptions modify-push-config olmocr-jobs-sub \
    --push-endpoint="${WORKER_URL}/process" \
    --push-auth-service-account="pubsub-invoker@${PROJECT_ID}.iam.gserviceaccount.com" \
    --quiet

# ============================================
# Output URLs
# ============================================
echo ""
echo_info "============================================"
echo_info "Deployment Complete!"
echo_info "============================================"
echo ""
FRONTEND_URL=$(gcloud run services describe "$FRONTEND_SERVICE" --region "$REGION" --format='value(status.url)')
BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" --region "$REGION" --format='value(status.url)')

echo -e "Frontend URL: ${GREEN}$FRONTEND_URL${NC}"
echo -e "Backend URL:  ${GREEN}$BACKEND_URL${NC}"
echo -e "Worker URL:   ${GREEN}$WORKER_URL${NC}"
echo ""
echo_info "Next steps:"
echo "  1. Set up Firebase Authentication in the Firebase Console"
echo "  2. Update frontend environment variables with Firebase config"
echo "  3. Configure CORS origins in backend to include frontend URL"
echo ""
