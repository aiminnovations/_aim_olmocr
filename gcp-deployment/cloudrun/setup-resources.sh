#!/bin/bash
# olmOCR GCP Resource Setup Script
# Run this once before first deployment to create all required GCP resources

set -e

# ============================================
# Configuration
# ============================================
PROJECT_ID="${GCP_PROJECT_ID:-juniper-core}"
REGION="${GCP_REGION:-us-central1}"
BUCKET_NAME="olmocr-${PROJECT_ID}"

# Parasail API key (required)
PARASAIL_API_KEY="${PARASAIL_API_KEY}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================
# Validation
# ============================================
echo_info "============================================"
echo_info "olmOCR GCP Resource Setup"
echo_info "============================================"
echo_info "Project: $PROJECT_ID"
echo_info "Region: $REGION"
echo_info "Bucket: $BUCKET_NAME"
echo ""

if [ -z "$PARASAIL_API_KEY" ]; then
    echo_error "PARASAIL_API_KEY environment variable is required"
    echo "Set it with: export PARASAIL_API_KEY=psk-your-key"
    exit 1
fi

# Check gcloud authentication
if ! gcloud auth print-identity-token &> /dev/null; then
    echo_error "gcloud is not authenticated. Run: gcloud auth login"
    exit 1
fi

# ============================================
# Set project
# ============================================
echo_info "Setting GCP project to $PROJECT_ID..."
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
    iam.googleapis.com \
    --quiet

echo_info "APIs enabled"

# ============================================
# Create Artifact Registry repository
# ============================================
echo_info "Creating Artifact Registry repository..."
if gcloud artifacts repositories describe olmocr --location="$REGION" &>/dev/null; then
    echo_warn "Repository already exists"
else
    gcloud artifacts repositories create olmocr \
        --repository-format=docker \
        --location="$REGION" \
        --description="olmOCR container images"
    echo_info "Repository created"
fi

# ============================================
# Create Cloud Storage bucket
# ============================================
echo_info "Creating Cloud Storage bucket..."
if gsutil ls "gs://$BUCKET_NAME" &>/dev/null; then
    echo_warn "Bucket already exists"
else
    gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://$BUCKET_NAME"
    echo_info "Bucket created"
fi

# Set CORS for frontend uploads
echo_info "Configuring CORS for bucket..."
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
rm /tmp/cors.json
echo_info "CORS configured"

# ============================================
# Create Firestore database
# ============================================
echo_info "Creating Firestore database..."
if gcloud firestore databases describe --database="(default)" &>/dev/null; then
    echo_warn "Firestore database already exists"
else
    gcloud firestore databases create --location="$REGION" --quiet
    echo_info "Firestore database created"
fi

# ============================================
# Create Pub/Sub topic
# ============================================
echo_info "Creating Pub/Sub topic..."
if gcloud pubsub topics describe olmocr-jobs &>/dev/null; then
    echo_warn "Topic already exists"
else
    gcloud pubsub topics create olmocr-jobs
    echo_info "Topic created"
fi

# ============================================
# Store Parasail API key in Secret Manager
# ============================================
echo_info "Storing Parasail API key in Secret Manager..."
if gcloud secrets describe parasail-api-key &>/dev/null; then
    echo_warn "Secret already exists, updating..."
    echo -n "$PARASAIL_API_KEY" | gcloud secrets versions add parasail-api-key --data-file=-
else
    echo -n "$PARASAIL_API_KEY" | gcloud secrets create parasail-api-key \
        --data-file=- \
        --replication-policy="automatic"
fi
echo_info "Secret stored"

# ============================================
# Create service accounts
# ============================================
echo_info "Creating service accounts..."

# Pub/Sub invoker service account
if gcloud iam service-accounts describe "pubsub-invoker@${PROJECT_ID}.iam.gserviceaccount.com" &>/dev/null; then
    echo_warn "pubsub-invoker service account already exists"
else
    gcloud iam service-accounts create pubsub-invoker \
        --display-name="Pub/Sub Cloud Run Invoker"
    echo_info "pubsub-invoker service account created"
fi

# Backend service account
if gcloud iam service-accounts describe "olmocr-backend@${PROJECT_ID}.iam.gserviceaccount.com" &>/dev/null; then
    echo_warn "olmocr-backend service account already exists"
else
    gcloud iam service-accounts create olmocr-backend \
        --display-name="olmOCR Backend Service"
    echo_info "olmocr-backend service account created"
fi

# Worker service account
if gcloud iam service-accounts describe "olmocr-worker@${PROJECT_ID}.iam.gserviceaccount.com" &>/dev/null; then
    echo_warn "olmocr-worker service account already exists"
else
    gcloud iam service-accounts create olmocr-worker \
        --display-name="olmOCR Worker Service"
    echo_info "olmocr-worker service account created"
fi

# ============================================
# Grant IAM permissions
# ============================================
echo_info "Granting IAM permissions..."

# Backend permissions
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:olmocr-backend@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin" \
    --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:olmocr-backend@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/datastore.user" \
    --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:olmocr-backend@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher" \
    --quiet

# Worker permissions
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:olmocr-worker@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin" \
    --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:olmocr-worker@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/datastore.user" \
    --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:olmocr-worker@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet

echo_info "IAM permissions granted"

# ============================================
# Summary
# ============================================
echo ""
echo_info "============================================"
echo_info "Resource Setup Complete!"
echo_info "============================================"
echo ""
echo "Resources created:"
echo "  - Artifact Registry: ${REGION}-docker.pkg.dev/${PROJECT_ID}/olmocr"
echo "  - Cloud Storage: gs://${BUCKET_NAME}"
echo "  - Firestore: (default) database"
echo "  - Pub/Sub Topic: olmocr-jobs"
echo "  - Secret: parasail-api-key"
echo "  - Service Accounts: pubsub-invoker, olmocr-backend, olmocr-worker"
echo ""
echo "Next steps:"
echo "  1. Deploy the application:"
echo "     gcloud builds submit --config gcp-deployment/cloudrun/cloudbuild.yaml ."
echo ""
echo "  2. Or use the deploy script:"
echo "     ./gcp-deployment/cloudrun/deploy.sh"
echo ""
