#!/bin/bash
#
# Deploy olmOCR Simple Batch Processor to Cloud Run
# Run this to get a public URL for your OCR app
#

set -e

PROJECT_ID="${GCP_PROJECT_ID:-juniper-core}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="olmocr-simple"
PARASAIL_KEY="${PARASAIL_API_KEY:-psk-aimiwsstmt1A-JBSW3y4jAxHjEvwMvScP}"

echo "============================================"
echo "Deploying olmOCR Simple Batch Processor"
echo "============================================"
echo ""
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
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
gcloud services enable run.googleapis.com cloudbuild.googleapis.com --quiet

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
    --set-env-vars "PARASAIL_API_KEY=$PARASAIL_KEY" \
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
echo "Open this URL in your browser to start processing PDFs!"
echo ""
