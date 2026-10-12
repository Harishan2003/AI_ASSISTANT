import pytest
import asyncio
from app.services.agent_feature_scanner import AgentFeatureScanner

@pytest.mark.anyio
async def test_scanner_initialization():
    scanner = AgentFeatureScanner()
    assert scanner is not None

@pytest.mark.anyio
async def test_scan_all_features_structure():
    scanner = AgentFeatureScanner()
    results = await scanner.scan_all_features()
    
    assert isinstance(results, list)
    assert len(results) >= 20
    
    for item in results:
        assert "feature" in item
        assert "status" in item
        assert "duration_ms" in item
        assert "details" in item
        assert "error" in item
        assert "tested_at" in item
        assert item["status"] in ["working", "failed", "skipped", "unavailable", "permission_required", "not_configured"]

@pytest.mark.anyio
async def test_feature_isolation_on_failure():
    scanner = AgentFeatureScanner()
    
    # Mock one test to raise an exception
    async def mock_faulty_test():
        raise RuntimeError("Simulated test crash")

    scanner._test_cpu_telemetry = mock_faulty_test
    results = await scanner.scan_all_features()
    
    cpu_result = next((r for r in results if "CPU" in r["feature"]), None)
    assert cpu_result is not None
    assert cpu_result["status"] == "failed"
    assert "Simulated test crash" in cpu_result["error"]
    
    # Verify other tests still ran successfully
    mic_result = next((r for r in results if "Microphone" in r["feature"]), None)
    assert mic_result is not None
    assert mic_result["status"] == "working"