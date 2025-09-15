# apps/main.py

import logging
import os
from fastapi import FastAPI
from fastapi_pagination import add_pagination
from fastapi_versioning import VersionedFastAPI

from apps.core.routers.health import router as health_router
from apps.metrics import metrics_router, setup_metrics
from apps.metrics.middleware import PrometheusMetricsMiddleware, MetricsContextMiddleware
from apps.ocr.routers import router as ocr_router
from conf.enhanced_logging import configure_enhanced_logging, get_logger

# Initialize enhanced logging
log_level = os.getenv("LOG_LEVEL", "INFO")
enable_file_logging = os.getenv("ENABLE_FILE_LOGGING", "true").lower() in ("true", "1", "yes")
configure_enhanced_logging(log_level=log_level, enable_file_logging=enable_file_logging)

# Get logger instance
logger = get_logger(__name__)

app = FastAPI(
    title="AIP OCR Service",
    description="FastAPI application for OCR processing using dots.ocr integration",
    version="v1.0.0",
)

# Add metrics middleware (must be added before other middleware)
app.add_middleware(PrometheusMetricsMiddleware, app_name="aip-ocr-service")
app.add_middleware(MetricsContextMiddleware)

# Include routers with appropriate prefixes and tags
app.include_router(health_router, tags=["Health"])
app.include_router(metrics_router, tags=["Monitoring"])
app.include_router(ocr_router, tags=["OCR"])

# Add any middleware, exception handlers, etc. here
add_pagination(app)

# API Versioning: endpoints will be available under /v1, /v2, etc.
app = VersionedFastAPI(app,
                       version_format="{major}",
                       prefix_format="/v{major}",
                       enable_latest=True,
                       default_version=(1, 0))

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    try:
        # Setup Prometheus metrics
        setup_metrics()
        logger.info("Prometheus metrics system initialized successfully")
        
        # Ensure upload directory exists
        from apps.ocr.utils import ensure_upload_directory
        ensure_upload_directory()
        logger.info("OCR upload directory initialized")
        
    except Exception as exc:
        logger.error(f"Failed to initialize application: {exc}")
        # Don't fail startup for non-critical issues

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Application shutting down")
