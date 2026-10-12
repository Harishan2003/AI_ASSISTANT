"""
Vision & Face Swap API Endpoints for Friday AI Assistant.
Exposes endpoints for:
1. Qwen-Image-2.1 Uncensored Multimodal Vision Analysis (abenzerps/Qwen-Image-2.1-Uncensored-GGUF)
2. BFS Best Face Swap (Alissonerdx/BFS-Best-Face-Swap)
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.qwen_vision_service import qwen_vision_service
from app.services.face_swap_service import face_swap_service

router = APIRouter(prefix="/vision-models", tags=["Vision Models & Face Swap"])


class QwenVisionRequest(BaseModel):
    image_base64: Optional[str] = None
    image_path: Optional[str] = None
    prompt: Optional[str] = "Analyze and describe this image in vivid, comprehensive, uncensored detail."
    temperature: Optional[float] = 0.4


class FaceSwapRequest(BaseModel):
    source_face_base64: Optional[str] = None
    source_face_path: Optional[str] = None
    target_image_base64: Optional[str] = None
    target_image_path: Optional[str] = None
    enhance: Optional[bool] = True


@router.post("/qwen-analyze")
async def analyze_with_qwen(req: QwenVisionRequest):
    """Deep uncensored image inspection using Qwen-Image-2.1."""
    img_input = req.image_base64 or req.image_path
    if not img_input:
        raise HTTPException(status_code=400, detail="Must provide either image_base64 or image_path.")
    
    res = await qwen_vision_service.analyze_image(
        image_input=img_input,
        prompt=req.prompt or "Analyze this image thoroughly.",
        temperature=req.temperature or 0.4
    )
    return res


@router.post("/qwen-upload")
async def analyze_with_qwen_upload(
    file: UploadFile = File(...),
    prompt: str = Form("Analyze and describe this image thoroughly.")
):
    """Upload an image file directly for uncensored Qwen visual analysis."""
    contents = await file.read()
    res = await qwen_vision_service.analyze_image(image_input=contents, prompt=prompt)
    return res


@router.post("/face-swap")
async def execute_face_swap(req: FaceSwapRequest):
    """High-fidelity face swapping using BFS Best Face Swap."""
    src = req.source_face_base64 or req.source_face_path
    tgt = req.target_image_base64 or req.target_image_path

    if not src or not tgt:
        raise HTTPException(status_code=400, detail="Both source_face and target_image must be provided.")

    res = await face_swap_service.swap_face(
        source_face_image=src,
        target_body_image=tgt,
        enhance_quality=bool(req.enhance)
    )
    return res


@router.post("/face-swap-upload")
async def execute_face_swap_upload(
    source_face: UploadFile = File(...),
    target_body: UploadFile = File(...),
    enhance: bool = Form(True)
):
    """Upload source face and target image files for instant AI face swap."""
    src_bytes = await source_face.read()
    tgt_bytes = await target_body.read()

    res = await face_swap_service.swap_face(
        source_face_image=src_bytes,
        target_body_image=tgt_bytes,
        enhance_quality=enhance
    )
    return res
