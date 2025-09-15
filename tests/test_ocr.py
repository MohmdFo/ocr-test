# tests/test_ocr.py
"""Tests for OCR functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import io

from apps.main import app
from apps.ocr.schemas import OCRResponse, DetectedText, OCRConfidenceLevel
from apps.ocr.service import DotsOCRService

client = TestClient(app)


def create_test_image() -> bytes:
    """Create a simple test image."""
    image = Image.new('RGB', (100, 100), color='white')
    # Add some text-like patterns
    for i in range(10, 90, 10):
        for j in range(10, 90, 20):
            image.putpixel((i, j), (0, 0, 0))
    
    img_bytes = io.BytesIO()
    image.save(img_bytes, format='PNG')
    return img_bytes.getvalue()


@pytest.fixture
def test_image_file():
    """Fixture that provides a test image file."""
    return create_test_image()


@pytest.fixture
def mock_ocr_response():
    """Fixture that provides a mock OCR response."""
    return {
        "success": True,
        "predictions": [
            {
                "text": "Sample OCR text",
                "confidence": 0.95,
                "bbox": {"x": 10, "y": 20, "width": 100, "height": 30}
            },
            {
                "text": "Another text block",
                "confidence": 0.87,
                "bbox": {"x": 15, "y": 60, "width": 120, "height": 25}
            }
        ]
    }


class TestOCREndpoints:
    """Test class for OCR endpoints."""
    
    def test_supported_formats_endpoint(self):
        """Test the supported formats endpoint."""
        response = client.get("/v1/ocr/supported-formats")
        assert response.status_code == 200
        
        data = response.json()
        assert "supported_formats" in data
        assert "max_file_size_mb" in data
        assert "supported_languages" in data
        
        # Check that common image formats are supported
        assert "image/jpeg" in data["supported_formats"]
        assert "image/png" in data["supported_formats"]
    
    def test_stats_endpoint(self):
        """Test the service stats endpoint."""
        response = client.get("/v1/ocr/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "service_status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "endpoints" in data
    
    @patch('apps.ocr.service.DotsOCRService.process_image')
    def test_upload_endpoint_success(self, mock_process, test_image_file, mock_ocr_response):
        """Test successful image upload and processing."""
        # Mock the OCR service response
        mock_result = OCRResponse(
            success=True,
            message="OCR processing completed successfully",
            filename="test.png",
            detected_text=[
                DetectedText(
                    text="Sample OCR text",
                    confidence=0.95,
                    confidence_level=OCRConfidenceLevel.HIGH
                )
            ],
            full_text="Sample OCR text",
            metadata={"language": "auto"},
            processing_time_ms=150.0
        )
        mock_process.return_value = mock_result
        
        # Prepare test file
        files = {"file": ("test.png", test_image_file, "image/png")}
        data = {
            "language": "en",
            "include_confidence": True,
            "include_bounding_boxes": False
        }
        
        response = client.post("/v1/ocr/upload", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["success"] is True
        assert result["filename"] == "test.png"
        assert "detected_text" in result
        assert "full_text" in result
        assert result["processing_time_ms"] == 150.0
        
        # Verify the mock was called
        mock_process.assert_called_once()
    
    def test_upload_endpoint_invalid_file_type(self):
        """Test upload with invalid file type."""
        # Create a text file instead of an image
        files = {"file": ("test.txt", b"This is not an image", "text/plain")}
        data = {"language": "auto"}
        
        response = client.post("/v1/ocr/upload", files=files, data=data)
        assert response.status_code == 415  # Unsupported Media Type
    
    def test_upload_endpoint_no_file(self):
        """Test upload endpoint without a file."""
        data = {"language": "auto"}
        
        response = client.post("/v1/ocr/upload", data=data)
        assert response.status_code == 422  # Validation error
    
    @patch('apps.ocr.service.DotsOCRService.process_image')
    def test_process_endpoint_with_json_options(self, mock_process, test_image_file):
        """Test the process endpoint with JSON options."""
        mock_result = OCRResponse(
            success=True,
            message="OCR processing completed successfully",
            filename="test.png",
            detected_text=[],
            full_text="Sample text",
            metadata={}
        )
        mock_process.return_value = mock_result
        
        files = {"file": ("test.png", test_image_file, "image/png")}
        options = {
            "language": "en",
            "include_confidence": True,
            "include_bounding_boxes": True
        }
        data = {"options": json.dumps(options)}
        
        response = client.post("/v1/ocr/process", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
    
    def test_process_endpoint_invalid_json(self, test_image_file):
        """Test the process endpoint with invalid JSON options."""
        files = {"file": ("test.png", test_image_file, "image/png")}
        data = {"options": "invalid json"}
        
        response = client.post("/v1/ocr/process", files=files, data=data)
        assert response.status_code == 400


class TestOCRService:
    """Test class for OCR service functionality."""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test OCR service health check when service is healthy."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            service = DotsOCRService()
            result = await service.health_check()
            
            assert result["status"] == "healthy"
            assert "dots.ocr service is running" in result["message"]
    
    @pytest.mark.asyncio
    async def test_health_check_service_down(self):
        """Test OCR service health check when service is down."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response
            
            service = DotsOCRService()
            result = await service.health_check()
            
            assert result["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_health_check_connection_error(self):
        """Test OCR service health check with connection error."""
        with patch('httpx.AsyncClient.get', side_effect=Exception("Connection failed")):
            service = DotsOCRService()
            result = await service.health_check()
            
            assert result["status"] == "error"
            assert "Connection failed" in result["message"]
    
    def test_confidence_level_determination(self):
        """Test confidence level categorization."""
        service = DotsOCRService()
        
        assert service._determine_confidence_level(0.9) == OCRConfidenceLevel.HIGH
        assert service._determine_confidence_level(0.7) == OCRConfidenceLevel.MEDIUM
        assert service._determine_confidence_level(0.3) == OCRConfidenceLevel.LOW
        assert service._determine_confidence_level(0.8) == OCRConfidenceLevel.HIGH
        assert service._determine_confidence_level(0.5) == OCRConfidenceLevel.MEDIUM
    
    def test_parse_dots_ocr_response(self, mock_ocr_response):
        """Test parsing of dots.ocr response."""
        service = DotsOCRService()
        
        result = service._parse_dots_ocr_response(mock_ocr_response, include_bounding_boxes=True)
        
        assert len(result) == 2
        assert result[0].text == "Sample OCR text"
        assert result[0].confidence == 0.95
        assert result[0].confidence_level == OCRConfidenceLevel.HIGH
        assert result[0].bounding_box is not None
        
        assert result[1].text == "Another text block"
        assert result[1].confidence == 0.87
        assert result[1].confidence_level == OCRConfidenceLevel.HIGH
    
    def test_parse_dots_ocr_response_without_bbox(self, mock_ocr_response):
        """Test parsing of dots.ocr response without bounding boxes."""
        service = DotsOCRService()
        
        result = service._parse_dots_ocr_response(mock_ocr_response, include_bounding_boxes=False)
        
        assert len(result) == 2
        assert result[0].bounding_box is None
        assert result[1].bounding_box is None


class TestOCRUtils:
    """Test class for OCR utility functions."""
    
    def test_validate_image_file_valid(self, test_image_file):
        """Test validation of a valid image file."""
        from apps.ocr.utils import validate_image_file
        from fastapi import UploadFile
        
        # Create a mock UploadFile
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "image/png"
        mock_file.filename = "test.png"
        mock_file.size = len(test_image_file)
        
        # Should not raise an exception
        validate_image_file(mock_file)
    
    def test_validate_image_file_invalid_type(self):
        """Test validation with invalid file type."""
        from apps.ocr.utils import validate_image_file
        from fastapi import UploadFile, HTTPException
        
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "text/plain"
        mock_file.filename = "test.txt"
        
        with pytest.raises(HTTPException) as exc_info:
            validate_image_file(mock_file)
        
        assert exc_info.value.status_code == 415
    
    def test_validate_image_file_too_large(self):
        """Test validation with file too large."""
        from apps.ocr.utils import validate_image_file, MAX_FILE_SIZE
        from fastapi import UploadFile, HTTPException
        
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "image/png"
        mock_file.filename = "test.png"
        mock_file.size = MAX_FILE_SIZE + 1
        
        with pytest.raises(HTTPException) as exc_info:
            validate_image_file(mock_file)
        
        assert exc_info.value.status_code == 413
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        from apps.ocr.utils import sanitize_filename
        
        assert sanitize_filename("test.png") == "test.png"
        assert sanitize_filename("test file.png") == "test file.png"
        assert sanitize_filename("test/file\\with|bad*chars.png") == "testfilewithbadchars.png"
        assert sanitize_filename("") == "unnamed_file"
        
        # Test long filename truncation
        long_name = "a" * 150 + ".png"
        result = sanitize_filename(long_name)
        assert len(result) <= 100


@pytest.mark.integration
class TestOCRIntegration:
    """Integration tests for OCR functionality."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_ocr_processing(self, test_image_file):
        """Test complete OCR processing flow (requires actual service)."""
        # This test should only run when integration testing is enabled
        # and actual dots.ocr service is available
        pass  # Implement when integration testing is set up


if __name__ == "__main__":
    pytest.main([__file__])
