# apps/ocr/routers.py
"""FastAPI routers for OCR endpoints."""

from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse

from apps.ocr.schemas import (
    OCRResponse, 
    ErrorResponse, 
    HealthResponse,
    OCRUploadRequest
)
from apps.ocr.service import DotsOCRService, get_ocr_service
from apps.ocr.utils import save_uploaded_file, cleanup_file, get_file_info
from conf.enhanced_logging import get_logger

logger = get_logger(__name__)

# Create the OCR router
router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    ocr_service: DotsOCRService = Depends(get_ocr_service)
) -> HealthResponse:
    """
    Check the health of OCR service and dots.ocr backend.
    
    Returns:
        Health status information
    """
    try:
        # Check dots.ocr service health
        dots_health = await ocr_service.health_check()
        
        return HealthResponse(
            status="healthy" if dots_health["status"] == "healthy" else "degraded",
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            dots_ocr_status=dots_health["status"]
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            dots_ocr_status="error"
        )


@router.post("/upload", response_model=OCRResponse)
async def upload_and_process_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Image file to process"),
    language: str = Form("auto", description="Language code for OCR (e.g., 'en', 'auto')"),
    include_confidence: bool = Form(True, description="Include confidence scores in response"),
    include_bounding_boxes: bool = Form(False, description="Include bounding box coordinates"),
    ocr_service: DotsOCRService = Depends(get_ocr_service)
) -> OCRResponse:
    """
    Upload an image file and process it with OCR.
    
    Args:
        background_tasks: FastAPI background tasks for cleanup
        file: Image file to process
        language: Language code for OCR processing
        include_confidence: Whether to include confidence scores
        include_bounding_boxes: Whether to include bounding box coordinates
        ocr_service: OCR service dependency
        
    Returns:
        OCR processing results
        
    Raises:
        HTTPException: If upload or processing fails
    """
    saved_file_path = None
    
    try:
        logger.info(f"Processing OCR upload: {file.filename}")
        
        # Save uploaded file
        saved_file_path = await save_uploaded_file(file)
        
        # Get file info for logging
        file_info = get_file_info(saved_file_path)
        logger.info(f"Saved file info: {file_info}")
        
        # Process image with OCR service
        result = await ocr_service.process_image(
            image_path=saved_file_path,
            language=language,
            include_confidence=include_confidence,
            include_bounding_boxes=include_bounding_boxes
        )
        
        # Schedule file cleanup in background
        background_tasks.add_task(cleanup_file, saved_file_path)
        
        logger.info(f"OCR processing completed for {file.filename}: {result.success}")
        return result
        
    except HTTPException:
        # Clean up file if it was saved
        if saved_file_path:
            background_tasks.add_task(cleanup_file, saved_file_path)
        raise
        
    except Exception as e:
        # Clean up file if it was saved
        if saved_file_path:
            background_tasks.add_task(cleanup_file, saved_file_path)
        
        error_msg = f"Unexpected error during OCR processing: {str(e)}"
        logger.error(error_msg)
        
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )


@router.post("/process", response_model=OCRResponse)
async def process_image_with_options(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Image file to process"),
    options: str = Form(
        '{"language": "auto", "include_confidence": true, "include_bounding_boxes": false}',
        description="JSON string with processing options"
    ),
    ocr_service: DotsOCRService = Depends(get_ocr_service)
) -> OCRResponse:
    """
    Alternative endpoint that accepts processing options as JSON.
    
    Args:
        background_tasks: FastAPI background tasks for cleanup
        file: Image file to process
        options: JSON string with processing options
        ocr_service: OCR service dependency
        
    Returns:
        OCR processing results
    """
    import json
    
    try:
        # Parse options
        parsed_options = json.loads(options)
        
        return await upload_and_process_image(
            background_tasks=background_tasks,
            file=file,
            language=parsed_options.get("language", "auto"),
            include_confidence=parsed_options.get("include_confidence", True),
            include_bounding_boxes=parsed_options.get("include_bounding_boxes", False),
            ocr_service=ocr_service
        )
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON in options parameter: {str(e)}"
        )


@router.get("/supported-formats")
async def get_supported_formats() -> dict:
    """
    Get list of supported image formats.
    
    Returns:
        Dictionary with supported formats and limits
    """
    from apps.ocr.utils import SUPPORTED_IMAGE_TYPES, MAX_FILE_SIZE
    
    return {
        "supported_formats": list(SUPPORTED_IMAGE_TYPES),
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
        "max_file_size_bytes": MAX_FILE_SIZE,
        "supported_languages": [
            "auto", "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko"
        ]  # Common language codes - adjust based on dots.ocr capabilities
    }


@router.get("/stats")
async def get_service_stats(
    ocr_service: DotsOCRService = Depends(get_ocr_service)
) -> dict:
    """
    Get service statistics and status.
    
    Returns:
        Service statistics
    """
    try:
        # Check dots.ocr health
        dots_health = await ocr_service.health_check()
        
        return {
            "service_status": "operational",
            "dots_ocr_status": dots_health["status"],
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "endpoints": {
                "health": "/api/v1/ocr/health",
                "upload": "/api/v1/ocr/upload",
                "process": "/api/v1/ocr/process",
                "supported_formats": "/api/v1/ocr/supported-formats",
                "stats": "/api/v1/ocr/stats"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get service stats: {e}")
        return {
            "service_status": "error",
            "dots_ocr_status": "unknown",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "error": str(e)
        }


# Note: Exception handlers should be registered on the main FastAPI app, not the router
# These would typically be added in apps/main.py:
#
# @app.exception_handler(HTTPException)
# async def ocr_http_exception_handler(request, exc: HTTPException):
#     """Handle HTTP exceptions in OCR endpoints."""
#     logger.error(f"HTTP error in OCR endpoint: {exc.status_code} - {exc.detail}")
#     
#     return JSONResponse(
#         status_code=exc.status_code,
#         content=ErrorResponse(
#             error="HTTPError",
#             message=exc.detail,
#             details={"status_code": exc.status_code}
#         ).dict()
#     )
