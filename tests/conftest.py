# tests/conftest.py
"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import asyncio
from typing import Generator

from fastapi.testclient import TestClient
from apps.main import app


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> TestClient:
    """Fixture that provides a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def temp_upload_dir() -> Generator[Path, None, None]:
    """Fixture that provides a temporary upload directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_dots_ocr_service():
    """Fixture that provides a mock dots.ocr service."""
    mock_service = MagicMock()
    mock_service.health_check.return_value = {
        "status": "healthy",
        "message": "Mock service running"
    }
    return mock_service


# Configure pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


# Skip integration tests by default
def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle markers."""
    if config.getoption("--runintegration"):
        return
    
    skip_integration = pytest.mark.skip(reason="need --runintegration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--runintegration",
        action="store_true",
        default=False,
        help="run integration tests"
    )
