# AIP OCR Servi## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for local development)

### Setup dots.ocr Dependency

The application requires the [dots.ocr](https://github.com/rednote-hilab/dots.ocr) service. Since the Docker image is not available on Docker Hub, you need to build it from source:

```bash
# Clone and setup dots.ocr
./setup-dots-ocr.sh

# This will clone the repository and prepare it for Docker building
```

**Note:** If you encounter issues building dots.ocr, you can use the development setup with a mock service:

```bash
# For development with mock OCR service
docker compose -f docker-compose.dev.yml up -d
```**FastAPI application** integrated with [dots.ocr](https://github.com/rednote-hilab/dots.ocr) for high-performance optical character recognition (OCR) processing.

## Features

- 🚀 **FastAPI** backend with async support
- 🔍 **OCR Integration** with dots.ocr service
- 📁 **File Upload** support for multiple image formats
- 🐳 **Docker Compose** setup for easy deployment
- 📊 **Prometheus Metrics** for monitoring
- 🧪 **Comprehensive Testing** with pytest
- 📝 **API Documentation** with Swagger/OpenAPI
- 🔧 **Configurable Processing** options

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.13+ (for local development)
- Poetry (for dependency management)

### Run with Docker Compose

1. **Clone and start the services:**

```bash
git clone <your-repo>
cd aip-ocr
docker-compose up -d
```

2. **Check service health:**

```bash
curl http://localhost:8500/v1/health
curl http://localhost:8500/v1/ocr/health
```

3. **Access API documentation:**

- Swagger UI: http://localhost:8500/docs
- ReDoc: http://localhost:8500/redoc

### Development Setup

1. **Install dependencies:**

```bash
poetry install
```

2. **Run in development mode:**

```bash
# Start with mock dots.ocr service
docker-compose -f docker-compose.dev.yml up -d

# Or run locally
poetry run uvicorn apps.main:app --reload --host 0.0.0.0 --port 8500
```

## Usage Examples

### Upload and Process Image

**Using curl:**

```bash
# Basic OCR processing
curl -X POST "http://localhost:8500/v1/ocr/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-image.png" \
  -F "language=en" \
  -F "include_confidence=true"

# With bounding boxes
curl -X POST "http://localhost:8500/v1/ocr/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-image.png" \
  -F "language=auto" \
  -F "include_confidence=true" \
  -F "include_bounding_boxes=true"
```

**Using Python requests:**

```python
import requests

# Upload and process an image
with open('your-image.png', 'rb') as f:
    files = {'file': f}
    data = {
        'language': 'en',
        'include_confidence': True,
        'include_bounding_boxes': False
    }
    
    response = requests.post(
        'http://localhost:8500/v1/ocr/upload',
        files=files,
        data=data
    )
    
    result = response.json()
    print(f"Extracted text: {result['full_text']}")
```

### Expected JSON Response

```json
{
  "success": true,
  "message": "OCR processing completed successfully",
  "filename": "your-image.png",
  "detected_text": [
    {
      "text": "Sample detected text",
      "confidence": 0.95,
      "confidence_level": "high",
      "bounding_box": {
        "x": 10,
        "y": 20,
        "width": 200,
        "height": 30
      }
    }
  ],
  "full_text": "Sample detected text",
  "metadata": {
    "language": "en",
    "text_blocks_count": 1,
    "processing_time_ms": 150.5
  },
  "processing_time_ms": 150.5
}
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/health` | Application health check |
| `GET` | `/v1/ocr/health` | OCR service health check |
| `POST` | `/v1/ocr/upload` | Upload and process image |
| `POST` | `/v1/ocr/process` | Process with JSON options |
| `GET` | `/v1/ocr/supported-formats` | Get supported image formats |
| `GET` | `/v1/ocr/stats` | Service statistics |
| `GET` | `/v1/metrics` | Prometheus metrics |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ENABLE_FILE_LOGGING` | `true` | Enable logging to files |
| `DOTS_OCR_URL` | `http://dots-ocr:8000` | URL of dots.ocr service |

### Supported Image Formats

- JPEG/JPG
- PNG
- GIF
- BMP
- TIFF
- WebP

**File size limit:** 10MB

### Supported Languages

The service supports automatic language detection (`auto`) and specific language codes:

- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `it` - Italian
- `pt` - Portuguese
- `ru` - Russian
- `zh` - Chinese
- `ja` - Japanese
- `ko` - Korean

*Note: Actual language support depends on the configured dots.ocr model.*

## Project Structure

```
aip-ocr/
├── apps/
│   ├── main.py              # FastAPI application entry point
│   ├── core/
│   │   ├── cli.py          # CLI commands
│   │   └── routers/
│   │       └── health.py   # Health check endpoints
│   ├── metrics/            # Prometheus metrics
│   │   ├── base.py
│   │   ├── middleware.py
│   │   └── routers.py
│   └── ocr/               # OCR application
│       ├── routers.py     # OCR API endpoints
│       ├── service.py     # OCR service layer
│       ├── schemas.py     # Pydantic models
│       └── utils.py       # Utility functions
├── conf/                  # Configuration
│   ├── settings.py
│   ├── logging.py
│   └── enhanced_logging.py
├── tests/                 # Test suite
│   ├── test_health.py
│   ├── test_ocr.py
│   └── conftest.py
├── scripts/               # Deployment scripts
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
├── pyproject.toml
└── README.md
```

## Docker Services

### Production (`docker-compose.yml`)

- **fastapi_app**: Main FastAPI application
- **dots-ocr**: dots.ocr service for OCR processing
- **redis**: Caching layer (optional)
- **postgres**: Database for storing results (optional)

### Development (`docker-compose.dev.yml`)

- **fastapi_app**: FastAPI with hot reload
- **dots-ocr**: Mock service for development

## Testing

### Run Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=apps

# Run only unit tests
poetry run pytest -m unit

# Run integration tests (requires running services)
poetry run pytest --runintegration
```

### Test Categories

- **Unit Tests**: Fast tests that don't require external services
- **Integration Tests**: Tests that require running OCR service
- **Health Tests**: API endpoint validation

## Monitoring

### Prometheus Metrics

The application exposes Prometheus metrics at `/v1/metrics`:

- HTTP request metrics
- Response time histograms
- Error rates
- Custom OCR processing metrics

### Health Checks

- **Application Health**: `/v1/health`
- **OCR Service Health**: `/v1/ocr/health`
- **Docker Health Checks**: Built into containers

## Development

### Adding New Features

1. **API Endpoints**: Add to `apps/ocr/routers.py`
2. **Business Logic**: Implement in `apps/ocr/service.py`
3. **Data Models**: Define in `apps/ocr/schemas.py`
4. **Utilities**: Add to `apps/ocr/utils.py`
5. **Tests**: Create in `tests/`

### Code Style

```bash
# Format code
poetry run black apps tests

# Lint code
poetry run flake8 apps tests

# Type checking
poetry run mypy apps
```

## Deployment

### Production Deployment

1. **Build images:**

```bash
docker-compose build
```

2. **Deploy:**

```bash
docker-compose up -d
```

3. **Scale services:**

```bash
docker-compose up -d --scale fastapi_app=3
```

### Environment-Specific Configs

- **Development**: `docker-compose.dev.yml`
- **Staging**: `docker-compose.staging.yml` (create as needed)
- **Production**: `docker-compose.yml`

## Troubleshooting

### Common Issues

1. **OCR Service Not Available**
   ```bash
   # Check service status
   docker-compose ps
   
   # Check logs
   docker-compose logs dots-ocr
   ```

2. **File Upload Errors**
   ```bash
   # Check file permissions
   ls -la /tmp/uploads
   
   # Check disk space
   df -h
   ```

3. **Memory Issues**
   ```bash
   # Monitor resource usage
   docker stats
   ```

### Logs

```bash
# Application logs
docker-compose logs fastapi_app

# OCR service logs
docker-compose logs dots-ocr

# All services
docker-compose logs
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [dots.ocr](https://github.com/rednote-hilab/dots.ocr) for OCR processing
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation
