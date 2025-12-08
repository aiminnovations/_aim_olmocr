#!/bin/bash

#####################################################################
#  olmOCR - ONE-COMMAND DEPLOYMENT                                  #
#  This script does EVERYTHING. Just run it.                        #
#####################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

clear
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}olmOCR - ONE-COMMAND DEPLOYMENT${NC}                            ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  This script will:                                            ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    1. Set up Google Cloud                                     ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    2. Deploy your OCR app                                     ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}    3. Give you a working URL                                  ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${YELLOW}You only need to answer 2 questions.${NC}                      ${CYAN}║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}ERROR: gcloud CLI is not installed.${NC}"
    echo ""
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    echo ""
    exit 1
fi

# Question 1: Parasail API Key
echo -e "${BOLD}Question 1 of 2:${NC} Get your Parasail API key"
echo ""
echo "Visit: ${BLUE}https://parasail.io${NC}"
echo "Sign up (free), then copy your API key."
echo ""
read -p "Paste your Parasail API key here: " PARASAIL_KEY

if [ -z "$PARASAIL_KEY" ]; then
    echo -e "${RED}Error: API key is required${NC}"
    exit 1
fi

# Question 2: Project name
echo ""
echo -e "${BOLD}Question 2 of 2:${NC} Choose a project name"
echo ""
echo "This will be your GCP project ID (lowercase, no spaces)"
echo "Example: my-ocr-app, company-pdf-reader, etc."
echo ""
read -p "Project name: " PROJECT_NAME

if [ -z "$PROJECT_NAME" ]; then
    PROJECT_NAME="olmocr-$(date +%s)"
    echo "Using auto-generated name: $PROJECT_NAME"
fi

# Convert to lowercase and replace spaces
PROJECT_NAME=$(echo "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}Ready to deploy!${NC}"
echo ""
echo "  Project Name: $PROJECT_NAME"
echo "  API Key:      ${PARASAIL_KEY:0:10}..."
echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo ""
read -p "Press ENTER to start deployment (or Ctrl+C to cancel)..."

echo ""
echo -e "${BLUE}[1/6]${NC} Setting up Google Cloud project..."

# Check if project exists, create if not
if ! gcloud projects describe $PROJECT_NAME &> /dev/null; then
    echo "  Creating project $PROJECT_NAME..."
    gcloud projects create $PROJECT_NAME --name="olmOCR App" --quiet
fi

gcloud config set project $PROJECT_NAME --quiet
echo -e "${GREEN}✓${NC} Project ready"

echo ""
echo -e "${BLUE}[2/6]${NC} Enabling required Google Cloud services..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    storage.googleapis.com \
    firestore.googleapis.com \
    --quiet

echo -e "${GREEN}✓${NC} Services enabled"

echo ""
echo -e "${BLUE}[3/6]${NC} Creating storage bucket..."

# Add timestamp to make bucket name unique
TIMESTAMP=$(date +%s)
BUCKET_NAME="${PROJECT_NAME}-pdfs-${TIMESTAMP}"

echo "  Checking billing status..."
if ! gcloud beta billing projects describe $PROJECT_NAME &> /dev/null; then
    echo ""
    echo -e "${RED}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  BILLING NOT ENABLED${NC}"
    echo -e "${RED}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Google Cloud requires billing to be enabled."
    echo "  Don't worry - you won't be charged much:"
    echo "    - First 5GB storage: FREE"
    echo "    - Cloud Run: Pay only when used (cents per request)"
    echo ""
    echo "  Enable billing:"
    echo "  1. Go to: ${BLUE}https://console.cloud.google.com/billing${NC}"
    echo "  2. Link a billing account to project: ${BOLD}$PROJECT_NAME${NC}"
    echo "  3. Run this script again"
    echo ""
    echo -e "${RED}════════════════════════════════════════════════════════════════${NC}"
    exit 1
fi

echo "  Creating bucket: $BUCKET_NAME"
if ! gsutil mb -l us-central1 gs://$BUCKET_NAME 2>&1; then
    echo "  Retrying with different name..."
    BUCKET_NAME="${PROJECT_NAME}-pdfs-$(uuidgen | cut -d'-' -f1)"
    gsutil mb -l us-central1 gs://$BUCKET_NAME
fi
echo -e "${GREEN}✓${NC} Storage bucket ready: $BUCKET_NAME"

echo ""
echo -e "${BLUE}[4/6]${NC} Creating Firestore database..."
if ! gcloud firestore databases describe --database="(default)" &> /dev/null 2>&1; then
    gcloud firestore databases create \
        --location=us-central1 \
        --type=firestore-native \
        --quiet
fi
echo -e "${GREEN}✓${NC} Database ready"

echo ""
echo -e "${BLUE}[5/6]${NC} Configuring the application..."

# Create .env file
cat > simple-ocr-app/.env << EOF
# olmOCR Configuration
PARASAIL_API_KEY=$PARASAIL_KEY
PORT=8080
GCP_PROJECT_ID=$PROJECT_NAME
GCS_BUCKET=$BUCKET_NAME
REGION=us-central1
MAX_CONCURRENT_PAGES=100
MAX_CONCURRENT_JOBS=10
RENDER_DPI=300
IMAGE_QUALITY=85
EOF

echo -e "${GREEN}✓${NC} Configuration complete"

echo ""
echo -e "${BLUE}[6/6]${NC} Deploying to Cloud Run..."
echo "  This may take 3-5 minutes..."

cd simple-ocr-app

# Deploy to Cloud Run
gcloud run deploy olmocr \
    --source . \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --set-env-vars "PARASAIL_API_KEY=$PARASAIL_KEY,GCP_PROJECT_ID=$PROJECT_NAME,GCS_BUCKET=$BUCKET_NAME,REGION=us-central1" \
    --quiet

# Get the URL
SERVICE_URL=$(gcloud run services describe olmocr --region us-central1 --format 'value(status.url)')

cd ..

echo ""
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}${GREEN}✓ DEPLOYMENT COMPLETE!${NC}                                     ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                                               ${GREEN}║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}Your olmOCR app is live at:${NC}"
echo ""
echo -e "${CYAN}${BOLD}${SERVICE_URL}${NC}"
echo ""
echo ""
echo -e "${BOLD}How to use:${NC}"
echo "  1. Click the URL above (or copy/paste to browser)"
echo "  2. Drag and drop a PDF file"
echo "  3. Wait for processing"
echo "  4. Download your Markdown result"
echo ""
echo -e "${BOLD}Cost estimate:${NC} ~\$0.05 - \$0.50 per document (pay only when used)"
echo ""
echo -e "${YELLOW}Save this URL - it's your permanent app address!${NC}"
echo ""
echo ""
echo -e "${BOLD}Need help?${NC}"
echo "  View logs: gcloud run services logs read olmocr --region us-central1"
echo "  Delete app: gcloud run services delete olmocr --region us-central1"
echo ""
