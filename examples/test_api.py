#!/usr/bin/env python3
"""
Example usage of the AIP OCR Service API.

This script demonstrates how to use the OCR service for processing images.
"""

import asyncio
import httpx
from pathlib import Path
import sys


async def test_ocr_service():
    """Test the OCR service with a sample request."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint
        print("🔍 Testing service health...")
        health_response = await client.get(f"{base_url}/v1/health")
        print(f"Service health: {health_response.status_code}")
        if health_response.status_code == 200:
            print(f"Status: {health_response.json()}")
        
        # Test OCR health
        print("\n🔍 Testing OCR service health...")
        ocr_health_response = await client.get(f"{base_url}/v1/ocr/health")
        print(f"OCR health: {ocr_health_response.status_code}")
        if ocr_health_response.status_code == 200:
            print(f"OCR Status: {ocr_health_response.json()}")
        
        # Test supported formats
        print("\n📋 Getting supported formats...")
        formats_response = await client.get(f"{base_url}/v1/ocr/supported-formats")
        if formats_response.status_code == 200:
            formats = formats_response.json()
            print(f"Supported formats: {formats['supported_formats']}")
            print(f"Max file size: {formats['max_file_size_mb']}MB")
        
        # Example image upload (would need actual image file)
        print("\n📤 Example image upload:")
        print("To upload an image, use:")
        print(f"curl -X POST '{base_url}/v1/ocr/upload' \\")
        print("  -H 'Content-Type: multipart/form-data' \\")
        print("  -F 'file=@your-image.png' \\")
        print("  -F 'language=auto' \\")
        print("  -F 'include_confidence=true'")


def create_sample_curl_commands():
    """Generate sample curl commands for testing."""
    commands = [
        "# Test service health",
        "curl -X GET 'http://localhost:8000/v1/health'",
        "",
        "# Test OCR health",
        "curl -X GET 'http://localhost:8000/v1/ocr/health'",
        "",
        "# Get supported formats",
        "curl -X GET 'http://localhost:8000/v1/ocr/supported-formats'",
        "",
        "# Upload and process an image",
        "curl -X POST 'http://localhost:8000/v1/ocr/upload' \\",
        "  -H 'Content-Type: multipart/form-data' \\",
        "  -F 'file=@sample-image.png' \\",
        "  -F 'language=auto' \\",
        "  -F 'include_confidence=true' \\",
        "  -F 'include_bounding_boxes=false'",
        "",
        "# Process with JSON options",
        "curl -X POST 'http://localhost:8000/v1/ocr/process' \\",
        "  -H 'Content-Type: multipart/form-data' \\",
        "  -F 'file=@sample-image.png' \\",
        "  -F 'options={\"language\":\"en\",\"include_confidence\":true,\"include_bounding_boxes\":true}'",
        "",
        "# Get service statistics",
        "curl -X GET 'http://localhost:8000/v1/ocr/stats'",
    ]
    
    return "\n".join(commands)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "curl":
        print("📝 Sample curl commands:")
        print("=" * 50)
        print(create_sample_curl_commands())
    else:
        print("🚀 Testing AIP OCR Service...")
        print("=" * 50)
        asyncio.run(test_ocr_service())
        print("\n💡 Run with 'curl' argument to get sample curl commands")
        print("   python examples/test_api.py curl")
