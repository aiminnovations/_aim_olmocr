#!/bin/bash
set -e

echo "========================================"
echo "Running olmOCR Test Suite"
echo "========================================"

# Core library tests
echo ""
echo "1. Testing Core Library (olmocr)..."
if [ -d "tests" ]; then
    pytest tests/ -v --cov=olmocr --cov-report=term-missing
    echo "✓ Core library tests passed"
else
    echo "⊘ No core library tests found, skipping"
fi

# Backend tests
echo ""
echo "2. Testing Backend (gcp-backend)..."
cd gcp-backend
if [ -d "tests" ]; then
    pytest tests/ -v --cov=app
    echo "✓ Backend tests passed"
else
    echo "⊘ No backend tests found, skipping"
fi
cd ..

# Frontend tests
echo ""
echo "3. Testing Frontend (gcp-frontend)..."
cd gcp-frontend
if [ -f "package.json" ]; then
    npm test -- --run
    echo "✓ Frontend tests passed"
else
    echo "⊘ No frontend tests configured, skipping"
fi
cd ..

# Simple OCR app tests
echo ""
echo "4. Testing Simple OCR App..."
cd simple-ocr-app
if [ -d "tests" ]; then
    pytest tests/ -v --cov
    echo "✓ Simple OCR app tests passed"
else
    echo "⊘ No simple OCR app tests found, skipping"
fi
cd ..

echo ""
echo "========================================"
echo "✓ All Tests Complete!"
echo "========================================"
