#!/bin/bash
#
# olmOCR Installer for Mac/Linux
# Usage: ./setup.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}olmOCR Automated Installer${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Configuration
export GCP_PROJECT_ID="${GCP_PROJECT_ID:-juniper-core}"
export PARASAIL_API_KEY="${PARASAIL_API_KEY:-psk-aimiwsstmt1A-JBSW3y4jAxHjEvwMvScP}"
export GCP_REGION="${GCP_REGION:-us-central1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}[OK]${NC} Python: $PYTHON_VERSION"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PYTHON_VERSION=$(python --version)
    echo -e "${GREEN}[OK]${NC} Python: $PYTHON_VERSION"
else
    echo -e "${RED}[ERROR]${NC} Python not found"
    echo ""
    echo "Please install Python 3.8+:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  brew install python3"
    else
        echo "  sudo apt install python3  # Debian/Ubuntu"
        echo "  sudo yum install python3  # CentOS/RHEL"
    fi
    exit 1
fi

# Check gcloud
if command -v gcloud &> /dev/null; then
    GCLOUD_VERSION=$(gcloud --version 2>&1 | head -1)
    echo -e "${GREEN}[OK]${NC} Google Cloud SDK: $GCLOUD_VERSION"
else
    echo -e "${YELLOW}[INFO]${NC} Google Cloud SDK not found"
    echo ""
    echo "Installing Google Cloud SDK..."

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install --cask google-cloud-sdk
        else
            curl https://sdk.cloud.google.com | bash
            exec -l $SHELL
        fi
    else
        # Linux
        curl https://sdk.cloud.google.com | bash
        exec -l $SHELL
    fi

    # Source the SDK
    if [ -f "$HOME/google-cloud-sdk/path.bash.inc" ]; then
        source "$HOME/google-cloud-sdk/path.bash.inc"
    fi

    if command -v gcloud &> /dev/null; then
        echo -e "${GREEN}[OK]${NC} Google Cloud SDK installed"
    else
        echo -e "${RED}[ERROR]${NC} Google Cloud SDK installation failed"
        echo "Please install manually: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
fi

# Check Firebase CLI (optional)
if command -v firebase &> /dev/null; then
    FIREBASE_VERSION=$(firebase --version)
    echo -e "${GREEN}[OK]${NC} Firebase CLI: $FIREBASE_VERSION"
else
    echo -e "${YELLOW}[INFO]${NC} Firebase CLI not found (will use gcloud fallback)"

    # Try to install
    if command -v npm &> /dev/null; then
        echo "Installing Firebase CLI via npm..."
        npm install -g firebase-tools 2>/dev/null || true
    fi
fi

echo ""
echo -e "${BLUE}Starting installation...${NC}"
echo ""

# Make the Python script executable
chmod +x "$SCRIPT_DIR/install.py"

# Run the Python installer
$PYTHON_CMD "$SCRIPT_DIR/install.py"

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo -e "${RED}Installation encountered an error.${NC}"
    exit $EXIT_CODE
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
