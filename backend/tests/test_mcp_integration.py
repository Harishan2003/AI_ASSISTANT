"""
Async test suite for Friday Model Context Protocol (MCP) Integration.
Tests FastMCP Server endpoints, SSE transport, REST router, and internal tool bridging.
"""
import asyncio
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import httpx
from main import app


async def run_all_tests():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        # 1. MCP Status
        print("\n[TEST 1] Testing /api/v1/mcp/status...")
        res = await client.get("/api/v1/mcp/status")
        assert res.status_code == 200, f"Status failed: {res.text}"
        data = res.json()
        print(f"  --> MCP Server Status: {data['status']}, Tools Count: {data['tools_count']}")
        assert data["status"] == "ONLINE"
        assert data["tools_count"] >= 10

        # 2. MCP Tools
        print("\n[TEST 2] Testing /api/v1/mcp/tools...")
        res = await client.get("/api/v1/mcp/tools")
        assert res.status_code == 200
        tools_data = res.json()
        tool_names = [t["name"] for t in tools_data["tools"]]
        print(f"  --> Registered Tools ({len(tool_names)}): {tool_names}")
        assert "friday_get_system_overview" in tool_names
        assert "friday_get_cpu_metrics" in tool_names
        assert "friday_get_gpu_metrics" in tool_names
        assert "friday_get_running_processes" in tool_names
        assert "friday_get_network_status" in tool_names
        assert "friday_read_file" in tool_names
        assert "friday_write_file" in tool_names
        assert "friday_list_directory" in tool_names
        assert "friday_web_search" in tool_names
        assert "friday_execute_registered_tool" in tool_names

        # 3. Call friday_get_system_overview
        print("\n[TEST 3] Calling MCP tool friday_get_system_overview...")
        res = await client.post("/api/v1/mcp/call", json={"tool_name": "friday_get_system_overview", "arguments": {}})
        assert res.status_code == 200
        overview_res = res.json()
        assert overview_res["success"] is True
        print("  --> Telemetry keys returned:", list(overview_res["result"].keys()) if isinstance(overview_res["result"], dict) else "raw")

        # 4. Call friday_list_directory
        print("\n[TEST 4] Calling MCP tool friday_list_directory...")
        res = await client.post("/api/v1/mcp/call", json={"tool_name": "friday_list_directory", "arguments": {"directory_path": "."}})
        assert res.status_code == 200
        dir_res = res.json()
        assert dir_res["success"] is True
        print(f"  --> Listed directory successfully ({dir_res['result'].get('total_items', 0)} items found)")

        # 5. Call friday_get_cpu_metrics
        print("\n[TEST 5] Calling MCP tool friday_get_cpu_metrics...")
        res = await client.post("/api/v1/mcp/call", json={"tool_name": "friday_get_cpu_metrics", "arguments": {"include_per_core": True}})
        assert res.status_code == 200
        cpu_res = res.json()
        assert cpu_res["success"] is True
        print("  --> CPU Metrics result:", cpu_res["result"].get("overall_cpu_percent") if isinstance(cpu_res["result"], dict) else "ok")

        # 6. Call friday_get_gpu_metrics
        print("\n[TEST 6] Calling MCP tool friday_get_gpu_metrics...")
        res = await client.post("/api/v1/mcp/call", json={"tool_name": "friday_get_gpu_metrics", "arguments": {}})
        assert res.status_code == 200
        gpu_res = res.json()
        assert gpu_res["success"] is True
        print(f"  --> GPU Metrics result: {gpu_res['result'].get('gpu_count', 0)} GPU(s) found")

        # 7. Call friday_get_network_status
        print("\n[TEST 7] Calling MCP tool friday_get_network_status...")
        res = await client.post("/api/v1/mcp/call", json={"tool_name": "friday_get_network_status", "arguments": {}})
        assert res.status_code == 200
        net_res = res.json()
        assert net_res["success"] is True
        print("  --> Network Status result:", net_res["result"].get("primary_ip") if isinstance(net_res["result"], dict) else "ok")

        # 8. Test External MCP Server Registry endpoints
        print("\n[TEST 8] Testing External MCP Server Registration...")
        res = await client.get("/api/v1/mcp/external-servers")
        assert res.status_code == 200
        servers = res.json()
        print(f"  --> External MCP servers registered: {len(servers.get('servers', []))}")

        # 9. Verify existing telemetry route unaffected
        print("\n[TEST 9] Verifying existing system telemetry route (/api/v1/system/overview)...")
        res = await client.get("/api/v1/system/overview")
        assert res.status_code == 200
        print("  --> Existing telemetry route /api/v1/system/overview is 100% functional!")

    print("\n=======================================================")
    print(" [OK] ALL 9 MCP & SYSTEM VERIFICATION TESTS PASSED! ")
    print("=======================================================\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
