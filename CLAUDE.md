# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a fork of [olmOCR](https://github.com/allenai/olmocr) by Allen AI, extended with Google Cloud Platform (GCP) deployment infrastructure. The project converts PDFs and images into clean Markdown text using a vision language model (VLM).

**Core Features:**
- PDF/PNG/JPEG to Markdown conversion
- Support for equations, tables, handwriting, complex layouts
- Multi-column layout handling with natural reading order
- Header/footer removal

## Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  gcp-frontend    │────▶│   gcp-backend    │────▶│    gcp-worker    │
│  React + Vite    │     │  FastAPI/Python  │     │  Python Worker   │
│  Firebase Auth   │     │  Cloud Run       │     │  Cloud Run       │
└──────────────────┘     └────────┬─────────┘     └────────┬─────────┘
                                  │                        │
                         ┌────────▼─────────┐       ┌──────▼───────┐
                         │  GCP Services    │       │  Parasail/   │
                         │  - Firestore     │       │  olmOCR API  │
                         │  - Cloud Storage │       └──────────────┘
                         │  - Pub/Sub       │
                         └──────────────────┘
```

## Tech Stack

### Core Library (`olmocr/`)
- **Language:** Python 3.11+
- **ML Framework:** PyTorch, Transformers, vLLM
- **Dependencies:** See `pyproject.toml`

### Frontend (`gcp-frontend/`)
- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite
- **Styling:** Tailwind CSS
- **State:** Zustand
- **Data Fetching:** TanStack Query
- **Auth:** Firebase
- **Testing:** Vitest + Testing Library

### Backend (`gcp-backend/`)
- **Framework:** FastAPI
- **GCP Services:** Cloud Storage, Firestore, Pub/Sub
- **Auth:** Firebase Admin SDK
- **Testing:** pytest + pytest-asyncio

### Worker (`gcp-worker/`)
- **Purpose:** Processes OCR jobs via Pub/Sub
- **Integration:** Parasail API (external olmOCR inference)

## Development Commands

### Core Library
```bash
# Install for development
pip install -e ".[dev]"

# Run core library tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=olmocr --cov-report=term-missing

# Linting
ruff check olmocr/
black olmocr/
mypy olmocr/
```

### Frontend
```bash
cd gcp-frontend

# Install dependencies
npm install

# Development server
npm run dev

# Build
npm run build

# Type check
npm run type-check

# Run tests
npm test -- --run

# Lint
npm run lint
```

### Backend
```bash
cd gcp-backend

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start dev server
uvicorn app.main:app --reload
```

### Run All Tests
```bash
./run_all_tests.sh
```

## Key Directories

| Directory | Description |
|-----------|-------------|
| `olmocr/` | Core OCR library (pipeline, prompts, training) |
| `olmocr/pipeline.py` | Main PDF processing pipeline |
| `olmocr/bench/` | Benchmark suite |
| `olmocr/train/` | Model training code (SFT, GRPO RL) |
| `gcp-frontend/src/` | React frontend source |
| `gcp-frontend/src/components/` | React components |
| `gcp-frontend/src/services/` | API and Firebase services |
| `gcp-backend/app/` | FastAPI backend |
| `gcp-backend/app/routers/` | API routes |
| `gcp-backend/app/services/` | Business logic |
| `gcp-worker/worker/` | Job processing worker |
| `gcp-deployment/` | Deployment scripts and configs |
| `tests/` | Core library tests |
| `scripts/` | Utility scripts |

## Important Files

- `pyproject.toml` - Python package configuration and dependencies
- `gcp-frontend/package.json` - Frontend dependencies
- `gcp-backend/requirements.txt` - Backend dependencies
- `docker-compose.yml` - Local development with Docker
- `run_all_tests.sh` - Run complete test suite
- `QUICKSTART.md` - GCP deployment guide

## Code Style

- **Python:** Black formatter, Ruff linter, line length 160
- **TypeScript:** ESLint, Prettier
- **Commits:** Descriptive messages focusing on "why"

## Environment Variables

### Backend (`.env`)
- `GCP_PROJECT_ID` - Google Cloud project
- `PARASAIL_API_KEY` - Parasail API key for OCR inference
- Firebase/Firestore credentials

### Frontend
- Firebase config (API key, auth domain, project ID, etc.)
- See `gcp-frontend/.env.example`

## Common Tasks

### Adding a new API endpoint
1. Create route in `gcp-backend/app/routers/`
2. Add business logic in `gcp-backend/app/services/`
3. Register router in `gcp-backend/app/main.py`
4. Add corresponding frontend service in `gcp-frontend/src/services/`

### Modifying OCR pipeline
1. Core logic is in `olmocr/pipeline.py`
2. Prompts are in `olmocr/prompts/`
3. Test with `pytest tests/test_pipeline.py`

## Notes

- The olmOCR model requires a GPU with 15GB+ VRAM for local inference
- For development without GPU, use the Parasail API endpoint
- Firestore has a 1MB document limit - large PDFs use in-memory storage
- Frontend uses Firebase Authentication for user management
