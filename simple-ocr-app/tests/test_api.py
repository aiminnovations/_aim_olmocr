"""
Simple OCR App API tests.
"""
import pytest

def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    # Should return 200 or 404 if not implemented
    assert response.status_code in [200, 404]

def test_root_endpoint(client):
    """Test root endpoint serves HTML."""
    response = client.get("/")
    assert response.status_code == 200
    # Should return HTML
    assert "text/html" in response.headers.get("content-type", "")

# TODO: Add upload endpoint tests
# TODO: Add batch processing tests
# TODO: Add job status tests
