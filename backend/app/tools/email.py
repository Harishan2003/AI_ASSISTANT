"""
Email Automation & Smart Composition Tools for Friday AI Assistant.
Generates subject and content dynamically based on user requirements, populates mail drafts,
and confirms with the user before dispatch.
"""

from __future__ import annotations

import urllib.parse
import webbrowser
import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


def generate_email_draft(requirement: str, recipient: str = "", context: Optional[str] = None) -> Dict[str, str]:
    """
    Uses LLM to dynamically generate a professional subject and body based on user requirements.
    No hardcoding!
    """
    agent_name = "Friday"
    user_name = "Harishan"
    try:
        from app.services.command_executor import load_user_profile
        prof = load_user_profile()
        agent_name = prof.get("agent_profile", {}).get("agent_name") or prof.get("agent_name") or "Friday"
        user_name = prof.get("profile", {}).get("name") or prof.get("name") or "Harishan"
    except Exception:
        pass

    system_prompt = (
        f"You are {agent_name}, {user_name}'s intelligent executive assistant.\n"
        "Draft a professional, clear, and context-appropriate email based on the user's instructions.\n"
        "Return ONLY a valid JSON object with keys 'subject' and 'body'. Do not output markdown codeblocks.\n"
        "The subject must be concise and descriptive.\n"
        f"The body must include a polite greeting, clearly structured paragraphs, and professional sign-off with {user_name}'s name."
    )

    user_prompt = f"Recipient: {recipient}\nRequirement: {requirement}"
    if context:
        user_prompt += f"\nContext/Attachments: {context}"

    try:
        res = llm_service.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_tokens=400
        )
        content = res.get("content", "").strip()
        # Parse JSON if possible
        import json
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            return {
                "subject": data.get("subject", "Important Update from Harishan"),
                "body": data.get("body", content)
            }
    except Exception as e:
        logger.warning(f"Failed to generate email draft via LLM: {e}")

    # Clean fallback
    clean_req = requirement.strip()
    return {
        "subject": f"Regarding: {clean_req[:50]}",
        "body": f"Hello {recipient or 'there'},\n\nI am writing regarding {clean_req}.\n\nBest regards,\nHarishan"
    }


def open_mail_client(recipient: str, subject: str, body: str, file_attachment: Optional[str] = None) -> bool:
    """
    Opens Gmail Web or default email client with pre-filled recipient, subject, and body.
    If a file attachment is provided, it stages the file to the Windows clipboard for instant attachment.
    """
    try:
        import os
        import subprocess
        import threading
        import time

        # If attachment is provided, stage to clipboard and launch background auto-attacher
        if file_attachment and os.path.exists(file_attachment):
            abs_path = os.path.abspath(file_attachment)
            try:
                ps_script = f"""
                Add-Type -AssemblyName System.Windows.Forms
                $col = New-Object System.Collections.Specialized.StringCollection
                $col.Add('{abs_path}')
                [System.Windows.Forms.Clipboard]::SetFileDropList($col)
                """
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True, creationflags=0x08000000)
                logger.info(f"Staged attachment '{abs_path}' to Windows clipboard.")
            except Exception as e:
                try:
                    subprocess.run(["powershell", "-NoProfile", "-Command", f'Set-Clipboard -Path "{abs_path}"'], check=True, creationflags=0x08000000)
                except Exception:
                    logger.warning(f"Failed to stage attachment to clipboard: {e}")

            # 1. Background Auto-Paste Thread (waits for Gmail compose to open and sends Ctrl+V)
            def _auto_paste_attachment():
                try:
                    import pyautogui
                    time.sleep(2.5)  # Wait for browser and Gmail compose UI to initialize
                    # Attempt to paste the staged attachment file directly into compose box
                    pyautogui.hotkey("ctrl", "v")
                    logger.info(f"Auto-pasted attachment '{abs_path}' into active compose window.")
                except Exception as ex:
                    logger.warning(f"Auto-paste worker failed: {ex}")

            threading.Thread(target=_auto_paste_attachment, daemon=True).start()

            # 2. Background Open File Dialog Watcher (fills Windows file picker automatically)
            def _dialog_watcher():
                try:
                    import win32gui
                    import win32con
                    import pyautogui
                    import pyperclip
                    start_t = time.time()
                    while time.time() - start_t < 30.0:
                        def _enum(h, extra):
                            if win32gui.IsWindowVisible(h):
                                if win32gui.GetClassName(h) == "#32770":
                                    t = win32gui.GetWindowText(h).lower()
                                    if any(w in t for w in ["open", "choose", "select", "upload", "file"]):
                                        extra.append(h)
                        dlgs = []
                        win32gui.EnumWindows(_enum, dlgs)
                        if dlgs:
                            d_hwnd = dlgs[0]
                            win32gui.ShowWindow(d_hwnd, win32con.SW_RESTORE)
                            win32gui.SetForegroundWindow(d_hwnd)
                            time.sleep(0.3)
                            pyperclip.copy(abs_path)
                            pyautogui.hotkey('ctrl', 'a')
                            pyautogui.press('backspace')
                            pyautogui.hotkey('ctrl', 'v')
                            time.sleep(0.2)
                            pyautogui.press('enter')
                            logger.info(f"Auto-attached '{abs_path}' into file dialog.")
                            break
                        time.sleep(0.5)
                except Exception:
                    pass

            threading.Thread(target=_dialog_watcher, daemon=True).start()

        query_params = {}
        if subject:
            query_params["su"] = subject
            query_params["subject"] = subject
        if body:
            query_params["body"] = body

        clean_recipient = recipient.strip()
        if clean_recipient.lower() in ["[recipient]", "recipient", "someone", ""]:
            clean_recipient = ""

        # Open Gmail compose web URL if browser is preferred, or mailto
        if clean_recipient or subject or body:
            gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(clean_recipient)}&su={urllib.parse.quote(subject or '')}&body={urllib.parse.quote(body or '')}"
            try:
                webbrowser.open(gmail_url)
                return True
            except Exception:
                pass

        # Fallback to mailto
        mail_query = urllib.parse.urlencode({"subject": subject or "", "body": body or ""}, quote_via=urllib.parse.quote)
        mailto_url = f"mailto:{clean_recipient}?{mail_query}"
        webbrowser.open(mailto_url)
        return True
    except Exception as e:
        logger.error(f"Failed to open mail client: {e}")
        return False


def send_current_email(user_message: str = "") -> str:
    """Triggers the Send action in Gmail or active email client (Ctrl + Enter)."""
    try:
        import pyautogui
        pyautogui.hotkey("ctrl", "enter")
        return "Sent the email (Ctrl + Enter)!"
    except Exception as e:
        return f"Failed to send email: {e}"


class DraftEmailInput(BaseModel):
    recipient: str = Field(..., description="Email address or name of recipient.")
    requirement: str = Field(..., description="What the email is about or the user's goal for the mail.")
    attachment_path: Optional[str] = Field(None, description="Optional path to an attached file or image.")


class DraftEmailTool(BaseTool):
    name: str = "draft_email"
    description: str = "Generates email subject and body dynamically for user review and opens the mail client."
    permission_level: PermissionLevel = PermissionLevel.CONFIRM
    category: str = "communication"
    args_schema = DraftEmailInput

    def run(self, recipient: str, requirement: str, attachment_path: Optional[str] = None, **kwargs: Any) -> ToolResult:
        draft = generate_email_draft(requirement, recipient=recipient, context=attachment_path)
        subject = draft.get("subject", "")
        body = draft.get("body", "")

        opened = open_mail_client(recipient, subject, body, file_attachment=attachment_path)

        return ToolResult(
            tool_name=self.name,
            success=True,
            data={
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "attachment": attachment_path,
                "opened_client": opened
            },
            metadata={
                "summary": f"Drafted email to {recipient} with Subject: '{subject}'"
            }
        )
