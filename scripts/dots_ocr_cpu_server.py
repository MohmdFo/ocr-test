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
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form
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


app = FastAPI(title="dots.ocr CPU Server", version="0.1.0")

MODEL_PATH = os.getenv("DOTS_OCR_MODEL_PATH", "./weights/DotsOCR")
PROMPT_MODE = os.getenv("DOTS_OCR_PROMPT", "prompt_layout_all_en")

_model = None
_processor = None


@app.on_event("startup")
def load_model():  # pragma: no cover
    global _model, _processor
    # Prefer float32 on CPU
    torch_dtype = torch.float32
    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch_dtype,
        device_map="cpu",
        trust_remote_code=True,
    )
    # Force CPU-friendly attention
    if hasattr(_model, "config"):
        try:
            setattr(_model.config, "attn_implementation", "sdpa")
        except Exception:
            pass
    _processor = AutoProcessor.from_pretrained(MODEL_PATH, trust_remote_code=True)


@app.get("/health")
def health():
    ok = _model is not None and _processor is not None
    return {"status": "healthy" if ok else "loading"}


@app.post("/ocr")
async def ocr(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    include_confidence: bool = Form(True),
    include_bounding_boxes: bool = Form(False),
):
    try:
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
