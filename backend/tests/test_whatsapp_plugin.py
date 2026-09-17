import pytest
from app.services.whatsapp_service import whatsapp_service
from app.tools.whatsapp.whatsapp_tools import (
    SendWhatsAppMessageTool,
    StartWhatsAppCallTool,
    ToggleWhatsAppMonitorTool,
    GetWhatsAppStatusTool
)


def test_whatsapp_service_status_and_settings():
    initial_status = whatsapp_service.get_status()
    assert isinstance(initial_status, dict)
    assert "enabled" in initial_status
    assert "auto_reply" in initial_status
    assert "monitoring_active" in initial_status
    assert "replied_count" in initial_status

    # Test toggling settings via set_monitoring
    updated = whatsapp_service.set_monitoring(enabled=True, auto_reply=True)
    assert updated["monitoring_active"] is True
    assert updated["auto_reply"] is True

    # Revert to safe test default
    whatsapp_service.set_monitoring(enabled=False, auto_reply=False)


def test_whatsapp_auto_reply_generation():
    reply_greeting = whatsapp_service.generate_auto_reply("Alice", "Hello there!")
    assert isinstance(reply_greeting, str)
    assert len(reply_greeting) > 0

    reply_busy = whatsapp_service.generate_auto_reply("Bob", "Are you free for a call?")
    assert isinstance(reply_busy, str)


def test_whatsapp_tools_invocation():
    # 1. Status Tool
    status_tool = GetWhatsAppStatusTool()
    status_res = status_tool.run()
    assert status_res.success is True
    assert "enabled" in status_res.data

    # 2. Toggle Monitor Tool
    toggle_tool = ToggleWhatsAppMonitorTool()
    toggle_res = toggle_tool.run(status="off")
    assert toggle_res.success is True
    assert toggle_res.data["monitoring_active"] is False

    # 3. Validation for Send Tool
    send_tool = SendWhatsAppMessageTool()
    send_fail = send_tool.run(contact="", message="")
    assert send_fail.success is False

    # 4. Validation for Call Tool
    call_tool = StartWhatsAppCallTool()
    call_fail = call_tool.run(contact="")
    assert call_fail.success is False


@pytest.mark.anyio
async def test_whatsapp_natural_language_queries():
    from main import execute_in_backend

    # 1. Status query
    status_ans = await execute_in_backend("are you monitoring my WhatsApp", session_id="test_wa")
    assert "whatsapp" in status_ans.lower()
    assert "monitoring" in status_ans.lower()

    # 2. Turn ON monitor query
    turn_on_ans = await execute_in_backend("monitor my WhatsApp", session_id="test_wa")
    assert "active" in turn_on_ans.lower() or "activated" in turn_on_ans.lower()

    # 3. Status query when active
    active_status_ans = await execute_in_backend("is WhatsApp monitoring active", session_id="test_wa")
    assert "active" in active_status_ans.lower()

    # 4. Turn OFF monitor query
    turn_off_ans = await execute_in_backend("stop monitoring WhatsApp", session_id="test_wa")
    assert "deactivated" in turn_off_ans.lower() or "off" in turn_off_ans.lower()

    # 5. Set custom auto-reply command (long format)
    custom_rule_ans = await execute_in_backend(
        "if any sent message to me means reply them i well call u later on",
        session_id="test_wa"
    )
    assert "reply" in custom_rule_ans.lower()
    
    # Verify the custom auto-reply is saved and generated
    reply = whatsapp_service.generate_auto_reply("John", "Hey, are you free?")
    assert "call" in reply.lower()

    # 6. Set custom auto-reply command (short format: reply them "i will call u later")
    short_rule_ans = await execute_in_backend(
        'reply them "i will call u later"',
        session_id="test_wa"
    )
    assert "auto-reply" in short_rule_ans.lower()
    assert "i will call u later" in short_rule_ans.lower()
    assert whatsapp_service.settings.get("custom_auto_reply_message") == "i will call u later"

    # 7. Check message history query (no fake hallucinated names)
    history_ans = await execute_in_backend(
        "who are all sent message to me in whatsapp",
        session_id="test_wa"
    )
    assert "no new whatsapp messages" in history_ans.lower() or "has sent" in history_ans.lower() or "new whatsapp" in history_ans.lower()
    # Confirm NO hallucinated contacts (e.g. Ravi Kumar)
    assert "ravi kumar" not in history_ans.lower()
    assert "priya singh" not in history_ans.lower()

    # 8. Compound monitor command: 'monitor my WhatsApp and send the AUTO-REPLY MESSAGE'
    compound_ans = await execute_in_backend(
        "monitor my WhatsApp and send the AUTO-REPLY MESSAGE",
        session_id="test_wa"
    )
    assert "active" in compound_ans.lower()
    assert "auto-reply" in compound_ans.lower()
    assert "dispatched whatsapp message to the" not in compound_ans.lower()

    # 9. Natural history query: 'friday who have send message to my whatsapp'
    who_have_ans = await execute_in_backend(
        "friday who have send message to my whatsapp",
        session_id="test_wa"
    )
    assert "dispatched whatsapp message to my" not in who_have_ans.lower()
    assert ("no new whatsapp messages" in who_have_ans.lower() or "has sent" in who_have_ans.lower() or "new whatsapp" in who_have_ans.lower())

    # 10. Call attend / answer query
    attend_ans = await execute_in_backend("attend the call", session_id="test_wa")
    assert "attending the incoming whatsapp call" in attend_ans.lower() or "incoming call" in attend_ans.lower()

    # 11. Call reject / decline query
    decline_ans = await execute_in_backend("reject the call", session_id="test_wa")
    assert "declined" in decline_ans.lower() or "call" in decline_ans.lower()

    # 12. Call contact query: 'call to Harini'
    call_ans = await execute_in_backend("call to Harini", session_id="test_wa")
    assert "harini" in call_ans.lower()
    assert "call" in call_ans.lower()

    # 13. Group message rejection test
    assert whatsapp_service._is_group_notification("Project Team", ["Project Team", "Ravi", "Hi all"], "Ravi - Hi all") is True
    assert whatsapp_service._is_group_notification("College Friends", ["College Friends", "Lithsha: Let's meet"], "Lithsha: Let's meet") is True
    assert whatsapp_service._is_group_notification("Batch 2024 (15 messages)", ["Batch 2024 (15 messages)", "Update"], "Update") is True
    assert whatsapp_service._is_group_notification("Amma No: 1", ["Amma No: 1", "What are u doing"], "What are u doing") is False
    assert whatsapp_service._is_group_notification("Lithsha", ["Lithsha", "Hii"], "Hii") is False

    # 14. Unknown number rejection test
    assert whatsapp_service._is_unknown_number("+91 98765 43210") is True
    assert whatsapp_service._is_unknown_number("+1 (555) 123-4567") is True
    assert whatsapp_service._is_unknown_number("9876543210") is True
    assert whatsapp_service._is_unknown_number("Unknown") is True
    assert whatsapp_service._is_unknown_number("Amma No: 1") is False
    assert whatsapp_service._is_unknown_number("Lithsha") is False
    assert whatsapp_service._is_unknown_number("Harini") is False

    # 15. Language detection tests
    assert whatsapp_service.detect_language("வணக்கம் Friday, ஹரிஷன் எங்கே?") == "tamil"
    assert whatsapp_service.detect_language("Hey Friday enna panra?") == "tanglish"
    assert whatsapp_service.detect_language("Harishan eppo varuvaaru seekiram sollu") == "tanglish"
    assert whatsapp_service.detect_language("Hey Friday, tell me more about you") == "english"

    # 16. Urgency detection tests
    assert whatsapp_service.check_is_urgent("Hey Friday, tell me more about you") is False
    assert whatsapp_service.check_is_urgent("Harishan call me immediately hospital emergency!") is True
    assert whatsapp_service.check_is_urgent("romba urgent seekiram call pannu") is True
    assert whatsapp_service.check_is_urgent("அவசரம் உடனடியாக பேசவும்") is True

    # 17. Conversational reply tests
    whatsapp_service.settings["custom_auto_reply_message"] = None

    reply_about_friday = whatsapp_service.generate_auto_reply("Lithsha", "Hey Friday, tell me more about you")
    assert "friday" in reply_about_friday.lower()
    assert len(reply_about_friday) > 20

    reply_tanglish = whatsapp_service.generate_auto_reply("Dinesh", "Enna panra Friday?")
    assert "friday" in reply_tanglish.lower()
    assert len(reply_tanglish) > 15

    reply_urgent = whatsapp_service.generate_auto_reply("Appa", "Call me ASAP, it is an emergency!")
    assert "urgent" in reply_urgent.lower() or "alert" in reply_urgent.lower() or "emergency" in reply_urgent.lower() or "friday" in reply_urgent.lower()

    # Reset
    whatsapp_service.set_monitoring(enabled=False, custom_auto_reply_message="")

