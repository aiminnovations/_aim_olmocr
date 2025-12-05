#!/bin/bash
#
# Run olmOCR Batch Processor
#

cd "$(dirname "$0")/simple-ocr-app"

# Activate virtual environment if it exists
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
python3 app.py "$@"
