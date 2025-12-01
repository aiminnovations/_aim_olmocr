#!/bin/bash
#
# Deploy olmOCR Simple Batch Processor to Cloud Run with Firestore
# Run this to get a public URL for your OCR app
#

set -e

PROJECT_ID="${GCP_PROJECT_ID:-juniper-core}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="olmocr-simple"
PARASAIL_KEY="${PARASAIL_API_KEY:-psk-aimiwsstmt1A-JBSW3y4jAxHjEvwMvScP}"
GCS_BUCKET_NAME="${GCS_BUCKET:-${PROJECT_ID}-olmocr-pdfs}"

echo "============================================"
echo "Deploying olmOCR Simple Batch Processor"
echo "============================================"
echo ""
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "GCS Bucket: $GCS_BUCKET_NAME"
echo ""

# Check auth
if ! gcloud auth print-identity-token &> /dev/null; then
    echo "Not authenticated. Running: gcloud auth login"
    gcloud auth login
fi

# Set project
gcloud config set project "$PROJECT_ID"

# Enable APIs
echo "Enabling APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    firestore.googleapis.com \
    storage.googleapis.com \
    --quiet

# Create Firestore database if it doesn't exist
echo "Setting up Firestore..."
if ! gcloud firestore databases describe --database="(default)" &> /dev/null; then
    echo "Creating Firestore database..."
    gcloud firestore databases create --location="$REGION" --quiet || true
fi

# Create GCS bucket if it doesn't exist
echo "Setting up Cloud Storage..."
if ! gcloud storage buckets describe "gs://$GCS_BUCKET_NAME" &> /dev/null; then
    echo "Creating GCS bucket: $GCS_BUCKET_NAME"
    gcloud storage buckets create "gs://$GCS_BUCKET_NAME" \
        --location="$REGION" \
        --uniform-bucket-level-access \
        --quiet || true
fi

# Build and deploy
echo ""
echo "Building and deploying (this takes 3-5 minutes)..."
echo ""

cd "$(dirname "$0")"

gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 600 \
    --set-env-vars "PARASAIL_API_KEY=$PARASAIL_KEY,GCP_PROJECT_ID=$PROJECT_ID,GCS_BUCKET=$GCS_BUCKET_NAME" \
    --quiet

# Get URL
URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')

echo ""
echo "============================================"
echo "Deployment Complete!"
echo "============================================"
echo ""
echo "Your app is live at:"
echo ""
echo "  $URL"
echo ""
echo "Backend Services:"
echo "  - Firestore: https://console.cloud.google.com/firestore/databases/-default-/data?project=$PROJECT_ID"
echo "  - GCS Bucket: https://console.cloud.google.com/storage/browser/$GCS_BUCKET_NAME?project=$PROJECT_ID"
echo ""
echo "Open the URL in your browser to start processing PDFs!"
echo ""
