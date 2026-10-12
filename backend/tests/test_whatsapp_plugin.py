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
    assert "whatsapp" in history_ans.lower() or "no new whatsapp messages" in history_ans.lower() or "has sent" in history_ans.lower() or "new whatsapp" in history_ans.lower()
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
    assert whatsapp_service._is_group_notification("Project Team", ["Project Team", "Member 1", "Hi all"], "Member 1 - Hi all") is True
    assert whatsapp_service._is_group_notification("Developers Group", ["Developers Group", "Sender: Let's meet"], "Sender: Let's meet") is True
    assert whatsapp_service._is_group_notification("Batch 2024 (15 messages)", ["Batch 2024 (15 messages)", "Update"], "Update") is True
    assert whatsapp_service._is_group_notification("Contact Option 1", ["Contact Option 1", "What are u doing"], "What are u doing") is False
    assert whatsapp_service._is_group_notification("Test User Alpha", ["Test User Alpha", "Hii"], "Hii") is False

    # 14. Unknown number rejection test
    assert whatsapp_service._is_unknown_number("+91 98765 43210") is True
    assert whatsapp_service._is_unknown_number("+1 (555) 123-4567") is True
    assert whatsapp_service._is_unknown_number("9876543210") is True
    assert whatsapp_service._is_unknown_number("Unknown") is True
    assert whatsapp_service._is_unknown_number("Contact Option 1") is False
    assert whatsapp_service._is_unknown_number("Test User Alpha") is False
    assert whatsapp_service._is_unknown_number("Test User Beta") is False

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

    reply_about_friday = whatsapp_service.generate_auto_reply("Test User Alpha", "Hey Friday, tell me more about you")
    assert "friday" in reply_about_friday.lower()
    assert len(reply_about_friday) > 20

    reply_tanglish = whatsapp_service.generate_auto_reply("Test Friend", "Enna panra Friday?")
    assert "friday" in reply_tanglish.lower()
    assert len(reply_tanglish) > 15

    reply_urgent = whatsapp_service.generate_auto_reply("Parent Contact", "Call me ASAP, it is an emergency!")
    assert "urgent" in reply_urgent.lower() or "alert" in reply_urgent.lower() or "emergency" in reply_urgent.lower() or "friday" in reply_urgent.lower()

    # 18. Media and Attachment handling tests (No vision prompt hallucinations)
    assert whatsapp_service.is_media_message("📷 Photo")[0] is True
    assert whatsapp_service.is_media_message("Document")[0] is True
    assert whatsapp_service.is_media_message("resume.pdf")[0] is True
    assert whatsapp_service.is_media_message("Voice message")[0] is True

    reply_photo = whatsapp_service.generate_auto_reply("Test User Alpha", "📷 Photo")
    assert "friday" in reply_photo.lower()
    # Confirm Friday NEVER asks for a vision prompt or prompt engineering
    assert "prompt" not in reply_photo.lower()
    assert "describe" not in reply_photo.lower()

    # 19. Multi-message context handling tests
    whatsapp_service.record_sender_message("Colleague", "Additional functionality: read the docs and images in this chat\nCreate a plan and respond me now", role="contact")
    whatsapp_service.record_sender_message("Colleague", "Thanks", role="contact")
    colleague_context = whatsapp_service.get_sender_context("Colleague")
    assert "Additional functionality" in colleague_context

    reply_multimsg = whatsapp_service.generate_auto_reply("Colleague", "Thanks", context=colleague_context)
    assert "friday" in reply_multimsg.lower()
    assert len(reply_multimsg) > 15

    # 20. Urgent alert tracking and dismissal tests
    whatsapp_service.latest_urgent_alert = {
        "id": 999,
        "sender": "Test User Alpha",
        "message": "Hospital emergency call ASAP!",
        "timestamp": "10:20:00"
    }
    assert whatsapp_service.get_urgent_alert() is not None
    assert whatsapp_service.get_urgent_alert()["sender"] == "Test User Alpha"

    dismiss_res = whatsapp_service.dismiss_urgent_alert()
    assert dismiss_res["status"] == "success"
    assert whatsapp_service.get_urgent_alert() is None

    # 21. Monitoring only vs Auto-Reply separation test
    mon_only_ans = await execute_in_backend("monitor my WhatsApp", session_id="test_wa")
    assert "active" in mon_only_ans.lower()
    assert whatsapp_service.settings["enabled"] is True
    assert whatsapp_service.settings["auto_reply"] is False

    ar_enable_ans = await execute_in_backend("enable auto reply on WhatsApp", session_id="test_wa")
    assert "active" in ar_enable_ans.lower()
    assert whatsapp_service.settings["enabled"] is True
    assert whatsapp_service.settings["auto_reply"] is True

    # 22. Spoken Notification Subscription test
    sample_contact = "Samantha Cole"
    notify_ans = await execute_in_backend(f"notify me when I receive message from {sample_contact}", session_id="test_wa")
    assert sample_contact.lower() in notify_ans.lower()
    assert whatsapp_service.settings["notify_mode"] == "specific"
    assert sample_contact.lower() in whatsapp_service.settings["notify_target_contact"].lower()

    # 23. Contextual Follow-Up Reply test
    whatsapp_service.latest_received_message = {
        "id": 888,
        "sender": sample_contact,
        "message": "Are we meeting today?",
        "timestamp": 123456789
    }
    follow_up_ans = await execute_in_backend("make auto reply to him saying yes at 5pm", session_id="test_wa")
    assert sample_contact.lower() in follow_up_ans.lower()
    assert "5pm" in follow_up_ans.lower()

    # 24. Contact Disambiguation test (Completely Dynamic - Zero Hardcoding)
    # Add two similar contacts to pool dynamically
    stem_name = "DevContact"
    cand_1 = f"{stem_name} No: 1"
    cand_2 = f"{stem_name} No: 2"
    whatsapp_service._sender_history[cand_1] = []
    whatsapp_service._sender_history[cand_2] = []
    disam_ans = await execute_in_backend(f"send message to {stem_name} saying reached safely", session_id="test_disam")
    assert cand_1.lower() in disam_ans.lower()
    assert cand_2.lower() in disam_ans.lower()

    # User responds with "first one"
    pick_ans = await execute_in_backend("first one", session_id="test_disam")
    assert cand_1.lower() in pick_ans.lower()
    assert "reached safely" in pick_ans.lower()

    # 25. Qualifier match test (Dynamic base -> qualified match, e.g. "Engineer Dave" -> "Engineer Dave (Robotics Lab)")
    base_name = "Engineer Dave"
    qual_contact = f"{base_name} (Robotics Lab)"
    whatsapp_service._sender_history[qual_contact] = []
    qual_ans = await execute_in_backend(f"call {base_name}", session_id="test_qual")
    assert qual_contact.lower() in qual_ans.lower()

    # User confirms with "yes"
    qual_confirm = await execute_in_backend("yes", session_id="test_qual")
    assert qual_contact.lower() in qual_confirm.lower()

    # 26. In-Call Speech Synthesis test
    speak_ans = await execute_in_backend("speak to him saying Harishan will call back in 10 minutes", session_id="test_wa")
    assert "spoken" in speak_ans.lower()
    assert "10 minutes" in speak_ans.lower()

    # 27. Smart Mail Drafting with Confirmation Guard
    mail_ans = await execute_in_backend("send an email to team@company.com regarding weekly status report", session_id="test_mail")
    assert "subject" in mail_ans.lower()
    assert "team@company.com" in mail_ans.lower()
    assert "confirm" in mail_ans.lower() or "check" in mail_ans.lower()

    # User confirms mail
    mail_confirm = await execute_in_backend("send it", session_id="test_mail")
    assert "dispatched" in mail_confirm.lower() or "email" in mail_confirm.lower()

    # 28. Send selected file to contact (No prompt asking for path)
    from unittest.mock import patch
    with patch("app.services.command_executor.get_selected_desktop_or_explorer_file", return_value="C:/test/sample_doc.pdf"):
        with patch.object(whatsapp_service, "send_file", return_value={"success": True}) as mock_send_file:
            test_recipient = "Developer Beta"
            file_ans = await execute_in_backend(f"send the selected file to {test_recipient}", session_id="test_file")
            assert "sample_doc.pdf" in file_ans.lower()
            assert test_recipient.lower() in file_ans.lower()
            mock_send_file.assert_called_once()

    # 29. Send selected file to contact with "in whatsapp" suffix
    with patch("app.services.command_executor.get_selected_desktop_or_explorer_file", return_value="C:/test/sample_doc.pdf"):
        with patch.object(whatsapp_service, "send_file", return_value={"success": True}) as mock_send_file:
            test_recipient_wa = "Developer Gamma"
            file_wa_ans = await execute_in_backend(f"send the selected file to {test_recipient_wa} in whatsapp", session_id="test_file_wa")
            assert "sample_doc.pdf" in file_wa_ans.lower()
            assert test_recipient_wa.lower() in file_wa_ans.lower()
            mock_send_file.assert_called_once()

    # 30. Power and System Controls (Testing environment dry-run)
    lock_ans = await execute_in_backend("lock the computer", session_id="test_pwr")
    assert "locked" in lock_ans.lower()

    sleep_ans = await execute_in_backend("put pc to sleep", session_id="test_pwr")
    assert "sleep" in sleep_ans.lower()

    reboot_ans = await execute_in_backend("restart system", session_id="test_pwr")
    assert "reboot" in reboot_ans.lower() or "restarting" in reboot_ans.lower()

    shutdown_ans = await execute_in_backend("shutdown system", session_id="test_pwr")
    assert "shutdown" in shutdown_ans.lower()

    cancel_ans = await execute_in_backend("cancel shutdown", session_id="test_pwr")
    assert "aborted" in cancel_ans.lower()

    # Reset
    whatsapp_service.set_monitoring(enabled=False, custom_auto_reply_message="", notify_mode="all", notify_target_contact=None)


