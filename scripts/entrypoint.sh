#!/usr/bin/env sh
set -e

# Expected target model path (dot-free)
TARGET_PATH="${DOTS_OCR_MODEL_PATH:-/weights/DotsOCR}"
SRC_DOTTED="/weights_src/dots.ocr"
MODEL_ID="${DOTS_OCR_MODEL_ID:-rednote-hilab/dots.ocr}"

echo "[entrypoint] Target model path: $TARGET_PATH"

# If target path missing config.json but a dotted source exists, copy it over
if [ ! -f "$TARGET_PATH/config.json" ] && [ -d "$SRC_DOTTED" ]; then
  echo "[entrypoint] Target missing or incomplete. Found dotted source at $SRC_DOTTED. Copying to $TARGET_PATH ..."
  mkdir -p "$TARGET_PATH"
  # Use cp -a to preserve structure and symlinks
  cp -a "$SRC_DOTTED/." "$TARGET_PATH/"
  echo "[entrypoint] Copy complete."
fi

# If still missing, try downloading from Hugging Face Hub
if [ ! -f "$TARGET_PATH/config.json" ]; then
  echo "[entrypoint] No model found at $TARGET_PATH. Attempting download from Hugging Face: $MODEL_ID"
  python - <<PY
import os
from huggingface_hub import snapshot_download

target = os.environ.get("DOTS_OCR_MODEL_PATH", "/weights/DotsOCR")
model_id = os.environ.get("DOTS_OCR_MODEL_ID", "rednote-hilab/dots.ocr")
token = os.environ.get("HUGGINGFACE_HUB_TOKEN")

os.makedirs(target, exist_ok=True)
snapshot_download(repo_id=model_id, local_dir=target, local_dir_use_symlinks=False, token=token)
print("[entrypoint] Download complete.")
PY
fi

if [ ! -f "$TARGET_PATH/config.json" ]; then
  echo "[entrypoint] WARNING: No valid model found at $TARGET_PATH (config.json missing) after copy/download. The server will start but remain unhealthy until a model is available." >&2
fi

exec python -u /app/scripts/dots_ocr_cpu_server.py
