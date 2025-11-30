#!/bin/bash
#
# olmOCR Master Deployment Script
#
# This script deploys the complete olmOCR application to Google Cloud Platform.
# It handles infrastructure provisioning, container building, and service deployment.
#
# Prerequisites:
#   - Google Cloud SDK (gcloud) installed and authenticated
#   - Docker installed (for local builds)
#   - Terraform installed (optional, for infrastructure-as-code)
#
# Usage:
#   ./deploy.sh
#
# Environment Variables (can be set before running):
#   GCP_PROJECT_ID    - Your GCP project ID (required)
#   PARASAIL_API_KEY  - Your Parasail API key (required)
#   GCP_REGION        - GCP region (default: us-central1)

set -e

# ============================================
# Configuration
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ID="${GCP_PROJECT_ID:-juniper-core}"
REGION="${GCP_REGION:-us-central1}"
PARASAIL_KEY="${PARASAIL_API_KEY}"

# Service names
FRONTEND_SERVICE="olmocr-frontend"
BACKEND_SERVICE="olmocr-backend"
WORKER_SERVICE="olmocr-worker"
BUCKET_NAME="olmocr-${PROJECT_ID}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
echo_header() { echo -e "\n${BLUE}========================================${NC}"; echo -e "${BLUE}$1${NC}"; echo -e "${BLUE}========================================${NC}"; }
echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================
# Pre-flight Checks
# ============================================
echo_header "olmOCR Deployment"
echo_info "Project: $PROJECT_ID"
echo_info "Region: $REGION"
echo ""

# Check required tools
check_tool() {
    if ! command -v "$1" &> /dev/null; then
        echo_error "$1 is required but not installed."
        exit 1
    fi
}

check_tool "gcloud"

# Check authentication
if ! gcloud auth print-identity-token &> /dev/null; then
    echo_error "Not authenticated with gcloud. Run: gcloud auth login"
    exit 1
fi

# Check Parasail API key
if [ -z "$PARASAIL_KEY" ]; then
    echo_error "PARASAIL_API_KEY environment variable is required"
    echo "Set it with: export PARASAIL_API_KEY=psk-your-key"
    exit 1
fi

# ============================================
# Step 1: Set up GCP Project
# ============================================
echo_header "Step 1: Setting up GCP Project"

gcloud config set project "$PROJECT_ID"

echo_info "Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    storage.googleapis.com \
    firestore.googleapis.com \
    pubsub.googleapis.com \
    secretmanager.googleapis.com \
    firebase.googleapis.com \
    --quiet

echo_info "APIs enabled successfully"

# ============================================
# Step 2: Create Infrastructure
# ============================================
echo_header "Step 2: Creating Infrastructure"

# Artifact Registry
echo_info "Creating Artifact Registry..."
gcloud artifacts repositories create olmocr \
    --repository-format=docker \
    --location="$REGION" \
    --description="olmOCR container images" \
    --quiet 2>/dev/null || echo_warn "Repository already exists"

# Cloud Storage
echo_info "Creating Cloud Storage bucket..."
gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://$BUCKET_NAME" 2>/dev/null || echo_warn "Bucket already exists"

# Set CORS
cat > /tmp/cors.json << 'CORS'
[{"origin": ["*"], "method": ["GET", "PUT", "POST", "DELETE", "OPTIONS"], "responseHeader": ["Content-Type", "Authorization", "Content-Length", "X-Requested-With"], "maxAgeSeconds": 3600}]
CORS
gsutil cors set /tmp/cors.json "gs://$BUCKET_NAME"
rm /tmp/cors.json

# Firestore
echo_info "Creating Firestore database..."
gcloud firestore databases create --location="$REGION" --quiet 2>/dev/null || echo_warn "Firestore already exists"

# Pub/Sub
echo_info "Creating Pub/Sub topic..."
gcloud pubsub topics create olmocr-jobs --quiet 2>/dev/null || echo_warn "Topic already exists"

# Secret Manager
echo_info "Storing Parasail API key in Secret Manager..."
if gcloud secrets describe parasail-api-key &>/dev/null; then
    echo -n "$PARASAIL_KEY" | gcloud secrets versions add parasail-api-key --data-file=- --quiet
else
    echo -n "$PARASAIL_KEY" | gcloud secrets create parasail-api-key --data-file=- --replication-policy="automatic" --quiet
fi

# Service Accounts
echo_info "Creating service accounts..."
for SA in "olmocr-backend:olmOCR Backend" "olmocr-worker:olmOCR Worker" "pubsub-invoker:Pub/Sub Invoker"; do
    ID="${SA%%:*}"
    NAME="${SA##*:}"
    gcloud iam service-accounts create "$ID" --display-name="$NAME" --quiet 2>/dev/null || true
done

# IAM bindings
echo_info "Setting up IAM permissions..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:olmocr-backend@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/storage.objectAdmin" --quiet
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:olmocr-backend@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/datastore.user" --quiet
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:olmocr-backend@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/pubsub.publisher" --quiet
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:olmocr-worker@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/storage.objectAdmin" --quiet
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:olmocr-worker@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/datastore.user" --quiet
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:olmocr-worker@${PROJECT_ID}.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor" --quiet

echo_info "Infrastructure created successfully"

# ============================================
# Step 3: Build Container Images
# ============================================
echo_header "Step 3: Building Container Images"

REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/olmocr"
cd "$SCRIPT_DIR"

echo_info "Building frontend image..."
gcloud builds submit --tag "${REGISTRY}/frontend:latest" --timeout=20m -f gcp-frontend/Dockerfile . --quiet

echo_info "Building backend image..."
gcloud builds submit --tag "${REGISTRY}/backend:latest" --timeout=20m -f gcp-backend/Dockerfile . --quiet

echo_info "Building worker image..."
gcloud builds submit --tag "${REGISTRY}/worker:latest" --timeout=30m -f gcp-worker/Dockerfile.cloudrun . --quiet

echo_info "Container images built successfully"

# ============================================
# Step 4: Deploy Services
# ============================================
echo_header "Step 4: Deploying Cloud Run Services"

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

FRONTEND_URL=$(gcloud run services describe "$FRONTEND_SERVICE" --region "$REGION" --format='value(status.url)')

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
    --service-account "olmocr-backend@${PROJECT_ID}.iam.gserviceaccount.com" \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,GCS_BUCKET=$BUCKET_NAME,PUBSUB_TOPIC=olmocr-jobs,ENVIRONMENT=production,CORS_ORIGINS=$FRONTEND_URL" \
    --quiet

BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" --region "$REGION" --format='value(status.url)')

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
    --service-account "olmocr-worker@${PROJECT_ID}.iam.gserviceaccount.com" \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,GCS_BUCKET=$BUCKET_NAME,PROCESSING_MODE=parasail,PARASAIL_MODEL=allenai/olmOCR-2-7B-1025" \
    --set-secrets "PARASAIL_API_KEY=parasail-api-key:latest" \
    --quiet

WORKER_URL=$(gcloud run services describe "$WORKER_SERVICE" --region "$REGION" --format='value(status.url)')

echo_info "Services deployed successfully"

# ============================================
# Step 5: Configure Pub/Sub Push
# ============================================
echo_header "Step 5: Configuring Pub/Sub Push Subscription"

# Grant invoker permission
gcloud run services add-iam-policy-binding "$WORKER_SERVICE" \
    --region="$REGION" \
    --member="serviceAccount:pubsub-invoker@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.invoker" \
    --quiet

# Create or update push subscription
if gcloud pubsub subscriptions describe olmocr-jobs-push --project="$PROJECT_ID" &>/dev/null; then
    echo_info "Updating existing push subscription..."
    gcloud pubsub subscriptions modify-push-config olmocr-jobs-push \
        --push-endpoint="${WORKER_URL}/process" \
        --push-auth-service-account="pubsub-invoker@${PROJECT_ID}.iam.gserviceaccount.com" \
        --quiet
else
    echo_info "Creating push subscription..."
    gcloud pubsub subscriptions create olmocr-jobs-push \
        --topic=olmocr-jobs \
        --push-endpoint="${WORKER_URL}/process" \
        --push-auth-service-account="pubsub-invoker@${PROJECT_ID}.iam.gserviceaccount.com" \
        --ack-deadline=600 \
        --quiet
fi

echo_info "Pub/Sub configured successfully"

# ============================================
# Step 6: Set up Firebase (instructions)
# ============================================
echo_header "Step 6: Firebase Setup Required"

echo ""
echo_info "Firebase setup is required for user authentication."
echo ""
echo "Please complete these steps manually:"
echo ""
echo "  1. Go to Firebase Console: https://console.firebase.google.com/"
echo "  2. Add Firebase to your GCP project: $PROJECT_ID"
echo "  3. Enable Authentication:"
echo "     - Email/Password provider"
echo "     - Google provider (optional)"
echo "  4. Get your Firebase config from Project Settings > Your Apps > Web App"
echo "  5. Update the frontend with Firebase credentials (see below)"
echo ""

# ============================================
# Deployment Complete
# ============================================
echo_header "Deployment Complete!"

echo ""
echo -e "Frontend URL:  ${GREEN}$FRONTEND_URL${NC}"
echo -e "Backend URL:   ${GREEN}$BACKEND_URL${NC}"
echo -e "Worker URL:    ${GREEN}$WORKER_URL${NC}"
echo ""
echo "Storage Bucket: gs://$BUCKET_NAME"
echo ""

# Create a quick start guide
cat > "$SCRIPT_DIR/DEPLOYED_URLS.txt" << EOF
olmOCR Deployment - $(date)

Frontend: $FRONTEND_URL
Backend:  $BACKEND_URL
Worker:   $WORKER_URL
Bucket:   gs://$BUCKET_NAME

Project:  $PROJECT_ID
Region:   $REGION

To update frontend with API URL:
1. Edit gcp-frontend/.env
2. Set VITE_API_URL=${BACKEND_URL}/api
3. Rebuild and redeploy frontend:
   gcloud builds submit --tag ${REGISTRY}/frontend:latest -f gcp-frontend/Dockerfile .
   gcloud run deploy $FRONTEND_SERVICE --image ${REGISTRY}/frontend:latest --region $REGION
EOF

echo_info "Deployment URLs saved to DEPLOYED_URLS.txt"
echo ""
echo_info "Next Steps:"
echo "  1. Set up Firebase Authentication (see instructions above)"
echo "  2. Update frontend .env with Firebase config and VITE_API_URL"
echo "  3. Rebuild and redeploy frontend with updated config"
echo ""
echo "Need help? See docs/gcp-architecture/USER_GUIDE.md"
echo ""
