#!/bin/bash

# Setup script for dots.ocr dependency
# This script clones the dots.ocr repository and prepares it for Docker building

set -e

echo "Setting up dots.ocr dependency..."

# Check if dots-ocr directory already exists
if [ -d "dots-ocr" ]; then
    echo "dots-ocr directory already exists. Updating..."
    cd dots-ocr
    git pull origin main
    cd ..
else
    echo "Cloning dots.ocr repository..."
    git clone https://github.com/rednote-hilab/dots.ocr.git dots-ocr

    # Check if the repository has a Dockerfile
    if [ ! -f "dots-ocr/Dockerfile" ]; then
        echo "Warning: No Dockerfile found in dots.ocr repository."
        echo "You may need to create one or check the repository documentation."
        echo ""
        echo "Common Dockerfile template for Python/FastAPI projects:"
        echo "FROM python:3.9-slim"
        echo "WORKDIR /app"
        echo "COPY requirements.txt ."
        echo "RUN pip install -r requirements.txt"
        echo "COPY . ."
        echo "EXPOSE 8000"
        echo 'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]'
        echo ""
        echo "Please check the dots.ocr repository README for build instructions."
        exit 1
    fi
fi

echo "dots.ocr setup complete!"
echo "You can now run: docker compose up -d"
