import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """Test client for API testing."""
    return TestClient(app)

@pytest.fixture
def mock_gcs_client():
    """Mock Google Cloud Storage client."""
    # TODO: Implement mock for GCS operations
    pass

@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client."""
    # TODO: Implement mock for Firestore operations
    pass

@pytest.fixture
def mock_pubsub_client():
    """Mock Pub/Sub client."""
    # TODO: Implement mock for Pub/Sub operations
    pass
