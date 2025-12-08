import pytest
from fastapi.testclient import TestClient

# Import app from parent directory
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app

@pytest.fixture
def client():
    """Test client for API testing."""
    return TestClient(app)

@pytest.fixture
def mock_parasail_api(monkeypatch):
    """Mock Parasail API calls to avoid actual API requests."""
    async def mock_post(*args, **kwargs):
        class MockResponse:
            status = 200
            async def json(self):
                return {"choices": [{"message": {"content": "# Test\nMocked OCR output"}}]}
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
        return MockResponse()
    
    # Mock aiohttp ClientSession if needed
    # monkeypatch.setattr("aiohttp.ClientSession.post", mock_post)
    return mock_post
