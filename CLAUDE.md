# CLAUDE.md - AI Assistant Guide for olmOCR

## Project Overview

**olmOCR** is an enterprise-grade PDF-to-Markdown conversion toolkit using vision language models for OCR. Developed by Allen Institute for AI.

- **Version**: 0.4.6
- **License**: Apache 2.0
- **Demo**: https://olmocr.allenai.org

## Architecture

This is a **monorepo** with three deployable applications:

1. **Core Library** (`olmocr/`) - Python package for GPU-based OCR pipeline
2. **GCP Full-Stack** (`gcp-backend/` + `gcp-frontend/`) - Scalable cloud app with Firebase auth
3. **Simple Batch Processor** (`simple-ocr-app/`) - Lightweight standalone app (recommended for most users)

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Zustand |
| Backend | FastAPI, Python 3.11+, Pydantic |
| Database | Firestore (cloud) / SQLite (local) |
| Storage | Google Cloud Storage |
| Auth | Firebase Authentication |
| Queue | Google Pub/Sub |
| ML | PyTorch, vLLM, Qwen2.5-VL models |

## Directory Structure

```
olmocr/                  # Core OCR library (pip-installable)
├── pipeline.py          # Main processing pipeline
├── bench/               # Benchmark suite (7k+ test cases)
├── train/               # Model training (SFT + GRPO)
└── filter/              # Language/spam filtering

gcp-backend/             # FastAPI backend
├── app/main.py          # App initialization
├── app/routers/         # API endpoints (upload, processing, browse, download)
├── app/services/        # Business logic (storage, firestore)
└── app/middleware/      # Auth middleware

gcp-frontend/            # React frontend
├── src/components/      # Reusable UI components
├── src/pages/           # Route handlers
├── src/services/        # API clients
└── src/store/           # Zustand state management

simple-ocr-app/          # Standalone batch processor
└── app.py               # Single-file FastAPI app with Parasail integration
```

## Quick Start Commands

### Simple Batch Processor (Local Dev)
```bash
cd simple-ocr-app
pip install -r requirements.txt
export PARASAIL_API_KEY="your-key"
python app.py
# Open http://localhost:8080
```

### Full Stack (Docker)
```bash
docker-compose up -d
# Frontend: :3000, Backend: :8000, Firestore Emulator: :8080
```

### Core Library
```bash
pip install olmocr[gpu]
python -m olmocr.pipeline ./workspace --markdown --pdfs input/*.pdf
```

## Development Commands

### Backend
```bash
cd gcp-backend
pytest tests/ -v --cov=app    # Tests
python -m uvicorn app.main:app --reload  # Dev server
```

### Frontend
```bash
cd gcp-frontend
npm run dev          # Dev server (:5173)
npm test             # Vitest
npm run build        # Production build
npm run lint         # ESLint
```

### Core Library
```bash
make run-checks      # isort, black, ruff, mypy, pytest
make docs            # Sphinx docs
pytest tests/ -v --cov=olmocr
```

## Environment Variables

### Required
| Variable | Purpose |
|----------|---------|
| `PARASAIL_API_KEY` | OCR API key from parasail.io |
| `GCP_PROJECT_ID` | GCP project (for cloud deployment) |

### Optional
```bash
GCS_BUCKET="bucket-name"        # Cloud storage bucket
MAX_CONCURRENT_PAGES=5          # Parallel page processing
MAX_CONCURRENT_JOBS=3           # Parallel job processing
RENDER_DPI=120                  # PDF render quality
IMAGE_QUALITY=85                # JPEG compression
PORT=8080                       # Server port
```

## API Patterns

### Backend (FastAPI)
- **Router-based**: Separate files per domain in `routers/`
- **Service layer**: Business logic in `services/`
- **Dependency injection**: `Depends()` for auth via `get_current_user`
- **Pydantic models**: Strong typing in `models/`

### Frontend (React)
- **File-based routing**: React Router
- **State**: Zustand stores
- **TypeScript**: Strong typing throughout
- **Testing**: Vitest + React Testing Library

## Key API Endpoints

```
POST /api/v1/upload/init        # Get signed upload URL
POST /api/v1/process            # Create processing job
GET  /api/v1/process/{job_id}   # Job status
GET  /api/v1/download/{job_id}  # Download result
GET  /api/v1/browse             # List files/folders
```

## Testing

```bash
# All tests
./run_all_tests.sh

# By component
pytest tests/ -v --cov=olmocr           # Core
cd gcp-backend && pytest tests/ -v       # Backend
cd gcp-frontend && npm test              # Frontend
cd simple-ocr-app && pytest tests/       # Simple app

# Skip non-CI tests
pytest -m 'not nonci'
```

## Important Notes

1. **Three apps**: Don't confuse `gcp-backend`/`gcp-frontend` with `simple-ocr-app`
2. **GPU required**: Core pipeline needs NVIDIA GPU (RTX 4090, A100, H100+)
3. **External API**: Requires Parasail API key for OCR inference
4. **Large deps**: vLLM + PyTorch + models ~30GB
5. **Sensitive files**: `.env` files contain API keys (not in git)
6. **Default model**: `allenai/olmOCR-2-7B-1025-FP8`

## Code Style

- Python: isort, black, ruff, mypy
- TypeScript: ESLint, Prettier
- Commits: Conventional commits preferred
