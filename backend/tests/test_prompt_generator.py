import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.prompt_generator_service import prompt_generator_service
from app.tools.prompt_generator_tool import prompt_generator_tool
from app.services.command_executor import execute_in_backend


@pytest.mark.anyio
async def test_prompt_generator_image():
    res = await prompt_generator_service.generate("cyberpunk flying vehicle in rain", target_type="image")
    assert res["category"] == "image"
    assert "master_prompt" in res
    formatted = prompt_generator_service.format_to_natural_speech(res)
    assert len(formatted) > 50


@pytest.mark.anyio
async def test_prompt_generator_code():
    res = await prompt_generator_service.generate("FastAPI WebSocket Chat Server", target_type="code")
    assert res["category"] == "code"
    assert "master_prompt" in res


@pytest.mark.anyio
async def test_prompt_generator_tool():
    tool_res = await prompt_generator_tool.execute(topic="photorealistic portrait of a robotic warrior", target_type="image")
    assert tool_res.success is True
    assert "master_prompt" in tool_res.data


@pytest.mark.anyio
async def test_command_executor_prompt_generation():
    reply = await execute_in_backend("generate a prompt for a luxury modern villa with swimming pool at sunset")
    assert "Prompt" in reply or "prompt" in reply
    assert len(reply) > 50
