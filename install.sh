#!/bin/bash
#
# olmOCR Easy Installer
#
# This script installs olmOCR and its dependencies for local use.
# Works on Linux, macOS, and Windows (WSL).
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}     olmOCR Easy Installer v1.0${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if running from the correct directory
if [ ! -f "simple-ocr-app/app.py" ]; then
    echo -e "${RED}Error: Please run this script from the olmocr root directory.${NC}"
    echo "  cd /path/to/_aim_olmocr"
    echo "  ./install.sh"
    exit 1
fi

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
echo -e "${GREEN}Detected OS:${NC} $OS"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install system dependencies
install_system_deps() {
    echo -e "${YELLOW}Installing system dependencies...${NC}"

    if [[ "$OS" == "linux" ]]; then
        if command_exists apt-get; then
            sudo apt-get update -qq
            sudo apt-get install -y -qq poppler-utils python3 python3-pip python3-venv
        elif command_exists yum; then
            sudo yum install -y -q poppler-utils python3 python3-pip
        elif command_exists dnf; then
            sudo dnf install -y -q poppler-utils python3 python3-pip
        elif command_exists pacman; then
            sudo pacman -S --noconfirm poppler python python-pip
        else
            echo -e "${YELLOW}Could not detect package manager. Please install poppler-utils manually.${NC}"
        fi
    elif [[ "$OS" == "macos" ]]; then
        if command_exists brew; then
            brew install poppler python3 2>/dev/null || true
        else
            echo -e "${YELLOW}Homebrew not found. Please install poppler:${NC}"
            echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            echo "  brew install poppler"
        fi
    else
        echo -e "${YELLOW}Please ensure poppler-utils and Python 3.9+ are installed.${NC}"
    fi

    echo -e "${GREEN}System dependencies installed.${NC}"
}

# Check Python version
check_python() {
    echo -e "${YELLOW}Checking Python...${NC}"

    PYTHON_CMD=""
    for cmd in python3 python; do
        if command_exists "$cmd"; then
            VERSION=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
            MAJOR=$(echo $VERSION | cut -d. -f1)
            MINOR=$(echo $VERSION | cut -d. -f2)

            if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 9 ]; then
                PYTHON_CMD="$cmd"
                echo -e "${GREEN}Found Python $VERSION ($cmd)${NC}"
                break
            fi
        fi
    done

    if [ -z "$PYTHON_CMD" ]; then
        echo -e "${RED}Error: Python 3.9+ is required but not found.${NC}"
        echo "Please install Python 3.9 or later from https://python.org"
        exit 1
    fi

    export PYTHON_CMD
}

# Create virtual environment and install dependencies
setup_venv() {
    echo ""
    echo -e "${YELLOW}Setting up Python virtual environment...${NC}"

    cd simple-ocr-app

    # Create venv if it doesn't exist
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
        echo -e "${GREEN}Created virtual environment.${NC}"
    else
        echo -e "${GREEN}Virtual environment already exists.${NC}"
    fi

    # Activate venv
    if [[ "$OS" == "windows" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi

    # Upgrade pip
    pip install --upgrade pip -q

    # Install dependencies
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    pip install -r requirements.txt -q

    echo -e "${GREEN}Python dependencies installed.${NC}"

    cd ..
}

# Create run script
create_run_script() {
    echo ""
    echo -e "${YELLOW}Creating run script...${NC}"

    cat > run.sh << 'EOF'
#!/bin/bash
#
# Run olmOCR Batch Processor
#

cd "$(dirname "$0")/simple-ocr-app"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# Check for API key
if [ -z "$PARASAIL_API_KEY" ]; then
    echo ""
    echo "============================================"
    echo "  PARASAIL_API_KEY not set!"
    echo "============================================"
    echo ""
    echo "To process PDFs, you need a Parasail API key."
    echo ""
    echo "1. Get a free API key from: https://parasail.io"
    echo "2. Then run with:"
    echo ""
    echo "   export PARASAIL_API_KEY='your-key-here'"
    echo "   ./run.sh"
    echo ""
    echo "Starting anyway (you can set the key later)..."
    echo ""
fi

# Run the app
python app.py "$@"
EOF

    chmod +x run.sh

    # Also create a Windows batch file
    cat > run.bat << 'EOF'
@echo off
cd /d "%~dp0\simple-ocr-app"

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

if "%PARASAIL_API_KEY%"=="" (
    echo.
    echo ============================================
    echo   PARASAIL_API_KEY not set!
    echo ============================================
    echo.
    echo To process PDFs, you need a Parasail API key.
    echo.
    echo 1. Get a free API key from: https://parasail.io
    echo 2. Then run with:
    echo.
    echo    set PARASAIL_API_KEY=your-key-here
    echo    run.bat
    echo.
    echo Starting anyway...
    echo.
)

python app.py %*
EOF

    echo -e "${GREEN}Created run.sh and run.bat${NC}"
}

# Main installation
echo -e "${YELLOW}Step 1/4: Installing system dependencies...${NC}"
install_system_deps

echo ""
echo -e "${YELLOW}Step 2/4: Checking Python...${NC}"
check_python

echo ""
echo -e "${YELLOW}Step 3/4: Setting up virtual environment...${NC}"
setup_venv

echo ""
echo -e "${YELLOW}Step 4/4: Creating run scripts...${NC}"
create_run_script

# Done!
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}     Installation Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "To start olmOCR:"
echo ""
echo -e "  ${BLUE}1. Get a Parasail API key from:${NC} https://parasail.io"
echo ""
echo -e "  ${BLUE}2. Set your API key:${NC}"
echo "     export PARASAIL_API_KEY='your-key-here'"
echo ""
echo -e "  ${BLUE}3. Run the app:${NC}"
echo "     ./run.sh"
echo ""
echo -e "  ${BLUE}4. Open in browser:${NC} http://localhost:8080"
echo ""
echo -e "${YELLOW}Note:${NC} Your processed files will be saved in:"
echo "      simple-ocr-app/data/outputs/"
echo ""
