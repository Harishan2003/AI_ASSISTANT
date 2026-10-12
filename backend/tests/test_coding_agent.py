# Tests for Coding Agent Service and MCP Integration
import asyncio
import os
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.coding_agent_service import coding_agent_service
from app.mcp.server import mcp_server, get_mcp_tools_list


async def test_coding_agent_system():
    print("1. Testing Code Generation & Syntax Verification...")
    res = await coding_agent_service.generate_code(
        prompt="Write a Python function to compute the Fibonacci sequence up to N elements with type annotations and docstrings.",
        language="python"
    )
    print("   Source used:", res.get("source"))
    print("   Model:", res.get("model_used"))
    syntax = res.get("syntax_verification", {})
    print("   Syntax check:", syntax)
    assert res["success"] is True
    assert "def " in res["code_response"] or "fibonacci" in res["code_response"].lower()
    print("   Code Generation Passed!")

    print("\n2. Testing Code Debugging...")
    buggy_code = """
def sum_even_numbers(numbers):
    total = 0
    for n in numbers
        if n % 2 = 0:
            total += n
    return total
"""
    debug_res = await coding_agent_service.debug_code(
        code=buggy_code,
        error_message="SyntaxError: invalid syntax",
        language="python"
    )
    assert debug_res["success"] is True
    print("   Debugging Output Verified!")

    print("\n3. Testing MCP Server Registered Tools...")
    tools = get_mcp_tools_list()
    tool_names = [t["name"] for t in tools]
    print("   Total Registered MCP Tools:", len(tools))
    print("   Coding Tools present:")
    for ct in ["friday_generate_code", "friday_debug_code", "friday_refactor_code", "friday_explain_code"]:
        assert ct in tool_names, f"Missing {ct} in MCP server!"
        print(f"     [x] {ct}")

    print("\nALL CODING AGENT & MCP TESTS PASSED PERFECTLY!")


if __name__ == "__main__":
    asyncio.run(test_coding_agent_system())
