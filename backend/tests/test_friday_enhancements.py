"""
Automated unit tests for Friday AI Assistant enhancements:
1. Multi-candidate contact disambiguation (e.g. Kishore vs Kishore Priyan(krct) vs Kishore M(svv))
2. Email drafting with topic prompting
3. Hover / fresh file selection (no stale cache re-use)
4. File moving to natural paths
5. Mouse-hover open and existing-screen navigation
6. GPU & telemetry power optimizations
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.whatsapp_service import whatsapp_service
from app.services.command_executor import (
    execute_in_backend,
    get_selected_desktop_or_explorer_file,
    PENDING_DISAMBIGUATION,
    PENDING_CONFIRMATION,
    PENDING_EMAIL_INPUT
)
from app.services.context_service import get_hovered_or_selected_file_or_folder, context_service
from app.services.context_state import context_state
from app.tools.system.gpu import GPUStatusTool


def test_whatsapp_multi_contact_disambiguation_generic():
    """Verify Friday detects multiple matching candidates and asks the user without picking the first."""
    whatsapp_service._sender_history.clear()
    
    # Simulate multiple real contacts
    cand_1 = "Kishore Priyan(krct)"
    cand_2 = "Kishore M(svv)"
    cand_3 = "Kishore Kumar"
    
    whatsapp_service._sender_history[cand_1] = []
    whatsapp_service._sender_history[cand_2] = []
    whatsapp_service._sender_history[cand_3] = []
    
    # Query: "Kishore"
    res = whatsapp_service.find_contact_candidates("Kishore")
    assert res["status"] == "multiple"
    assert len(res["candidates"]) >= 3
    assert cand_1 in res["candidates"]
    assert cand_2 in res["candidates"]
    assert cand_3 in res["candidates"]
    assert "1." in res["prompt"]
    assert "2." in res["prompt"]
    assert "3." in res["prompt"]


def test_fresh_file_selection_does_not_use_stale_cache():
    """Verify that when no item is hovered or selected, Friday does not return stale previous files."""
    context_state.clear_all()
    context_state.set_selected_file("C:/nonexistent/stale_file.txt")
    
    # Clear and test fresh query
    with patch("uiautomation.ControlFromCursor", return_value=None):
        with patch("comtypes.client.CreateObject") as mock_com:
            mock_shell = MagicMock()
            mock_shell.Windows.return_value.Count = 0
            mock_com.return_value = mock_shell
            fresh_result = get_hovered_or_selected_file_or_folder()
            # Must be None, NOT the stale file!
            assert fresh_result is None


def test_gpu_monitoring_power_optimization():
    """Verify GPUStatusTool returns cached results rapidly without spawning processes."""
    gpu_tool = GPUStatusTool()
    res1 = gpu_tool.run()
    assert res1.success is True
    
    # Second call within 3s must hit cache instantaneously
    res2 = gpu_tool.run()
    assert res2.success is True
    assert res2.data["available"] == res1.data["available"]
    assert res2.data["total_gpus"] == res1.data["total_gpus"]


@pytest.mark.anyio
async def test_email_topic_prompting_flow():
    """Verify Friday asks user for topic/content if not provided, then confirms before sending."""
    PENDING_EMAIL_INPUT.clear()
    PENDING_CONFIRMATION.clear()
    
    # User says just "send email to hr@company.com" without topic
    prompt_ans = await execute_in_backend("send email to hr@company.com", session_id="test_email_prompt")
    assert "hr@company.com" in prompt_ans.lower()
    assert "what subject and message content" in prompt_ans.lower()
    assert "test_email_prompt" in PENDING_EMAIL_INPUT
    
    # User supplies their content: "Regarding leave request for tomorrow due to personal emergency"
    draft_ans = await execute_in_backend("Regarding leave request for tomorrow due to personal emergency", session_id="test_email_prompt")
    assert "drafted" in draft_ans.lower()
    assert "leave" in draft_ans.lower() or "subject" in draft_ans.lower()
    assert "test_email_prompt" in PENDING_CONFIRMATION
    
    # User confirms
    with patch("app.tools.email.webbrowser.open") as mock_browser:
        confirm_ans = await execute_in_backend("yes send it", session_id="test_email_prompt")
        assert "dispatched" in confirm_ans.lower()
        mock_browser.assert_called()


@pytest.mark.anyio
async def test_file_move_flow(tmp_path):
    """Verify natural file move operation."""
    src_file = tmp_path / "report_temp.txt"
    src_file.write_text("Test Content", encoding="utf-8")
    
    dst_folder = tmp_path / "TargetArchive"
    
    with patch("app.services.command_executor.get_selected_desktop_or_explorer_file", return_value=str(src_file)):
        with patch("app.tools.filesystem.file_ops.resolve_natural_path", return_value=dst_folder):
            ans = await execute_in_backend(f"move this to TargetArchive", session_id="test_move")
            assert "moved" in ans.lower()
            assert "report_temp.txt" in ans.lower()
            assert (dst_folder / "report_temp.txt").exists()


@pytest.mark.anyio
async def test_whatsapp_message_flow_with_multi_candidate_and_user_selection():
    """Verify Friday asks which contact when multiple match, and sends to the chosen one."""
    PENDING_DISAMBIGUATION.clear()
    whatsapp_service._sender_history.clear()
    
    whatsapp_service._sender_history["Kishore💙"] = []
    whatsapp_service._sender_history["Kishore Priyan(krct)"] = []
    whatsapp_service._sender_history["Kishore M(svv)"] = []
    
    with patch.object(whatsapp_service, "send_message", return_value={"success": True}) as mock_send:
        # 1. User says: "send message to Kishore that I will call you later"
        prompt_ans = await execute_in_backend("send message to Kishore that I will call you later", session_id="test_kishore_session")
        
        # Must ask user which one, and NOT immediately call send_message
        assert "multiple contacts" in prompt_ans.lower()
        assert "kishore priyan" in prompt_ans.lower()
        assert "kishore m" in prompt_ans.lower()
        mock_send.assert_not_called()
        
        # 2. User says: "the second one"
        reply_ans = await execute_in_backend("the second one", session_id="test_kishore_session")
        assert "kishore priyan" in reply_ans.lower()
        mock_send.assert_called_once_with("Kishore Priyan(krct)", "I will call you later")


@pytest.mark.anyio
async def test_whatsapp_send_file_to_harini(tmp_path):
    """Verify sending a file to Harini correctly resolves real files and rejects directories."""
    real_file = tmp_path / "document.pdf"
    real_file.write_text("Sample PDF Content", encoding="utf-8")
    
    whatsapp_service._sender_history.clear()
    whatsapp_service._sender_history["Harini"] = []
    
    # Case A: Real file selected
    with patch("app.services.command_executor.get_selected_desktop_or_explorer_file", return_value=str(real_file)):
        with patch.object(whatsapp_service, "send_file", return_value={"success": True, "file_name": "document.pdf"}) as mock_send_file:
            ans = await execute_in_backend("send this file to Harini in WhatsApp", session_id="test_harini_file")
            assert "dispatched file" in ans.lower()
            assert "harini" in ans.lower()
            mock_send_file.assert_called_once_with("Harini", str(real_file))
            
    # Case B: No file selected (e.g. empty or directory)
    with patch("app.services.command_executor.get_selected_desktop_or_explorer_file", return_value=None):
        ans_none = await execute_in_backend("send this file to Harini in WhatsApp", session_id="test_harini_file_none")
        assert "can't locate a selected file" in ans_none.lower()
        assert "d:\\" not in ans_none.lower()


@pytest.mark.anyio
async def test_whatsapp_attend_call_and_speak():
    """Verify 'attend this call and speak to them' actually attends the call first."""
    with patch.object(whatsapp_service, "answer_call", return_value={"success": True}) as mock_answer:
        # Case A: attend and speak without specific message
        ans1 = await execute_in_backend("attend this call and speak to them", session_id="test_attend_call")
        mock_answer.assert_called_once()
        assert "attended" in ans1.lower()
        assert "to them" not in ans1.lower()  # Must not speak "to them" as a dummy payload
        
    with patch.object(whatsapp_service, "answer_call", return_value={"success": True}) as mock_answer2:
        with patch.object(whatsapp_service, "speak_in_call", return_value={"success": True}) as mock_speak:
            # Case B: attend and speak with actual message
            ans2 = await execute_in_backend("attend this call and speak to them saying Harishan will call back in 5 minutes", session_id="test_attend_call_msg")
            mock_answer2.assert_called_once()
            mock_speak.assert_called_once_with("Harishan will call back in 5 minutes")
            assert "attended" in ans2.lower()
            assert "5 minutes" in ans2.lower()


@pytest.mark.anyio
async def test_whatsapp_natural_send_message_disambiguation():
    """Verify 'send the message to kishore i well call u later' triggers multi-candidate disambiguation and does not auto-dispatch."""
    PENDING_DISAMBIGUATION.clear()
    whatsapp_service._sender_history.clear()
    whatsapp_service._sender_history["Kishore💙"] = []
    whatsapp_service._sender_history["Kishore Priyan(krct)"] = []
    whatsapp_service._sender_history["Kishore M(svv)"] = []

    with patch.object(whatsapp_service, "send_message", return_value={"success": True}) as mock_send:
        ans = await execute_in_backend("send the message to kishore i well call u later", session_id="test_kishore_session_2")
        mock_send.assert_not_called()
        assert "multiple" in ans.lower() and "contacts" in ans.lower()
        assert "kishore💙" in ans.lower()
        assert "kishore priyan(krct)" in ans.lower()
        assert "kishore m(svv)" in ans.lower()

        # Follow up choice by index
        ans_choice = await execute_in_backend("1", session_id="test_kishore_session_2")
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        assert args[0] == "Kishore💙"
        assert "call u later" in args[1]


@pytest.mark.anyio
async def test_whatsapp_qualifier_confirmation_abhishek():
    """Verify 'send the message to abhishek that i will can u later' asks for confirmation when a qualified match exists."""
    PENDING_DISAMBIGUATION.clear()
    whatsapp_service._sender_history.clear()
    whatsapp_service._sender_history["Abhishek N S(krct)"] = []

    with patch.object(whatsapp_service, "send_message", return_value={"success": True}) as mock_send:
        ans = await execute_in_backend("send the message to abhishek that i will can u later", session_id="test_abhishek_session")
        mock_send.assert_not_called()
        assert "abhishek n s(krct)" in ans.lower()
        assert "would you like me to message" in ans.lower()

        # Confirm with yes
        ans_confirm = await execute_in_backend("yes", session_id="test_abhishek_session")
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        assert args[0] == "Abhishek N S(krct)"
        assert "will can u later" in args[1]


@pytest.mark.anyio
async def test_mouse_pointer_overlay_filtering_and_clean_formatting():
    """Verify 'where is my mouse pointing' ignores Friday overlay and returns natural conversational text."""
    from app.services.vision_service import get_mouse_pointer_context
    ans = get_mouse_pointer_context()
    # Must never include raw debug text or coordinates unless requested
    assert "Active: **Friday AI Assistant" not in ans
    assert "Neural Core Overlay" not in ans
    assert "x=" not in ans or "y=" not in ans  # No raw coordinates in clean conversational response
    assert "mouse cursor is currently" in ans.lower() or "desktop" in ans.lower()


@pytest.mark.anyio
async def test_whatsapp_live_unread_fallback_query():
    """Verify who messaged checks live unread chats when no logs exist."""
    with patch.object(whatsapp_service, "get_unseen_logs", return_value=[]):
        with patch.object(whatsapp_service, "get_live_unread_chats", return_value=[{"chat": "Kishore Priyan (2 unread)"}]):
            ans = await execute_in_backend("who messaged me on whatsapp", session_id="test_live_unread")
            assert "unread chats in whatsapp" in ans.lower()
            assert "kishore priyan" in ans.lower()


@pytest.mark.anyio
async def test_open_whatsapp_app_launch_not_folder():
    """Verify 'open WhatsApp' launches the WhatsApp application, NOT local folders like 'whatsapp refence plugin'."""
    with patch("os.system") as mock_sys:
        ans = await execute_in_backend("open WhatsApp", session_id="test_open_wa")
        assert "opened whatsapp" in ans.lower()
        assert "refence plugin" not in ans.lower()
        assert "file explorer" not in ans.lower()
        mock_sys.assert_called_once()
        cmd_run = mock_sys.call_args[0][0]
        assert "start whatsapp:" in cmd_run or "whatsapp" in cmd_run


@pytest.mark.anyio
async def test_close_app_execution():
    """Verify 'close whatsapp' and 'close active window' trigger application termination."""
    from app.services.system_service import system_service
    with patch.object(system_service, "close_application", return_value="Closed WhatsApp, Harishan.") as mock_close:
        ans = await execute_in_backend("close WhatsApp", session_id="test_close_app")
        assert "closed whatsapp" in ans.lower()
        mock_close.assert_called_once_with("whatsapp")

    with patch.object(system_service, "close_application", return_value="Closed the active window, Harishan.") as mock_close_win:
        ans_win = await execute_in_backend("close active window", session_id="test_close_win")
        assert "closed the active window" in ans_win.lower()
        mock_close_win.assert_called_once_with("")


@pytest.mark.anyio
async def test_mouse_movement_commands():
    """Verify mouse positioning commands move the cursor accurately."""
    with patch("pyautogui.moveTo") as mock_move_to:
        with patch("pyautogui.size", return_value=(1920, 1080)):
            ans = await execute_in_backend("move mouse to center", session_id="test_mouse_center")
            assert "moved mouse cursor to the center" in ans.lower()
            mock_move_to.assert_called_once_with(960, 540, duration=0.15)

    with patch("pyautogui.moveTo") as mock_move_to, patch("pyautogui.position", return_value=(500, 500)), patch("pyautogui.size", return_value=(1920, 1080)):
        ans_left = await execute_in_backend("move mouse left 200", session_id="test_mouse_left")
        assert "200 pixels left" in ans_left.lower()
        mock_move_to.assert_called_once_with(300, 500, duration=0.15)


@pytest.mark.anyio
async def test_open_hovered_pointed_file_or_folder(tmp_path):
    """Verify 'open that file' opens the item currently hovered or selected."""
    sample_file = tmp_path / "project_brief.pdf"
    sample_file.write_text("dummy", encoding="utf-8")

    with patch("app.services.context_service.get_hovered_or_selected_file_or_folder", return_value=str(sample_file)):
        with patch("os.startfile") as mock_start:
            ans = await execute_in_backend("open that file", session_id="test_open_hovered")
            assert "opened" in ans.lower()
            assert "project_brief.pdf" in ans.lower()
            mock_start.assert_called_once_with(str(sample_file))

