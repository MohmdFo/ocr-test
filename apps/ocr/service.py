# apps/ocr/service.py
"""Service layer for OCR operations using dots.ocr integration."""

import asyncio
import json
import os
import time
from typing import Dict, Any, List, Optional
import httpx
from pathlib import Path

from apps.ocr.schemas import (
    OCRResponse, 
    DetectedText, 
    BoundingBox, 
    OCRConfidenceLevel,
    ErrorResponse
)
from apps.ocr.utils import ensure_upload_directory, save_uploaded_file, cleanup_file
from conf.enhanced_logging import get_logger

logger = get_logger(__name__)


class DotsOCRService:
    """Service class for handling OCR operations with dots.ocr backend."""
    
    def __init__(self, dots_ocr_url: str = "http://dots-ocr:8000"):
        """
        Initialize the OCR service.
        
        Args:
            dots_ocr_url: URL of the dots.ocr service
        """
        self.dots_ocr_url = dots_ocr_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
        
    async def health_check(self) -> Dict[str, str]:
        """
        Check the health of the dots.ocr service.
        
        Returns:
            Dict containing service status information
        """
        try:
            response = await self.client.get(f"{self.dots_ocr_url}/health")
            if response.status_code == 200:
                return {"status": "healthy", "message": "dots.ocr service is running"}
            else:
                return {"status": "unhealthy", "message": f"Service returned status {response.status_code}"}
        except httpx.RequestError as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unreachable", "message": f"Cannot reach dots.ocr service: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error during health check: {e}")
            return {"status": "error", "message": f"Health check error: {str(e)}"}
    
    def _determine_confidence_level(self, confidence: float) -> OCRConfidenceLevel:
        """
        Determine confidence level category based on numeric confidence.
        
        Args:
            confidence: Numeric confidence score (0.0 to 1.0)
            
        Returns:
            OCRConfidenceLevel enum value
        """
        if confidence >= 0.8:
            return OCRConfidenceLevel.HIGH
        elif confidence >= 0.5:
            return OCRConfidenceLevel.MEDIUM
        else:
            return OCRConfidenceLevel.LOW
    
    def _parse_dots_ocr_response(self, response_data: Dict[str, Any], include_bounding_boxes: bool = False) -> List[DetectedText]:
        """
        Parse the response from dots.ocr into our schema format.
        
        Args:
            response_data: Raw response from dots.ocr
            include_bounding_boxes: Whether to include bounding box data
            
        Returns:
            List of DetectedText objects
        """
        detected_texts = []
        
        # Handle different possible response formats from dots.ocr
        # This is a simplified parser - adapt based on actual dots.ocr response format
        if "predictions" in response_data:
            predictions = response_data["predictions"]
        elif "results" in response_data:
            predictions = response_data["results"]
        elif "text_blocks" in response_data:
            predictions = response_data["text_blocks"]
        else:
            # Fallback: assume the response itself contains the text data
            predictions = [response_data] if isinstance(response_data, dict) else response_data
        
        for prediction in predictions:
            try:
                # Extract text
                text = prediction.get("text", prediction.get("content", ""))
                if not text:
                    continue
                
                # Extract confidence (default to 0.9 if not provided)
                confidence = float(prediction.get("confidence", prediction.get("score", 0.9)))
                confidence = max(0.0, min(1.0, confidence))  # Clamp to [0,1]
                
                # Create bounding box if data is available and requested
                bbox = None
                if include_bounding_boxes:
                    bbox_data = prediction.get("bbox", prediction.get("bounding_box"))
                    if bbox_data:
                        try:
                            bbox = BoundingBox(
                                x=float(bbox_data.get("x", 0)),
                                y=float(bbox_data.get("y", 0)),
                                width=float(bbox_data.get("width", bbox_data.get("w", 0))),
                                height=float(bbox_data.get("height", bbox_data.get("h", 0)))
                            )
                        except (ValueError, KeyError) as e:
                            logger.warning(f"Failed to parse bounding box: {e}")
                
                detected_text = DetectedText(
                    text=text,
                    confidence=confidence,
                    confidence_level=self._determine_confidence_level(confidence),
                    bounding_box=bbox
                )
                detected_texts.append(detected_text)
                
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse prediction: {e}")
                continue
        
        return detected_texts
    
    async def process_image(
        self, 
        image_path: Path,
        language: str = "auto",
        include_confidence: bool = True,
        include_bounding_boxes: bool = False
    ) -> OCRResponse:
        """
        Process an image file using dots.ocr service.
        
        Args:
            image_path: Path to the image file
            language: Language code for OCR processing
            include_confidence: Whether to include confidence scores
            include_bounding_boxes: Whether to include bounding box coordinates
            
        Returns:
            OCRResponse with processing results
        """
        start_time = time.time()
        filename = image_path.name
        
        try:
            # Prepare the request to dots.ocr
            files = {"file": (filename, open(image_path, "rb"), "image/*")}
            data = {
                "language": language,
                "include_confidence": include_confidence,
                "include_bounding_boxes": include_bounding_boxes
            }
            
            logger.info(f"Sending OCR request for {filename} to dots.ocr service")
            
            # Make request to dots.ocr service
            response = await self.client.post(
                f"{self.dots_ocr_url}/ocr",
                files=files,
                data=data
            )
            
            # Close the file
            files["file"][1].close()
            
            processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            if response.status_code != 200:
                error_msg = f"dots.ocr service returned status {response.status_code}"
                logger.error(f"{error_msg}: {response.text}")
                return OCRResponse(
                    success=False,
                    message=error_msg,
                    filename=filename,
                    detected_text=[],
                    full_text="",
                    metadata={"error": response.text},
                    processing_time_ms=processing_time
                )
            
            # Parse response
            response_data = response.json()
            detected_texts = self._parse_dots_ocr_response(response_data, include_bounding_boxes)
            
            # Combine all text
            full_text = " ".join([dt.text for dt in detected_texts])
            
            logger.info(f"OCR processing completed for {filename} in {processing_time:.2f}ms")
            
            return OCRResponse(
                success=True,
                message="OCR processing completed successfully",
                filename=filename,
                detected_text=detected_texts,
                full_text=full_text,
                metadata={
                    "language": language,
                    "text_blocks_count": len(detected_texts),
                    "dots_ocr_response": response_data
                },
                processing_time_ms=processing_time
            )
            
        except httpx.RequestError as e:
            error_msg = f"Failed to connect to dots.ocr service: {str(e)}"
            logger.error(error_msg)
            processing_time = (time.time() - start_time) * 1000
            
            return OCRResponse(
                success=False,
                message=error_msg,
                filename=filename,
                detected_text=[],
                full_text="",
                metadata={"error": str(e)},
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            error_msg = f"Unexpected error during OCR processing: {str(e)}"
            logger.error(error_msg)
            processing_time = (time.time() - start_time) * 1000
            
            return OCRResponse(
                success=False,
                message=error_msg,
                filename=filename,
                detected_text=[],
                full_text="",
                metadata={"error": str(e)},
                processing_time_ms=processing_time
            )


# Singleton instance for dependency injection
default_url = os.getenv("DOTS_OCR_URL", "http://localhost:8501")
ocr_service = DotsOCRService(dots_ocr_url=default_url)


async def get_ocr_service() -> DotsOCRService:
    """Dependency injection function for OCR service."""
    return ocr_service
