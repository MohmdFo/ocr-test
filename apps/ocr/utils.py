# apps/ocr/utils.py
"""Utility functions for OCR file handling and processing."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Union, BinaryIO
import mimetypes
from fastapi import UploadFile, HTTPException

from conf.enhanced_logging import get_logger

logger = get_logger(__name__)

# Supported image formats
SUPPORTED_IMAGE_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/gif", 
    "image/bmp", "image/tiff", "image/webp"
}

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


def ensure_upload_directory(upload_dir: Union[str, Path] = "/tmp/uploads") -> Path:
    """
    Ensure the upload directory exists.
    
    Args:
        upload_dir: Path to the upload directory
        
    Returns:
        Path object for the upload directory
    """
    upload_path = Path(upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Upload directory ensured: {upload_path}")
    return upload_path


def validate_image_file(file: UploadFile) -> None:
    """
    Validate uploaded file is a supported image format.
    
    Args:
        file: FastAPI UploadFile object
        
    Raises:
        HTTPException: If file is not valid
    """
    # Check file size
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Check content type
    if file.content_type not in SUPPORTED_IMAGE_TYPES:
        # Try to guess from filename
        if file.filename:
            guessed_type, _ = mimetypes.guess_type(file.filename)
            if guessed_type not in SUPPORTED_IMAGE_TYPES:
                raise HTTPException(
                    status_code=415,
                    detail=f"Unsupported file type. Supported types: {', '.join(SUPPORTED_IMAGE_TYPES)}"
                )
        else:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type. Supported types: {', '.join(SUPPORTED_IMAGE_TYPES)}"
            )
    
    # Check filename
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided"
        )
    
    logger.debug(f"File validation passed for: {file.filename}")


async def save_uploaded_file(
    file: UploadFile, 
    upload_dir: Union[str, Path] = "/tmp/uploads"
) -> Path:
    """
    Save uploaded file to disk.
    
    Args:
        file: FastAPI UploadFile object
        upload_dir: Directory to save file in
        
    Returns:
        Path to the saved file
        
    Raises:
        HTTPException: If file operations fail
    """
    try:
        # Validate the file first
        validate_image_file(file)
        
        # Ensure upload directory exists
        upload_path = ensure_upload_directory(upload_dir)
        
        # Create a temporary file with original extension
        file_extension = Path(file.filename).suffix.lower()
        if not file_extension:
            file_extension = ".jpg"  # Default extension
            
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=file_extension,
            dir=upload_path,
            prefix="ocr_upload_"
        )
        
        # Copy file contents
        shutil.copyfileobj(file.file, temp_file)
        temp_file.close()
        
        saved_path = Path(temp_file.name)
        logger.info(f"File saved: {file.filename} -> {saved_path}")
        
        return saved_path
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded file: {str(e)}"
        )


def cleanup_file(file_path: Union[str, Path]) -> None:
    """
    Clean up a temporary file.
    
    Args:
        file_path: Path to the file to delete
    """
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.debug(f"Cleaned up file: {path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup file {file_path}: {e}")


def get_file_info(file_path: Union[str, Path]) -> dict:
    """
    Get information about a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file information
    """
    path = Path(file_path)
    try:
        stat = path.stat()
        return {
            "filename": path.name,
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "extension": path.suffix.lower(),
            "exists": True
        }
    except Exception as e:
        logger.error(f"Failed to get file info for {file_path}: {e}")
        return {
            "filename": path.name if path else "unknown",
            "size": 0,
            "size_mb": 0.0,
            "extension": "",
            "exists": False,
            "error": str(e)
        }


def create_temp_directory() -> Path:
    """
    Create a temporary directory for OCR processing.
    
    Returns:
        Path to the temporary directory
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="ocr_temp_"))
    logger.debug(f"Created temporary directory: {temp_dir}")
    return temp_dir


def cleanup_directory(dir_path: Union[str, Path]) -> None:
    """
    Remove a directory and all its contents.
    
    Args:
        dir_path: Path to the directory to remove
    """
    try:
        path = Path(dir_path)
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            logger.debug(f"Cleaned up directory: {path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup directory {dir_path}: {e}")


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe storage.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace dangerous characters
    safe_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    sanitized = "".join(c for c in filename if c in safe_chars)
    
    # Ensure it's not empty and not too long
    if not sanitized:
        sanitized = "unnamed_file"
    
    # Limit length
    if len(sanitized) > 100:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:95] + ext
    
    return sanitized
