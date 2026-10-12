"""
Friday Context Service
Detects foreground Windows applications and executes in-context commands
(WhatsApp, Gmail, Active Browser tabs, File Explorer, Notepad, VS Code).
"""

from __future__ import annotations

import ctypes
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

from app.services.context_state import context_state


# Windows API Structures
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def get_active_window_info() -> Dict[str, Any]:
    """Retrieves foreground window title, class name, process name, and HWND."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return {"hwnd": 0, "title": "", "class": "", "process": ""}

    length = user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    title = buff.value

    class_buff = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, class_buff, 256)
    class_name = class_buff.value

    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    process_name = ""
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    h_process = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid.value)
    if h_process:
        exe_buff = ctypes.create_unicode_buffer(512)
        size = ctypes.c_ulong(512)
        try:
            if kernel32.QueryFullProcessImageNameW(h_process, 0, exe_buff, ctypes.byref(size)):
                process_name = Path(exe_buff.value).name.lower()
        except Exception:
            pass
        kernel32.CloseHandle(h_process)

    return {
        "hwnd": hwnd,
        "title": title,
        "class": class_name,
        "process": process_name,
    }


def force_focus_window(process_name_substr: str, title_substr: str = "") -> bool:
    """Finds and forces the target window into the foreground via Win32 APIs."""
    target_hwnd = None

    def enum_windows_callback(hwnd, extra):
        nonlocal target_hwnd
        if user32.IsWindowVisible(hwnd):
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            h_process = kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)
            pname = ""
            if h_process:
                exe_buff = ctypes.create_unicode_buffer(512)
                size = ctypes.c_ulong(512)
                if kernel32.QueryFullProcessImageNameW(h_process, 0, exe_buff, ctypes.byref(size)):
                    pname = Path(exe_buff.value).name.lower()
                kernel32.CloseHandle(h_process)

            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            wtitle = buff.value.lower()

            if process_name_substr.lower() in pname or (title_substr and title_substr.lower() in wtitle):
                target_hwnd = hwnd
                return False
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)

    if target_hwnd:
        user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
        current_thread_id = kernel32.GetCurrentThreadId()
        remote_thread_id = user32.GetWindowThreadProcessId(target_hwnd, None)
        user32.AttachThreadInput(current_thread_id, remote_thread_id, True)
        user32.SetForegroundWindow(target_hwnd)
        user32.BringWindowToTop(target_hwnd)
        user32.AttachThreadInput(current_thread_id, remote_thread_id, False)
        time.sleep(0.3)
        return True

    return False


def paste_text(text: str):
    """Safely pastes text using clipboard."""
    if pyperclip:
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.write(text, interval=0.01)


def set_file_to_clipboard(file_path: str) -> bool:
    """Sets a real file to the Windows Clipboard using PowerShell HDROP."""
    try:
        ps_script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        $file = [System.Collections.Specialized.StringCollection]::new()
        $file.Add('{file_path}')
        [System.Windows.Forms.Clipboard]::SetFileDropList($file)
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True, creationflags=0x08000000)
        return True
    except Exception as e:
        print(f"[ContextService] Clipboard error: {e}")
        return False


def get_hovered_or_selected_file_or_folder(must_be_file: bool = False) -> Optional[str]:
    """
    Dynamically locates the file or folder currently hovered by mouse cursor or selected in Explorer/Desktop.
    Freshly evaluated on every invocation to prevent stale file re-use.
    """
    # 1. Check mouse hover element via UIAutomation
    try:
        import uiautomation as auto
        ctrl = auto.ControlFromCursor()
        if ctrl:
            curr = ctrl
            for _ in range(5):
                if not curr:
                    break
                name = (curr.Name or "").strip()
                if name and os.path.exists(name):
                    if not must_be_file or os.path.isfile(name):
                        context_state.set_selected_file(name)
                        return name
                c_type = (curr.ControlTypeName or "").lower()
                if any(k in c_type for k in ["listitem", "treeitem", "text", "custom", "pane", "button"]):
                    # Check if the control is inside File Explorer or on the Desktop
                    is_explorer_or_desktop = False
                    top_class = ""
                    try:
                        top_ctrl = curr.GetTopLevelControl()
                        if top_ctrl:
                            top_hwnd = top_ctrl.NativeWindowHandle
                            class_buff = ctypes.create_unicode_buffer(256)
                            user32.GetClassNameW(top_hwnd, class_buff, 256)
                            top_class = class_buff.value
                            if top_class in ["CabinetWClass", "ExploreWClass", "Progman", "WorkerW"]:
                                is_explorer_or_desktop = True
                    except Exception:
                        pass

                    if is_explorer_or_desktop:
                        # 1. First check active File Explorer directory if in Explorer window
                        if top_class in ["CabinetWClass", "ExploreWClass"]:
                            active_explorer_dir = FileExplorerContextHandler.get_active_explorer_path()
                            if active_explorer_dir and os.path.exists(active_explorer_dir):
                                p_exp = Path(active_explorer_dir)
                                cand = p_exp / name
                                if cand.exists() and (not must_be_file or cand.is_file()):
                                    context_state.set_selected_file(str(cand.resolve()))
                                    return str(cand.resolve())
                                for match in p_exp.glob(f"{name}.*"):
                                    if match.is_file():
                                        context_state.set_selected_file(str(match.resolve()))
                                        return str(match.resolve())

                        # 2. Check Desktop if in Desktop window
                        if top_class in ["Progman", "WorkerW"]:
                            desktop_p = Path.home() / "Desktop"
                            cand = desktop_p / name
                            if cand.exists() and (not must_be_file or cand.is_file()):
                                context_state.set_selected_file(str(cand.resolve()))
                                return str(cand.resolve())
                            for match in desktop_p.glob(f"{name}.*"):
                                if match.is_file():
                                    context_state.set_selected_file(str(match.resolve()))
                                    return str(match.resolve())
                curr = curr.GetParentControl()
    except Exception:
        pass

    # 2. Check active File Explorer window selection
    try:
        import comtypes.client
        shell = comtypes.client.CreateObject("Shell.Application")
        windows = shell.Windows()
        hwnd_fg = user32.GetForegroundWindow()

        # Check foreground Explorer window first
        for i in range(windows.Count):
            try:
                w = windows.Item(i)
                if w and int(w.HWND) == int(hwnd_fg):
                    doc = getattr(w, "Document", None)
                    if doc and hasattr(doc, "SelectedItems"):
                        sel = doc.SelectedItems()
                        if sel and sel.Count > 0:
                            for item_idx in range(sel.Count):
                                p = sel.Item(item_idx).Path
                                if p and os.path.exists(p):
                                    if not must_be_file or os.path.isfile(p):
                                        context_state.set_selected_file(p)
                                        return str(p)
                    # Try FocusedItem if selection was empty
                    focused = getattr(doc, "FocusedItem", None)
                    if focused:
                        p = getattr(focused, "Path", None)
                        if p and os.path.exists(p):
                            if not must_be_file or os.path.isfile(p):
                                context_state.set_selected_file(p)
                                return str(p)
            except Exception:
                continue

        # Check any open Explorer window with selection
        for i in range(windows.Count):
            try:
                w = windows.Item(i)
                doc = getattr(w, "Document", None)
                if doc and hasattr(doc, "SelectedItems"):
                    sel = doc.SelectedItems()
                    if sel and sel.Count > 0:
                        for item_idx in range(sel.Count):
                            p = sel.Item(item_idx).Path
                            if p and os.path.exists(p):
                                if not must_be_file or os.path.isfile(p):
                                    context_state.set_selected_file(p)
                                    return str(p)
                focused = getattr(doc, "FocusedItem", None)
                if focused:
                    p = getattr(focused, "Path", None)
                    if p and os.path.exists(p):
                        if not must_be_file or os.path.isfile(p):
                            context_state.set_selected_file(p)
                            return str(p)
            except Exception:
                continue

        # 3. Check Windows Desktop surface selection
        try:
            desktop_view = shell.Windows().FindWindowSW(0, 0, 8, 0, 1)
            if desktop_view and hasattr(desktop_view, "Document"):
                sel = desktop_view.Document.SelectedItems()
                if sel and sel.Count > 0:
                    for item_idx in range(sel.Count):
                        p = sel.Item(item_idx).Path
                        if p and os.path.exists(p):
                            if not must_be_file or os.path.isfile(p):
                                context_state.set_selected_file(p)
                                return str(p)
                focused = getattr(desktop_view.Document, "FocusedItem", None)
                if focused:
                    p = getattr(focused, "Path", None)
                    if p and os.path.exists(p):
                        if not must_be_file or os.path.isfile(p):
                            context_state.set_selected_file(p)
                            return str(p)
        except Exception:
            pass
    except Exception as e:
        print(f"[ContextService] Selection query failed: {e}")

    return None


def get_current_explorer_selection(must_be_file: bool = False) -> Optional[str]:
    """Reads fresh file/folder selection from mouse cursor or active Explorer/Desktop window."""
    return get_hovered_or_selected_file_or_folder(must_be_file=must_be_file)


def prepare_file_or_folder_for_sharing(target_path: str) -> str:
    """If target is a folder, zips it so WhatsApp can transfer it natively."""
    path_obj = Path(target_path)
    if path_obj.is_file():
        return str(path_obj.resolve())

    if path_obj.is_dir():
        temp_dir = Path(tempfile.gettempdir()) / "Friday_Transfers"
        temp_dir.mkdir(parents=True, exist_ok=True)
        zip_path = temp_dir / f"{path_obj.name}.zip"

        shutil.make_archive(str(temp_dir / path_obj.name), "zip", str(path_obj))
        return str(zip_path.resolve())

    return str(path_obj)


def clean_query_text(text: str) -> str:
    """Strips voice filler phrases, app tags, and search preambles."""
    cleaned = text.lower().strip()

    app_noise = [
        r"\b(?:in|on)?\s*whats\s*app\b",
        r"\b(?:in|on)?\s*whatsapp\b",
        r"\b(?:in|on)?\s*gmail\b",
        r"\b(?:in|on)?\s*wa\b",
        r"\b(?:search|find|locate|look for)\s+(?:for\s+)?",
    ]
    for pat in app_noise:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

    noise = [
        r"\b(?:in\s+)?(?:activated|inactivated|active|current|existing|opening|open|the|depth|ta|window)\s+(?:tab|window|the\s+tab|the\s+open\s+the\s+tab)\b",
        r"\b(?:in\s+depth|in\s+ta|in\s+tab|in\s+existing\s+tab|in\s+current\s+tab)\b",
        r"\b(?:existing|current|active)\s+tab\b",
        r"\b(file|folder|document|item)\b$",
    ]
    for pat in noise:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

    return " ".join(cleaned.split()).strip()


# ============================================================
# 1. WHATSAPP CONTEXT HANDLER
# ============================================================

class WhatsAppContextHandler:
    """Handles commands inside active WhatsApp Desktop and WhatsApp Web."""

    @classmethod
    def matches(cls, info: Dict[str, Any]) -> bool:
        proc = info.get("process", "").lower()
        title = info.get("title", "").lower()
        return (
            "whatsapp" in proc
            or "whatsapp" in title
            or ("applicationframehost" in proc and "whatsapp" in title)
        )

    @classmethod
    def handle(cls, command: str, info: Dict[str, Any]) -> Optional[str]:
        if pyautogui is None:
            return None

        cmd_lower = command.lower().strip()

        # A. SEND EXPLICIT COMMAND
        if any(cmd_lower == s for s in ["send", "send it", "send that message", "send message", "send the message"]):
            pyautogui.press("enter")
            context_state.clear_draft()
            return "Sent."

        # B. COMPOUND ACTION: SEARCH CONTACT -> OPEN CHAT -> WRITE (DRAFT) OR SEND
        compound_match = re.search(
            r"^(?:whatsapp\s+(send|write)\s+to\s+|send\s+(?:a\s+)?message\s+to\s+|write\s+(?:a\s+)?message\s+to\s+)([a-zA-Z0-9_\s]+?)(?:\s*:\s*|\s+that\s+|\s+)(.+)$",
            command,
            flags=re.IGNORECASE,
        )
        if not compound_match:
            compound_match = re.search(
                r"(?:(?:open\s+whatsapp\s+(?:and\s+)?)?(?:search(?:\s+for)?|find)\s+([a-zA-Z0-9_\s]+?)\s+and\s+(send|write|type|text|draft)(?:\s+a\s+message|\s+message)?(?:\s*:\s*|\s+that\s+|\s+)(.+))$",
                command,
                flags=re.IGNORECASE,
            )

        if compound_match:
            if compound_match.re.pattern.startswith("^(?:whatsapp"):
                intent_action = compound_match.group(1).lower()
                raw_contact = compound_match.group(2).strip()
                msg_text = compound_match.group(3).strip()
            else:
                raw_contact = compound_match.group(1).strip()
                intent_action = compound_match.group(2).lower()
                msg_text = compound_match.group(3).strip()

            contact = clean_query_text(raw_contact)
            context_state.set_selected_contact(contact)
            context_state.set_draft(msg_text, draft_type="whatsapp")

            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.15)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            paste_text(contact)
            time.sleep(0.6)

            pyautogui.press("down")
            time.sleep(0.1)
            pyautogui.press("enter")
            time.sleep(0.5)

            paste_text(msg_text)
            time.sleep(0.2)

            if intent_action in ["write", "type", "draft"]:
                return f"Drafted message for {contact.capitalize()}: '{msg_text}'. Say 'send it' when you are ready."
            else:
                pyautogui.press("enter")
                context_state.clear_draft()
                return f"Sent message to {contact.capitalize()}: '{msg_text}'"

        # C. SEND SELECTED FILE / FOLDER
        if any(p in cmd_lower for p in ["send this file", "send the selected file", "send selected file", "send file", "send this folder", "send the selected folder"]):
            raw_path = get_current_explorer_selection()
            if not raw_path or not os.path.exists(raw_path):
                return "No file or folder is currently selected. Please select one in File Explorer first."

            final_file_path = prepare_file_or_folder_for_sharing(target_path=raw_path)
            set_file_to_clipboard(final_file_path)

            os.system("start whatsapp:")
            time.sleep(0.5)
            force_focus_window("whatsapp.exe", "whatsapp")
            time.sleep(0.5)

            recipient_match = re.search(r"to\s+([a-zA-Z0-9_]+)", cmd_lower)
            target_contact = recipient_match.group(1).strip() if recipient_match else context_state.selected_contact
            if target_contact and target_contact.lower() not in ["whatsapp", "chat"]:
                context_state.set_selected_contact(target_contact)
                pyautogui.hotkey("ctrl", "f")
                time.sleep(0.15)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.press("backspace")
                paste_text(target_contact)
                time.sleep(0.6)
                pyautogui.press("down")
                time.sleep(0.1)
                pyautogui.press("enter")
                time.sleep(0.8)

            pyautogui.hotkey("ctrl", "v")
            time.sleep(1.5)
            pyautogui.press("enter")
            time.sleep(0.5)
            return f"Sent {Path(final_file_path).name} to {context_state.selected_contact or 'contact'} on WhatsApp."

        # D. SEARCH CONTACT
        search_match = re.search(r"^(?:search(?:\s+for)?|find|locate)\s+(.+)$", cmd_lower)
        if search_match:
            raw_contact = search_match.group(1).strip()
            if " and " in raw_contact:
                raw_contact = raw_contact.split(" and ")[0].strip()
            contact = clean_query_text(raw_contact)
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            paste_text(contact)
            return f"Searching for {contact} in WhatsApp."

        # E. SELECT CONTACT
        select_match = re.search(r"^(?:select|open|choose)\s+(.+)$", cmd_lower)
        if select_match:
            raw_contact = select_match.group(1).strip()
            if " and " in raw_contact:
                raw_contact = raw_contact.split(" and ")[0].strip()
            contact = clean_query_text(raw_contact)
            context_state.set_selected_contact(contact)
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            paste_text(contact)
            time.sleep(0.4)
            pyautogui.press("down")
            time.sleep(0.05)
            pyautogui.press("enter")
            return f"Selected {contact} in WhatsApp."

        # F. WRITE MESSAGE
        write_match = re.search(r"^(?:write|type|message|draft|text)(?:\s+a\s+message|\s+message)?(?:\s+to\s+[a-zA-Z0-9_]+)?(?:\s*:\s*|\s+that\s+|\s+)(.+)$", command, flags=re.IGNORECASE)
        if write_match:
            msg_text = write_match.group(1).strip()
            context_state.set_draft(msg_text, draft_type="whatsapp")
            paste_text(msg_text)
            return f"Drafted: '{msg_text}'. Say 'send it' when you are ready."

        return None


# ============================================================
# 2. GMAIL CONTEXT HANDLER
# ============================================================

class GmailContextHandler:
    """Handles commands inside active Gmail browser tab."""

    @classmethod
    def matches(cls, info: Dict[str, Any]) -> bool:
        title = info.get("title", "").lower()
        proc = info.get("process", "").lower()
        return ("gmail" in title or "mail.google.com" in title) and proc in {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"}

    @classmethod
    def handle(cls, command: str, info: Dict[str, Any]) -> Optional[str]:
        if pyautogui is None:
            return None

        cmd_lower = command.lower().strip()

        if cmd_lower in ["send", "send it", "send email", "send the mail", "send the email", "send that email"]:
            pyautogui.hotkey("ctrl", "enter")
            context_state.clear_draft()
            return "Email sent."

        if any(p in cmd_lower for p in ["attach file", "attach this file", "attach selected file", "send this file", "attach folder"]):
            raw_path = get_current_explorer_selection()
            if not raw_path or not os.path.exists(raw_path):
                return "No file currently selected from File Explorer."

            final_file_path = prepare_file_or_folder_for_sharing(raw_path)
            set_file_to_clipboard(final_file_path)
            time.sleep(0.2)
            pyautogui.hotkey("ctrl", "v")
            return f"Attached {Path(final_file_path).name} to email."

        search_match = re.search(r"^(?:search(?:\s+for)?|find)\s+(.+)$", cmd_lower)
        if search_match:
            raw_query = search_match.group(1).strip()
            query = clean_query_text(raw_query)
            pyautogui.press("/")
            time.sleep(0.08)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            paste_text(query)
            pyautogui.press("enter")
            return f"Searching Gmail for '{query}'."

        if any(cmd_lower.startswith(p) for p in ["compose", "write a mail", "write email", "create email", "draft email"]):
            pyautogui.press("c")
            return "Opened new email draft."

        write_match = re.search(r"^(?:write|type|insert)\s+(.+)$", command, flags=re.IGNORECASE)
        if write_match:
            draft_text = write_match.group(1).strip()
            context_state.set_draft(draft_text, draft_type="email")
            paste_text(draft_text)
            return f"Drafted email text. Say 'send the mail' when ready."

        return None


# ============================================================
# 3. BROWSER CONTEXT HANDLER
# ============================================================

class BrowserContextHandler:
    """Handles commands inside focused browser tabs."""

    BROWSERS = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"}

    @classmethod
    def matches(cls, info: Dict[str, Any]) -> bool:
        proc = info.get("process", "").lower()
        title = info.get("title", "").lower()

        # 1. Do not capture if it is a Gmail window
        if GmailContextHandler.matches(info):
            return False

        # 2. Prevent Friday's own UI window/tab from being treated as a generic browser target
        if any(ui_term in title for ui_term in ["frontend", "localhost", "friday", "127.0.0.1", "vite"]):
            return False

        return proc in cls.BROWSERS

    @classmethod
    def handle(cls, command: str, info: Dict[str, Any]) -> Optional[str]:
        if pyautogui is None:
            return None

        cmd_lower = command.lower().strip()

        # Navigation shortcuts
        if any(k in cmd_lower for k in ["new tab", "open tab", "open a new tab", "open new tab"]):
            pyautogui.hotkey("ctrl", "t")
            return "Opened new tab in browser."

        if any(k in cmd_lower for k in ["close tab", "close current tab", "close this tab"]):
            pyautogui.hotkey("ctrl", "w")
            return "Closed current tab."

        if "youtube" in info.get("title", "").lower() or "youtube" in cmd_lower:
            youtube_routes = {
                "subscription": "https://www.youtube.com/feed/subscriptions",
                "subscriptions": "https://www.youtube.com/feed/subscriptions",
                "history": "https://www.youtube.com/feed/history",
                "trending": "https://www.youtube.com/feed/trending",
                "library": "https://www.youtube.com/feed/library",
                "home": "https://www.youtube.com",
            }
            for keyword, target_url in youtube_routes.items():
                if re.search(rf"\b{keyword}\b", cmd_lower):
                    pyautogui.hotkey("ctrl", "l")
                    time.sleep(0.04)
                    pyautogui.hotkey("ctrl", "a")
                    pyautogui.press("backspace")
                    paste_text(target_url)
                    pyautogui.press("enter")
                    return f"Opened YouTube {keyword.capitalize()}."

        # Explicit browser search check: only take over browser when user explicitly requests a browser search/action
        explicit_search_triggers = [
            "search in chrome", "search on chrome", "in chrome",
            "search in browser", "search on browser", "in browser",
            "google this", "search on google", "search google for",
            "browse to", "open url", "go to url"
        ]
        is_explicit_browser_search = any(trigger in cmd_lower for trigger in explicit_search_triggers)

        search_match = re.search(r"^(?:search(?:\s+for)?|look\s+up|find|browse(?:\s+to)?)\s+(.+)$", cmd_lower)
        search_query = None

        if is_explicit_browser_search:
            clean_cmd = cmd_lower
            for trig in explicit_search_triggers:
                clean_cmd = clean_cmd.replace(trig, "")
            search_query = clean_query_text(clean_cmd)
        elif search_match:
            candidate = search_match.group(1).strip()
            if not any(candidate.startswith(q) for q in ["who is", "what is", "where is", "how to", "why is"]):
                search_query = clean_query_text(candidate)

        if search_query:
            if search_query in ["youtube", "open youtube", "youtube.com"]:
                target_url = "https://www.youtube.com"
            elif re.match(r"^https?://", search_query):
                target_url = search_query
            elif "." in search_query and " " not in search_query:
                target_url = f"https://{search_query}"
            else:
                target_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(search_query)}"

            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.04)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            paste_text(target_url)
            pyautogui.press("enter")
            return f"Searched for '{search_query}' in active browser."

        # Page scrolling & navigation
        if cmd_lower in ["scroll down", "page down", "down"]:
            pyautogui.scroll(-500)
            return "Scrolled down."
        if cmd_lower in ["scroll up", "page up", "up"]:
            pyautogui.scroll(500)
            return "Scrolled up."
        if cmd_lower in ["go back", "back"]:
            pyautogui.hotkey("alt", "left")
            return "Navigated back."
        if cmd_lower in ["go forward", "forward"]:
            pyautogui.hotkey("alt", "right")
            return "Navigated forward."

        return None


# ============================================================
# 4. FILE EXPLORER CONTEXT HANDLER
# ============================================================

class FileExplorerContextHandler:
    """Handles commands inside active Windows File Explorer."""

    @classmethod
    def matches(cls, info: Dict[str, Any]) -> bool:
        return (
            info.get("class") == "CabinetWClass"
            or info.get("process") == "explorer.exe"
            or "file explorer" in info.get("title", "").lower()
        )

    @classmethod
    def get_active_explorer_path(cls) -> Optional[str]:
        try:
            import comtypes.client
            shell = comtypes.client.CreateObject("Shell.Application")
            windows = shell.Windows()
            hwnd_foreground = user32.GetForegroundWindow()

            for i in range(windows.Count):
                w = windows.Item(i)
                if w and int(w.HWND) == int(hwnd_foreground):
                    url = w.LocationURL
                    if url and url.startswith("file:///"):
                        local_path = urllib.parse.unquote(url[8:].replace("/", "\\"))
                        if os.path.exists(local_path):
                            return local_path

            if windows.Count > 0:
                w = windows.Item(windows.Count - 1)
                if w and hasattr(w, "LocationURL"):
                    url = w.LocationURL
                    if url and url.startswith("file:///"):
                        local_path = urllib.parse.unquote(url[8:].replace("/", "\\"))
                        if os.path.exists(local_path):
                            return local_path
        except Exception:
            pass
        return None

    @classmethod
    def select_in_explorer_view(cls, target_full_path: str) -> bool:
        """Natively selects and highlights an item in active File Explorer view."""
        try:
            import comtypes.client
            shell = comtypes.client.CreateObject("Shell.Application")
            windows = shell.Windows()
            hwnd_foreground = user32.GetForegroundWindow()

            for i in range(windows.Count):
                w = windows.Item(i)
                if w and int(w.HWND) == int(hwnd_foreground):
                    doc = getattr(w, "Document", None)
                    if doc and hasattr(doc, "Folder"):
                        folder = doc.Folder
                        target_name = Path(target_full_path).name.lower()
                        for item in folder.Items():
                            if item.Name.lower() == target_name or Path(item.Path).name.lower() == target_name:
                                doc.SelectItem(item, 29)
                                return True
        except Exception as e:
            print(f"[FileExplorerContext] COM SelectItem failed: {e}")
        return False

    @classmethod
    def navigate_existing_tab(cls, target_full_path: str) -> bool:
        """Navigates the currently focused File Explorer tab in-place using COM or Address Bar."""
        try:
            import comtypes.client
            shell = comtypes.client.CreateObject("Shell.Application")
            windows = shell.Windows()
            hwnd_foreground = user32.GetForegroundWindow()

            for i in range(windows.Count):
                w = windows.Item(i)
                if w and int(w.HWND) == int(hwnd_foreground):
                    w.Navigate(target_full_path)
                    return True
        except Exception as e:
            print(f"[FileExplorerContext] COM Navigate failed: {e}")

        if pyautogui:
            try:
                pyautogui.hotkey("alt", "d")
                time.sleep(0.08)
                paste_text(target_full_path)
                time.sleep(0.05)
                pyautogui.press("enter")
                return True
            except Exception as e:
                print(f"[FileExplorerContext] Address bar fallback failed: {e}")

        return False

    @classmethod
    def handle(cls, command: str, info: Dict[str, Any]) -> Optional[str]:
        if pyautogui is None:
            return None

        cmd_lower = command.lower().strip()
        active_path = cls.get_active_explorer_path()

        # 1. Navigation
        if cmd_lower in ["go back", "back"]:
            pyautogui.hotkey("alt", "left")
            return "Navigated back."
        if cmd_lower in ["go forward", "forward"]:
            pyautogui.hotkey("alt", "right")
            return "Navigated forward."
        if cmd_lower in ["go up", "up folder", "parent folder"]:
            pyautogui.hotkey("alt", "up")
            return "Navigated to parent directory."

        # 2. SELECT ITEM
        select_match = re.search(r"^(?:select|choose|highlight)\s+(.+)$", cmd_lower)
        if select_match:
            raw_target = select_match.group(1).strip()
            target_name = clean_query_text(raw_target)

            found_path = None
            found_name = None

            if active_path and os.path.exists(active_path):
                try:
                    entries = list(os.scandir(active_path))
                    for entry in entries:
                        if entry.name.lower() == target_name or Path(entry.name).stem.lower() == target_name:
                            found_path = entry.path
                            found_name = entry.name
                            break

                    if not found_path:
                        for entry in entries:
                            if entry.name.lower().startswith(target_name) or Path(entry.name).stem.lower().startswith(target_name):
                                found_path = entry.path
                                found_name = entry.name
                                break
                except Exception as e:
                    print(f"[FileExplorerContext] Scan error: {e}")

            if found_path:
                context_state.set_selected_file(found_path)
                if not cls.select_in_explorer_view(found_path):
                    if pyautogui:
                        pyautogui.press("space")
                        time.sleep(0.05)
                        paste_text(found_name)
                return f"Selected {found_name} in File Explorer."

            paste_text(target_name)
            return f"Selected '{target_name}' in File Explorer."

        # 3. OPEN ITEM (IN-PLACE NAVIGATION FOR ACTIVE TAB / HOVERED FILE)
        open_match = re.search(r"^(?:open|launch|enter|go to)\s+(.+)$", cmd_lower)
        if open_match:
            raw_target = open_match.group(1).strip()
            target_name = clean_query_text(raw_target)

            found_path = None
            found_name = None

            # Check if user specifically referred to hovered / selected item
            is_hover_or_pronoun = target_name in ["", "this", "this file", "this folder", "the file", "the folder", "item", "the item", "folder", "file"]
            if is_hover_or_pronoun:
                hovered = get_hovered_or_selected_file_or_folder()
                if hovered and os.path.exists(hovered):
                    found_path = hovered
                    found_name = Path(hovered).name

            if not found_path and active_path and os.path.exists(active_path):
                try:
                    entries = list(os.scandir(active_path))
                    for entry in entries:
                        if entry.name.lower() == target_name or Path(entry.name).stem.lower() == target_name:
                            found_path = entry.path
                            found_name = entry.name
                            break

                    if not found_path:
                        for entry in entries:
                            if entry.name.lower().startswith(target_name) or Path(entry.name).stem.lower().startswith(target_name):
                                found_path = entry.path
                                found_name = entry.name
                                break
                except Exception as e:
                    print(f"[FileExplorerContext] Scan error: {e}")

            if found_path:
                context_state.set_selected_file(found_path)

                # If existing screen / tab requested or if it is a directory in Explorer
                if any(w in cmd_lower for w in ["existing screen", "existing tab", "current tab", "existing window"]):
                    if os.path.isdir(found_path):
                        if cls.navigate_existing_tab(found_path):
                            return f"Opened {found_name} in existing screen."
                    else:
                        os.startfile(found_path)
                        return f"Opened {found_name} in existing screen."

                if os.path.isdir(found_path):
                    if cls.navigate_existing_tab(found_path):
                        return f"Opened {found_name} in current tab."

                os.startfile(found_path)
                return f"Opened {found_name}."

            paste_text(target_name)
            time.sleep(0.1)
            pyautogui.press("enter")
            return f"Opening '{target_name}' in File Explorer."

        # 4. Search
        search_match = re.search(r"^(?:search(?:\s+for)?|find|locate)\s+(.+)$", cmd_lower)
        if search_match:
            raw_target = search_match.group(1).strip()
            search_target = clean_query_text(raw_target)

            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.08)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.03)
            pyautogui.press("backspace")
            time.sleep(0.03)
            paste_text(search_target)
            pyautogui.press("enter")
            return f"Searching for '{search_target}' in File Explorer."

        return None


# ============================================================
# 5. NOTEPAD CONTEXT HANDLER
# ============================================================

class NotepadContextHandler:
    """Handles text typing and saving inside active Notepad."""

    @classmethod
    def matches(cls, info: Dict[str, Any]) -> bool:
        return "notepad" in info.get("process", "") or "notepad" in info.get("class", "").lower()

    @classmethod
    def handle(cls, command: str, info: Dict[str, Any]) -> Optional[str]:
        if pyautogui is None:
            return None

        cmd_lower = command.lower().strip()
        write_match = re.search(r"^(?:write|type|insert|add text)\s+(.+)$", command, flags=re.IGNORECASE)
        if write_match:
            text_to_write = write_match.group(1)
            paste_text(text_to_write + "\n")
            return "Wrote text into Notepad."

        if cmd_lower in ["save", "save file"]:
            pyautogui.hotkey("ctrl", "s")
            return "Saved Notepad file."

        return None


# ============================================================
# CONTEXT DISPATCHER
# ============================================================

class ContextService:
    def __init__(self):
        self.handlers = [
            WhatsAppContextHandler,
            GmailContextHandler,
            BrowserContextHandler,
            FileExplorerContextHandler,
            NotepadContextHandler,
        ]

    def try_handle_context(self, user_command: str) -> Optional[str]:
        cleaned = user_command.lower().strip()

        info = get_active_window_info()
        if not info or not info.get("process"):
            return None

        window_title = info.get("title", "").lower()
        process_name = info.get("process", "").lower()

        # Hard guard: Ignore Friday's frontend client window
        if any(tag in window_title for tag in ["frontend", "localhost", "friday", "127.0.0.1", ":5173", ":3000", "vite"]):
            return None

        # Hard guard: Conversational queries bypass keyboard automation
        informational_starters = [
            "who is", "who are", "what is", "what are", "where is", "where are",
            "why is", "why does", "when is", "when did", "how to", "how do",
            "tell me", "explain", "describe", "can you"
        ]
        if any(cleaned.startswith(q) for q in informational_starters):
            return None

        # Explicit file sending commands from ANY foreground window
        if any(p in cleaned for p in ["send this file", "send the selected file", "send selected file", "send file", "send this folder", "send the selected folder"]):
            return WhatsAppContextHandler.handle(user_command, info)

        # Global WhatsApp Draft Dispatch
        if cleaned in ["send", "send it", "send message", "send the message", "send that", "send that message"]:
            if context_state.has_draft() and context_state.draft_type == "whatsapp":
                force_focus_window("whatsapp.root.exe", "whatsapp")
                time.sleep(0.35)
                if pyautogui:
                    pyautogui.press("enter")
                contact = context_state.selected_contact or "contact"
                context_state.clear_draft()
                return f"Sent drafted message to {contact.capitalize()}."

        # Standalone application launches bypass context (unless File Explorer is focused)
        is_file_explorer = (
            info.get("class") == "CabinetWClass"
            or process_name == "explorer.exe"
            or "file explorer" in window_title
        )

        if not is_file_explorer:
            if any(cleaned.startswith(p) for p in [
                "open app", "launch app", "play ", "open spiderman", "open spider man",
                "open whatsapp", "open chrome", "open notepad", "open calculator"
            ]):
                if cleaned == "open whatsapp":
                    if os.name == "nt":
                        os.system("start whatsapp:")
                    else:
                        os.system("xdg-open whatsapp:// &")
                    return "Opening WhatsApp, Harishan."
                return None

        try:
            print(f"[ContextService] Active Window: '{info.get('title')}' | Process: '{info.get('process')}'")

            for handler in self.handlers:
                if hasattr(handler, "matches") and handler.matches(info):
                    result = handler.handle(user_command, info)
                    if result:
                        print(f"[ContextService] Handled via {handler.__name__}: {result}")
                        return result
        except Exception as e:
            print(f"[ContextService] Warning during context evaluation: {e}")

        return None


context_service = ContextService()