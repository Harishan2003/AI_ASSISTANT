import io
import sys
from pathlib import Path
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.qwen_vision_service import qwen_vision_service
from app.services.face_swap_service import face_swap_service
from app.tools.qwen_vision_tool import qwen_vision_tool
from app.tools.face_swap_tool import face_swap_tool


def create_dummy_image_bytes(color=(255, 100, 100), size=(200, 200)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.anyio
async def test_qwen_vision_service():
    img_bytes = create_dummy_image_bytes((120, 180, 240))
    res = await qwen_vision_service.analyze_image(
        image_input=img_bytes,
        prompt="Describe this image"
    )
    assert res.get("success") is True
    assert "analysis" in res or "model_used" in res


@pytest.mark.anyio
async def test_face_swap_service():
    src_bytes = create_dummy_image_bytes((255, 200, 150), (150, 150))
    tgt_bytes = create_dummy_image_bytes((50, 100, 200), (300, 300))

    res = await face_swap_service.swap_face(
        source_face_image=src_bytes,
        target_body_image=tgt_bytes,
        enhance_quality=True,
        save_filename="test_swap.jpg"
    )
    assert res.get("success") is True
    assert "output_path" in res or "output_base64" in res


@pytest.mark.anyio
async def test_tools_execution():
    img_bytes = create_dummy_image_bytes()
    # Save temp test image
    temp_path = Path(__file__).resolve().parent / "test_temp_img.jpg"
    with open(temp_path, "wb") as f:
        f.write(img_bytes)

    try:
        # Test Qwen Vision Tool
        tool_qwen = await qwen_vision_tool.execute(image_path=str(temp_path), prompt="Quick test")
        assert tool_qwen.success is True

        # Test Face Swap Tool
        tool_fs = await face_swap_tool.execute(source_face=str(temp_path), target_image=str(temp_path))
        assert tool_fs.success is True
    finally:
        if temp_path.exists():
            temp_path.unlink()
