"""
Minimal CPU server for dots.ocr using Hugging Face Transformers.

Run:
  export DOTS_OCR_MODEL_PATH=/path/to/weights/DotsOCR
  export PORT=8501
  python scripts/dots_ocr_cpu_server.py

Notes:
- Ensure model weights directory name contains no dots (e.g., DotsOCR).
- This uses CPU (device_map="cpu") and sets attention to "sdpa" as recommended.
"""

import io
import os
import json
import logging
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

import torch
from transformers import AutoModelForCausalLM, AutoProcessor

try:
    from qwen_vl_utils import process_vision_info
except Exception:  # pragma: no cover
    process_vision_info = None

# Use a basic default prompt. Upstream prompts are available in the repo but not required here.
dict_promptmode_to_prompt = {"prompt_layout_all_en": "Please parse all layout info in English."}


class OCRResponse(BaseModel):
    success: bool
    message: str
    predictions: list


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover
    # Load on startup but don't crash on failure
    global _load_error
    try:
        load_model()
    except Exception as e:
        _load_error = f"Model load failed: {e}"
        logging.exception("Model load failed")
    yield
    # No teardown necessary


app = FastAPI(title="dots.ocr CPU Server", version="0.1.0", lifespan=lifespan)

MODEL_PATH = os.getenv("DOTS_OCR_MODEL_PATH", "./weights/DotsOCR")
MODEL_ID_FALLBACK = os.getenv("DOTS_OCR_MODEL_ID", None)
PROMPT_MODE = os.getenv("DOTS_OCR_PROMPT", "prompt_layout_all_en")

_model = None
_processor = None
_load_error: Optional[str] = None


def _is_valid_hf_model_dir(path: str) -> bool:
    try:
        cfg_path = os.path.join(path, "config.json")
        if not os.path.isfile(cfg_path):
            return False
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return bool(cfg.get("model_type") or cfg.get("auto_map") or cfg.get("architectures"))
    except Exception:
        return False


def load_model():  # pragma: no cover
    global _model, _processor
    # Prefer float32 on CPU
    torch_dtype = torch.float32
    # Guard: folder names containing dots can break transformers dynamic module imports
    def _has_dot_in_any_segment(p: str) -> bool:
        for seg in os.path.normpath(p).split(os.sep):
            if seg and '.' in seg:
                return True
        return False

    # If the model path still contains dots after entrypoint, warn (copy may have failed)
    if _has_dot_in_any_segment(MODEL_PATH):
        logging.warning(
            "Model path contains '.' segments. If you mounted models/dots.ocr, the entrypoint should have copied it to a dot-free path."
        )
    # Choose source (local HF dir or hub ID fallback)
    if os.path.isdir(MODEL_PATH) and _is_valid_hf_model_dir(MODEL_PATH):
        source = MODEL_PATH
    elif MODEL_ID_FALLBACK:
        source = MODEL_ID_FALLBACK
        logging.warning("Using DOTS_OCR_MODEL_ID fallback: %s", source)
    else:
        raise RuntimeError(
            "DOTS_OCR_MODEL_PATH is not a valid Hugging Face model directory (missing config.json/model_type). "
            "Set DOTS_OCR_MODEL_ID to a Hub model (e.g., 'Qwen/Qwen2.5-VL-3B-Instruct') or mount a valid model."
        )
    try:
        _model = AutoModelForCausalLM.from_pretrained(
            source,
            torch_dtype=torch_dtype,
            device_map="cpu",
            trust_remote_code=True,
        )
    except ValueError as e:
        # e.g., "Using a `device_map` or `tp_plan` requires `accelerate`"
        if "requires `accelerate`" in str(e).lower():
            logging.warning("accelerate not available; loading model on CPU without device_map.")
            _model = AutoModelForCausalLM.from_pretrained(
                source,
                torch_dtype=torch_dtype,
                trust_remote_code=True,
            )
            _model.to("cpu")
        else:
            raise
    # Force CPU-friendly attention
    if hasattr(_model, "config"):
        try:
            setattr(_model.config, "attn_implementation", "sdpa")
        except Exception:
            pass
    _processor = AutoProcessor.from_pretrained(source, trust_remote_code=True)


@app.get("/health")
def health():
    ok = _model is not None and _processor is not None
    if ok:
        return {"status": "healthy"}
    if _load_error:
        return {"status": "error", "message": _load_error}
    return {"status": "loading"}


@app.post("/ocr")
async def ocr(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    include_confidence: bool = Form(True),
    include_bounding_boxes: bool = Form(False),
):
    try:
        if _model is None or _processor is None:
            return JSONResponse(status_code=503, content={"success": False, "message": _load_error or "Model not ready", "predictions": []})
        content = await file.read()
        image_bytes = io.BytesIO(content)

        prompt = dict_promptmode_to_prompt.get(PROMPT_MODE, "Please parse the document.")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image_bytes},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        if process_vision_info is None:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "qwen_vl_utils not installed",
                    "predictions": [],
                },
            )

        text = _processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = _processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        # Keep on CPU
        generated_ids = _model.generate(**inputs, max_new_tokens=4096)
        generated_ids_trimmed = [
            out_ids[len(in_ids) :]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = _processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]

        # Return in a simple predictions format our FastAPI understands
        return OCRResponse(
            success=True,
            message="ok",
            predictions=[{"text": output_text, "confidence": 0.9}],
        )
    except Exception as e:  # pragma: no cover
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e), "predictions": []},
        )


if __name__ == "__main__":  # pragma: no cover
    port = int(os.getenv("PORT", "8501"))
    uvicorn.run(app, host="0.0.0.0", port=port)
