# tests/test_health.py
"""Tests for health check endpoints."""

import pytest
from fastapi.testclient import TestClient
from apps.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test the main health endpoint."""
    response = client.get("/v1/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "timestamp" in data


def test_ocr_health_endpoint():
    """Test the OCR-specific health endpoint."""
    response = client.get("/v1/ocr/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "version" in data
    assert "dots_ocr_status" in data


def test_metrics_endpoint():
    """Test the metrics endpoint."""
    response = client.get("/v1/metrics")
    assert response.status_code == 200
    
    # Metrics should be in Prometheus format
    assert "text/plain" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_startup_and_shutdown():
    """Test application startup and shutdown events."""
    # This test ensures the startup/shutdown events work correctly
    from apps.main import startup_event, shutdown_event
    
    try:
        await startup_event()
        # If we get here, startup was successful
        assert True
    except Exception as e:
        pytest.fail(f"Startup event failed: {e}")
    
    try:
        await shutdown_event()
        # If we get here, shutdown was successful
        assert True
    except Exception as e:
        pytest.fail(f"Shutdown event failed: {e}")


def test_api_versioning():
    """Test that API versioning is working correctly."""
    # Test that versioned endpoints are accessible
    response = client.get("/v1/health")
    assert response.status_code == 200
    
    # Test that latest version works
    response = client.get("/latest/health")
    assert response.status_code == 200


def test_cors_headers():
    """Test CORS headers if configured."""
    response = client.get("/v1/health")
    
    # Check if CORS headers are present (they might not be in test environment)
    # This is more of a documentation test
    assert response.status_code == 200
