#!/bin/bash

# Script to download the dots.ocr model
# Model source: https://www.modelscope.cn/models/rednote-hilab/dots.ocr

set -e

MODEL_DIR="./models/dots.ocr"
MODEL_URL="https://www.modelscope.cn/models/rednote-hilab/dots.ocr"

echo "Setting up dots.ocr model download..."

# Check if model directory already exists and has content
if [ -d "$MODEL_DIR" ] && [ "$(ls -A $MODEL_DIR)" ]; then
    echo "Model directory already exists and contains files."
    echo "Skipping download. Remove $MODEL_DIR if you want to re-download."
    exit 0
fi

# Create model directory
mkdir -p "$MODEL_DIR"

echo "Model needs to be downloaded manually from:"
echo "$MODEL_URL"
echo ""
echo "Please download the model and extract it to: $MODEL_DIR"
echo ""
echo "The directory structure should look like:"
echo "$MODEL_DIR/"
echo "├── config.json"
echo "├── pytorch_model.bin"
echo "└── ... (other model files)"
echo ""
echo "After downloading, run: docker compose up -d"
echo ""
echo "Note: This model is quite large (>10GB) and requires significant disk space."

# Optional: Try to use modelscope CLI if available
if command -v modelscope &> /dev/null; then
    echo "modelscope CLI found. Attempting automatic download..."
    echo "This may take a while depending on your internet connection..."
    modelscope download --model rednote-hilab/dots.ocr --local_dir "$MODEL_DIR"
    echo "Model downloaded successfully!"
else
    echo "modelscope CLI not found. Installing it in a virtual environment..."
    if command -v python3 &> /dev/null; then
        # Create a temporary virtual environment for modelscope
        VENV_DIR="/tmp/modelscope_venv"
        python3 -m venv "$VENV_DIR"
        source "$VENV_DIR/bin/activate"
        pip install modelscope
        echo "modelscope installed. Attempting automatic download..."
        modelscope download --model rednote-hilab/dots.ocr --local_dir "$MODEL_DIR"
        echo "Model downloaded successfully!"
        deactivate
        rm -rf "$VENV_DIR"
    else
        echo "python3 not found. Please install modelscope manually with:"
        echo "pip install modelscope"
        echo "or download manually from the URL above."
    fi
fi
