import pytest
from fastapi.testclient import TestClient
from main import app, load_power_settings, save_power_settings

@pytest.fixture
def client():
    return TestClient(app)

def test_power_settings_get_and_post(client):
    # 1. GET power settings
    res = client.get("/api/v1/settings/power")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "settings" in data
    assert "eco_mode" in data["settings"]
    assert "auto_battery_saver" in data["settings"]
    assert "is_eco_active" in data

    # 2. POST update power settings
    res_update = client.post("/api/v1/settings/power", json={
        "eco_mode": True,
        "auto_battery_saver": True,
        "telemetry_interval_battery": 6.0,
        "telemetry_interval_ac": 2.0
    })
    assert res_update.status_code == 200
    up_data = res_update.json()
    assert up_data["status"] == "success"
    assert up_data["settings"]["eco_mode"] is True
    assert up_data["settings"]["auto_battery_saver"] is True
    assert up_data["settings"]["telemetry_interval_battery"] == 6.0
