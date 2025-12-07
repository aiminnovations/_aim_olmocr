# Testing Guide

## Overview

This document explains how to run tests for all components of the olmOCR project.

## Quick Start

### Run All Tests

```bash
./run_all_tests.sh
```

This will run tests for:
- Core library (`olmocr/`)
- Backend API (`gcp-backend/`)
- Frontend (`gcp-frontend/`)
- Simple OCR App (`simple-ocr-app/`)

## Individual Component Testing

### Core Library Tests

```bash
pytest tests/ -v --cov=olmocr --cov-report=html
```

**Coverage Report:** Open `htmlcov/index.html` in your browser

**Test Files:**
- `tests/test_pipeline.py` - OCR pipeline tests
- `tests/test_dataloader.py` - Data loading tests
- `tests/test_filter.py` - Content filtering tests

### Backend API Tests

```bash
cd gcp-backend
pytest tests/ -v --cov=app --cov-report=html
```

**Coverage Report:** `gcp-backend/htmlcov/index.html`

**Test Files:**
- `tests/test_health.py` - Health check endpoint
- `tests/routers/test_upload.py` - Upload endpoints (requires auth mocking)

**Note:** Backend tests require Firebase authentication mocking for full coverage.

### Frontend Tests

```bash
cd gcp-frontend
npm test                    # Run tests in watch mode
npm run test:coverage       # Run with coverage report
npm run test:ui             # Open Vitest UI
```

**Coverage Report:** `gcp-frontend/coverage/index.html`

**Test Files:**
- `src/components/__tests__/example.test.tsx` - Example component test

**Adding New Tests:**
1. Create `ComponentName.test.tsx` in `src/components/__tests__/`
2. Import test utilities: `import { render, screen } from '@testing-library/react'`
3. Write tests using Vitest syntax

### Simple OCR App Tests

```bash
cd simple-ocr-app
pytest tests/ -v --cov --cov-report=html
```

**Coverage Report:** `simple-ocr-app/htmlcov/index.html`

**Test Files:**
- `tests/test_api.py` - API endpoint tests

## Writing Tests

### Backend (Python/FastAPI)

```python
def test_my_endpoint(client):
    """Test description."""
    response = client.get("/my-endpoint")
    assert response.status_code == 200
    assert response.json()["key"] == "value"
```

### Frontend (React/TypeScript)

```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MyComponent } from '../MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });
});
```

## Test Configuration

### Backend (pytest)

**File:** `gcp-backend/pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v --cov=app --cov-report=html
asyncio_mode = auto
```

### Frontend (Vitest)

**File:** `gcp-frontend/vitest.config.ts`

```typescript
export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
});
```

## Continuous Integration

Tests run automatically on:
- Pull requests to `main`
- Pushes to `main` branch
- Manual workflow triggers

**GitHub Actions Workflow:** `.github/workflows/main.yml`

## Troubleshooting

### Backend Tests Fail

**Error:** `ModuleNotFoundError: No module named 'app'`

**Solution:**
```bash
cd gcp-backend
pip install -e .
pytest tests/
```

### Frontend Tests Fail

**Error:** `Cannot find module '@testing-library/react'`

**Solution:**
```bash
cd gcp-frontend
npm install
npm test
```

### Import Errors

Ensure you're running tests from the correct directory:
- Backend: Run from `gcp-backend/`
- Frontend: Run from `gcp-frontend/`
- Simple OCR App: Run from `simple-ocr-app/`
- Core library: Run from project root

## Test Coverage Goals

- **Backend:** > 80% coverage
- **Frontend:** > 70% coverage
- **Core Library:** > 90% coverage (already achieved)

## TODO: Tests to Add

### Backend
- [ ] Authenticated upload tests with Firebase token mocking
- [ ] Job status endpoint tests
- [ ] Results download tests
- [ ] File validation tests (size, type)
- [ ] Firestore integration tests
- [ ] Pub/Sub message publishing tests

### Frontend
- [ ] LoginPage component tests
- [ ] Upload component tests
- [ ] Job list display tests
- [ ] Error boundary tests
- [ ] Authentication flow tests
- [ ] API integration tests (mocked)

### Simple OCR App
- [ ] Upload endpoint with file tests
- [ ] Batch processing tests
- [ ] Job status polling tests
- [ ] Parasail API mocking tests

## Best Practices

1. **Write tests first** - TDD approach when adding new features
2. **Mock external services** - Don't make real API calls in tests
3. **Test user workflows** - Not just individual functions
4. **Keep tests fast** - Use mocks, avoid heavy operations
5. **Clear test names** - Describe what's being tested
6. **One assertion per test** - Or related assertions only
7. **Use fixtures** - DRY principle for test setup

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
