#!/bin/bash

#
# olmOCR GCP Setup Script
# This script creates all required GCP resources for the olmOCR web application
#
# Usage:
#   ./setup-gcp.sh [PROJECT_ID] [REGION]
#
# Example:
#   ./setup-gcp.sh olmocr-prod us-central1
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEFAULT_REGION="us-central1"
DEFAULT_ZONE="us-central1-a"

# Print with color
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is required but not installed."
        exit 1
    fi
}

# Banner
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                   olmOCR GCP Setup Script                     ║"
echo "║                                                               ║"
echo "║  This script will create all required GCP resources for      ║"
echo "║  running the olmOCR web application.                         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check prerequisites
print_info "Checking prerequisites..."
check_command gcloud
check_command gsutil
check_command kubectl
print_success "All prerequisites found"

# Get project ID
if [ -n "$1" ]; then
    PROJECT_ID="$1"
else
    read -p "Enter GCP Project ID (or press Enter to create new): " PROJECT_ID
    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID="olmocr-$(date +%s)"
        print_info "Generated project ID: $PROJECT_ID"
    fi
fi

# Get region
REGION="${2:-$DEFAULT_REGION}"
ZONE="${DEFAULT_ZONE}"

print_info "Configuration:"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Zone: $ZONE"
echo ""

read -p "Continue with this configuration? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Setup cancelled"
    exit 0
fi

# ============================================
# Step 1: Create or select project
# ============================================
print_info "Step 1: Setting up GCP project..."

# Check if project exists
if gcloud projects describe $PROJECT_ID &> /dev/null; then
    print_info "Project $PROJECT_ID exists, selecting it..."
else
    print_info "Creating project $PROJECT_ID..."
    gcloud projects create $PROJECT_ID --name="olmOCR Production"
fi

gcloud config set project $PROJECT_ID
print_success "Project configured: $PROJECT_ID"

# ============================================
# Step 2: Enable APIs
# ============================================
print_info "Step 2: Enabling required APIs..."

APIS=(
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "container.googleapis.com"
    "containerregistry.googleapis.com"
    "storage.googleapis.com"
    "firestore.googleapis.com"
    "pubsub.googleapis.com"
    "secretmanager.googleapis.com"
    "cloudresourcemanager.googleapis.com"
    "iam.googleapis.com"
    "compute.googleapis.com"
    "artifactregistry.googleapis.com"
)

for api in "${APIS[@]}"; do
    print_info "  Enabling $api..."
    gcloud services enable $api --quiet
done

print_success "All APIs enabled"

# ============================================
# Step 3: Create service accounts
# ============================================
print_info "Step 3: Creating service accounts..."

# Backend service account
if ! gcloud iam service-accounts describe olmocr-backend@$PROJECT_ID.iam.gserviceaccount.com &> /dev/null 2>&1; then
    gcloud iam service-accounts create olmocr-backend \
        --display-name="olmOCR Backend API"
    print_success "Created backend service account"
else
    print_info "Backend service account already exists"
fi

# Worker service account
if ! gcloud iam service-accounts describe olmocr-worker@$PROJECT_ID.iam.gserviceaccount.com &> /dev/null 2>&1; then
    gcloud iam service-accounts create olmocr-worker \
        --display-name="olmOCR Processing Worker"
    print_success "Created worker service account"
else
    print_info "Worker service account already exists"
fi

# ============================================
# Step 4: Assign IAM roles
# ============================================
print_info "Step 4: Assigning IAM roles..."

# Backend roles
BACKEND_ROLES=(
    "roles/storage.objectAdmin"
    "roles/pubsub.publisher"
    "roles/datastore.user"
    "roles/secretmanager.secretAccessor"
)

for role in "${BACKEND_ROLES[@]}"; do
    print_info "  Granting $role to backend..."
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:olmocr-backend@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="$role" \
        --condition=None \
        --quiet
done

# Worker roles
WORKER_ROLES=(
    "roles/storage.objectAdmin"
    "roles/pubsub.subscriber"
    "roles/datastore.user"
)

for role in "${WORKER_ROLES[@]}"; do
    print_info "  Granting $role to worker..."
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:olmocr-worker@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="$role" \
        --condition=None \
        --quiet
done

print_success "IAM roles assigned"

# ============================================
# Step 5: Create Cloud Storage bucket
# ============================================
print_info "Step 5: Creating Cloud Storage bucket..."

BUCKET_NAME="olmocr-$PROJECT_ID"

if ! gsutil ls -b gs://$BUCKET_NAME &> /dev/null 2>&1; then
    gsutil mb -l $REGION gs://$BUCKET_NAME

    # Set CORS
    cat > /tmp/cors.json << 'CORS_EOF'
[
  {
    "origin": ["*"],
    "method": ["GET", "PUT", "POST", "DELETE", "HEAD"],
    "responseHeader": ["Content-Type", "Content-Length", "Content-Range", "Content-Disposition"],
    "maxAgeSeconds": 3600
  }
]
CORS_EOF
    gsutil cors set /tmp/cors.json gs://$BUCKET_NAME

    # Set lifecycle policy
    cat > /tmp/lifecycle.json << 'LIFECYCLE_EOF'
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {
        "age": 7,
        "matchesPrefix": ["users/"]
      }
    }
  ]
}
LIFECYCLE_EOF
    gsutil lifecycle set /tmp/lifecycle.json gs://$BUCKET_NAME

    print_success "Created bucket: $BUCKET_NAME"
else
    print_info "Bucket $BUCKET_NAME already exists"
fi

# ============================================
# Step 6: Create Firestore database
# ============================================
print_info "Step 6: Creating Firestore database..."

if ! gcloud firestore databases describe --database="(default)" &> /dev/null 2>&1; then
    gcloud firestore databases create \
        --location=$REGION \
        --type=firestore-native \
        --quiet
    print_success "Created Firestore database"
else
    print_info "Firestore database already exists"
fi

# ============================================
# Step 7: Create Pub/Sub resources
# ============================================
print_info "Step 7: Creating Pub/Sub resources..."

# Create topic
if ! gcloud pubsub topics describe olmocr-jobs &> /dev/null 2>&1; then
    gcloud pubsub topics create olmocr-jobs
    print_success "Created Pub/Sub topic: olmocr-jobs"
else
    print_info "Pub/Sub topic olmocr-jobs already exists"
fi

# Create subscription
if ! gcloud pubsub subscriptions describe olmocr-jobs-sub &> /dev/null 2>&1; then
    gcloud pubsub subscriptions create olmocr-jobs-sub \
        --topic=olmocr-jobs \
        --ack-deadline=600 \
        --message-retention-duration=1h
    print_success "Created Pub/Sub subscription: olmocr-jobs-sub"
else
    print_info "Pub/Sub subscription olmocr-jobs-sub already exists"
fi

# ============================================
# Step 8: Create GKE cluster (optional)
# ============================================
read -p "Create GKE cluster with GPU support? This will incur costs. (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Step 8: Creating GKE cluster..."

    if ! gcloud container clusters describe olmocr-cluster --zone=$ZONE &> /dev/null 2>&1; then
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

        # Get credentials
        gcloud container clusters get-credentials olmocr-cluster --zone=$ZONE

        # Install NVIDIA drivers
        kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded.yaml

        # Create namespace
        kubectl create namespace olmocr || true

        print_success "Created GKE cluster with GPU support"
    else
        print_info "GKE cluster olmocr-cluster already exists"
        gcloud container clusters get-credentials olmocr-cluster --zone=$ZONE
    fi
else
    print_info "Skipping GKE cluster creation"
fi

# ============================================
# Summary
# ============================================
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    Setup Complete!                            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
print_success "All GCP resources have been created!"
echo ""
echo "Resource Summary:"
echo "  Project ID:      $PROJECT_ID"
echo "  Region:          $REGION"
echo "  Storage Bucket:  gs://$BUCKET_NAME"
echo "  Firestore:       (default) database"
echo "  Pub/Sub Topic:   olmocr-jobs"
echo "  Pub/Sub Sub:     olmocr-jobs-sub"
echo ""
echo "Service Accounts:"
echo "  Backend: olmocr-backend@$PROJECT_ID.iam.gserviceaccount.com"
echo "  Worker:  olmocr-worker@$PROJECT_ID.iam.gserviceaccount.com"
echo ""
echo "Next Steps:"
echo "  1. Set up Firebase Authentication:"
echo "     firebase projects:addfirebase $PROJECT_ID"
echo ""
echo "  2. Create .env files with the following values:"
echo "     GCP_PROJECT_ID=$PROJECT_ID"
echo "     GCS_BUCKET=$BUCKET_NAME"
echo "     REGION=$REGION"
echo ""
echo "  3. Deploy the application:"
echo "     gcloud builds submit --config gcp-deployment/cloudbuild.yaml"
echo ""
