import os
import pytest
import anyio

os.environ["TESTING"] = "1"

from app.services.command_executor import execute_in_backend
from app.services.alarm_service import parse_alarm_or_reminder_query


@pytest.mark.anyio
async def test_alarm_and_inform_queries():
    res = parse_alarm_or_reminder_query("inform me in 2 minutes I need to cook")
    assert res is not None
    assert res["action"] == "set"
    assert "Cook" in res["alarm"]["label"] or "cook" in res["alarm"]["label"].lower()
    assert res["alarm"]["remaining_seconds"] == 120

    res2 = await execute_in_backend("inform me in 2 minutes I need to cook")
    assert "reminder" in res2.lower() or "alarm" in res2.lower()


@pytest.mark.anyio
async def test_friday_map_features():
    res1 = await execute_in_backend("do you have a holographic map")
    assert "Friday Tactical Holographic" in res1

    res2 = await execute_in_backend("open friday map")
    assert "ACTION:OPEN_FRIDAY_MAP" in res2

    res3 = await execute_in_backend("find trichy in friday map")
    assert "ACTION:FRIDAY_MAP_SEARCH:trichy" in res3

    res4 = await execute_in_backend("give map route for chennai to bengaluru")
    assert "ACTION:FRIDAY_MAP_ROUTE:chennai:bengaluru" in res4


@pytest.mark.anyio
async def test_settings_toggles():
    # 1. WhatsApp Monitoring Toggle
    res_wa_on = await execute_in_backend("turn on WhatsApp monitoring")
    assert "ACTIVE" in res_wa_on
    assert "ACTION:SET_WHATSAPP_SETTINGS" in res_wa_on

    res_wa_off = await execute_in_backend("turn off WhatsApp monitoring")
    assert "DEACTIVATED" in res_wa_off

    # 2. Battery Saver Toggle
    res_batt_off = await execute_in_backend("turn off battery saver")
    assert "DEACTIVATED" in res_batt_off
    assert "ACTION:SET_POWER_SETTINGS" in res_batt_off

    res_batt_on = await execute_in_backend("turn on battery saver")
    assert "ACTIVE" in res_batt_on
    assert "ACTION:SET_POWER_SETTINGS" in res_batt_on

    # 3. Device Monitoring Toggle
    res_dev_off = await execute_in_backend("disable the device monitoring")
    assert "DISABLED" in res_dev_off
    assert "ACTION:SET_DEVICE_MONITOR:false" in res_dev_off

    res_dev_on = await execute_in_backend("turn on device monitoring")
    assert "ENABLED" in res_dev_on
    assert "ACTION:SET_DEVICE_MONITOR:true" in res_dev_on


@pytest.mark.anyio
async def test_mouse_and_screen_vision():
    res_mouse = await execute_in_backend("where is mouse is pointing now")
    assert "mouse cursor" in res_mouse.lower()

    res_screen1 = await execute_in_backend("what is I am currently viewing")
    assert "focused on" in res_screen1.lower() or "application" in res_screen1.lower()

    res_screen2 = await execute_in_backend("what is on my current screen")
    assert "focused on" in res_screen2.lower() or "application" in res_screen2.lower()


@pytest.mark.anyio
async def test_auto_reply_and_map_variations():
    # WhatsApp AI Auto-reply toggles
    res_ar1 = await execute_in_backend("turn on AI Auto reply in WhatsApp monitoring")
    assert "ENABLED" in res_ar1
    assert "ACTION:SET_WHATSAPP_SETTINGS" in res_ar1

    res_ar2 = await execute_in_backend("turn on a Auto reply in WhatsApp monitoring")
    assert "ENABLED" in res_ar2
    assert "in WhatsApp monitoring" not in res_ar2

    res_ar3 = await execute_in_backend("turn off AI Auto reply")
    assert "DISABLED" in res_ar3

    # Map search commands without explicit google keyword
    res_map1 = await execute_in_backend("open map and search Trichy")
    assert "ACTION:FRIDAY_MAP_SEARCH:Trichy" in res_map1 or "ACTION:FRIDAY_MAP_SEARCH:trichy" in res_map1
    assert "ACTION:OPEN_FRIDAY_MAP" in res_map1

    res_map2 = await execute_in_backend("point out trichy on map")
    assert "ACTION:FRIDAY_MAP_SEARCH:trichy" in res_map2


@pytest.mark.anyio
async def test_device_control_and_telemetry():
    # 1. WhatsApp send with "call" in content should NOT decline call
    res_wa = await execute_in_backend("send the WhatsApp message to Harini saying that I will call you later")
    assert "declined" not in res_wa.lower()
    assert "harini" in res_wa.lower()
    assert "call you later" in res_wa.lower()

    # 2. System Power Controls
    res_lock = await execute_in_backend("lock the computer")
    assert "locked" in res_lock.lower()

    res_sleep = await execute_in_backend("put PC to sleep")
    assert "sleep" in res_sleep.lower()

    # 3. Live Hardware Telemetry
    res_stats = await execute_in_backend("Check system stats")
    assert "telemetry" in res_stats.lower() or "cpu" in res_stats.lower()
    assert "intel core i7-12700" not in res_stats.lower()  # No hallucinated Intel CPU
    assert "ram" in res_stats.lower()

    res_health = await execute_in_backend("Show system health")
    assert "telemetry" in res_health.lower() or "cpu" in res_health.lower()

    # 4. Folder Opening
    res_folder = await execute_in_backend("open memo filling folder in my screen")
    assert "opened" in res_folder.lower()


@pytest.mark.anyio
async def test_fast_ui_clicking_and_shortcuts():
    # 1. First link clicking
    res_click = await execute_in_backend("can you click the first link")
    assert "clicked" in res_click.lower() or "link" in res_click.lower()

    # 2. Scrolling and Zooming shortcuts
    res_scroll = await execute_in_backend("scroll down")
    assert "scrolled" in res_scroll.lower()

    res_zoom = await execute_in_backend("zoom in")
    assert "zoomed in" in res_zoom.lower()



