import pytest
import asyncio
from app.services.agent_feature_scanner import AgentFeatureScanner

@pytest.mark.asyncio
async def test_scanner_initialization():
    scanner = AgentFeatureScanner()
    assert scanner is not None

@pytest.mark.asyncio
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

@pytest.mark.asyncio
async def test_feature_isolation_on_failure():
    scanner = AgentFeatureScanner()
    
    # Mock one test to raise an exception
    async def mock_faulty_test():
        raise RuntimeError("Simulated test crash")

    scanner._test_calculator = mock_faulty_test
    results = await scanner.scan_all_features()
    
    calc_result = next((r for r in results if r["feature"] == "Calculator"), None)
    assert calc_result is not None
    assert calc_result["status"] == "failed"
    assert "Simulated test crash" in calc_result["error"]
    
    # Verify other tests still ran successfully
    mic_result = next((r for r in results if r["feature"] == "Microphone"), None)
    assert mic_result["status"] == "working"