#!/usr/bin/env sh
set -e

# Expected target model path (dot-free)
TARGET_PATH="${DOTS_OCR_MODEL_PATH:-/weights/DotsOCR}"
SRC_DOTTED="/weights_src/dots.ocr"

echo "[entrypoint] Target model path: $TARGET_PATH"

# If target path missing config.json but a dotted source exists, copy it over
if [ ! -f "$TARGET_PATH/config.json" ] && [ -d "$SRC_DOTTED" ]; then
  echo "[entrypoint] Target missing or incomplete. Found dotted source at $SRC_DOTTED. Copying to $TARGET_PATH ..."
  mkdir -p "$TARGET_PATH"
  # Use cp -a to preserve structure and symlinks
  cp -a "$SRC_DOTTED/." "$TARGET_PATH/"
  echo "[entrypoint] Copy complete."
fi

if [ ! -f "$TARGET_PATH/config.json" ]; then
  echo "[entrypoint] WARNING: No valid model found at $TARGET_PATH (config.json missing). The server will start but remain unhealthy until a model is available." >&2
fi

exec python -u /app/scripts/dots_ocr_cpu_server.py
