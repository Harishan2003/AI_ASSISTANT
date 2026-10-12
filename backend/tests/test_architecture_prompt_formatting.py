import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.prompt_generator_service import prompt_generator_service
from app.core.agent_config import agent_config


@pytest.mark.anyio
async def test_prompt_formatting_has_fenced_blocks():
    res = await prompt_generator_service.generate("cyberpunk flying vehicle in neon rain", target_type="image")
    formatted = prompt_generator_service.format_to_natural_speech(res)
    assert "```prompt" in formatted or "```" in formatted
    assert "```" in formatted


def test_agent_config_has_architecture_instruction():
    instruction = agent_config.get_system_instruction(
        agent_name="Friday",
        user_name="Harishan",
        user_age="21",
        user_email="harishan@example.com",
        user_city="Chennai",
        language="english",
        live_web_context=""
    )
    assert "PROJECT ARCHITECTURE FORMATTING" in instruction or "architecture" in instruction.lower()
    assert "```project_architecture" in instruction or "fenced code block" in instruction
