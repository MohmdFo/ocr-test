# dots.ocr on CPU (Transformers)

This guide shows how to run rednote-hilab/dots.ocr on CPU using Hugging Face Transformers and expose a simple HTTP API compatible with this project.

Upstream repo: https://github.com/rednote-hilab/dots.ocr

Notes from the official README:
- Prefer vLLM for deployment, but CPU usage is recommended via Transformers (see “Huggingface inference with CPU”).
- Use a model weights directory name without a dot (e.g., `DotsOCR` instead of `dots.ocr`).
- Set attention implementation to "sdpa" or "eager" for CPU.

## Option A: Run in Docker (recommended)

1) Download model weights
- Place them under `./models/DotsOCR` (note the folder name)
- Or use their script: `python3 tools/download_model.py` inside the upstream repo and then copy to `models/DotsOCR` here.

2) Build and run the CPU server

```bash
# Build and start only the CPU OCR server
docker compose -f docker-compose.dots-ocr-cpu.yml up -d --build

# Check health
curl -sf http://localhost:8501/health
```

3) Point your app to it
- Set in `.env` of this repo:

```
DOTS_OCR_URL=http://localhost:8501
```

- Recreate your API service if needed.

## Option B: Run locally without Docker

Create a Python virtualenv and install CPU dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install torch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 --index-url https://download.pytorch.org/whl/cpu
pip install transformers==4.51.3 qwen_vl_utils==0.0.11 fastapi==0.116.1 uvicorn[standard]==0.30.6
# Optional: prompts/utils from upstream repo
pip install -e git+https://github.com/rednote-hilab/dots.ocr.git#egg=dots_ocr
```

Run the server:

```bash
export DOTS_OCR_MODEL_PATH=/absolute/path/to/weights/DotsOCR
export PORT=8501
python scripts/dots_ocr_cpu_server.py
```

Test:

```bash
curl -sf http://localhost:8501/health
```

## Important CPU Tips
- Directory name for weights must avoid dots: `DotsOCR`.
- CPU is slower; keep images small to start.
- If you hit attention issues, ensure the model’s config uses `attn_implementation="sdpa"` (the helper server sets it if possible).

## Integration with this project
- We’ve removed the dots.ocr container from our main `docker-compose.yml` to prevent dependency conflicts.
- The API reads `DOTS_OCR_URL` from environment (default `http://localhost:8501`).
- Use `docker-compose.dots-ocr-cpu.yml` to host the OCR CPU server separately.

## References
- Upstream README section: "Hugginface inference with CPU" (linked from their issue comment).
- Issue reference with code snippet: https://github.com/rednote-hilab/dots.ocr/issues/1#issuecomment-3148962536