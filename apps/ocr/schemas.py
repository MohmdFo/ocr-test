# apps/ocr/schemas.py
"""Pydantic schemas for OCR API requests and responses."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class OCRConfidenceLevel(str, Enum):
    """Confidence levels for OCR results."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BoundingBox(BaseModel):
    """Bounding box coordinates for detected text."""
    x: float = Field(..., description="X coordinate of top-left corner")
    y: float = Field(..., description="Y coordinate of top-left corner")
    width: float = Field(..., description="Width of the bounding box")
    height: float = Field(..., description="Height of the bounding box")


class DetectedText(BaseModel):
    """Individual text detection result."""
    text: str = Field(..., description="Extracted text content")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    confidence_level: OCRConfidenceLevel = Field(..., description="Confidence level category")
    bounding_box: Optional[BoundingBox] = Field(None, description="Bounding box coordinates")


class OCRUploadRequest(BaseModel):
    """Request schema for OCR upload (used in form data description)."""
    language: Optional[str] = Field("auto", description="Language code for OCR (e.g., 'en', 'auto')")
    include_confidence: bool = Field(True, description="Include confidence scores in response")
    include_bounding_boxes: bool = Field(False, description="Include bounding box coordinates")


class OCRResponse(BaseModel):
    """Response schema for OCR processing results."""
    success: bool = Field(..., description="Whether OCR processing was successful")
    message: str = Field(..., description="Status message")
    filename: str = Field(..., description="Original filename of processed image")
    detected_text: List[DetectedText] = Field(default_factory=list, description="List of detected text blocks")
    full_text: str = Field(..., description="Complete extracted text concatenated")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about processing")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")


class ErrorResponse(BaseModel):
    """Error response schema."""
    success: bool = Field(False, description="Always false for error responses")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Detailed error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(..., description="Application version")
    dots_ocr_status: str = Field(..., description="Status of dots.ocr service")
