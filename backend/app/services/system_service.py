"""
Friday System Service
Manages system execution, screen capture, camera capture, tab controls, and OS tools.
"""

from __future__ import annotations

import datetime
import os
import re
import shutil
import json
import subprocess
import time
import urllib.parse
import winreg
from pathlib import Path
from typing import Dict, List, Optional

try:
    import pyautogui
except ImportError:
    pyautogui = None


class SystemService:
    def __init__(self):
        self.home_dir = Path.home()
        self.pictures_dir = self.home_dir / "Pictures"
        self.screenshots_dir = self.pictures_dir / "Screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        # Standard discovery roots across drives
        self.search_directories: List[Path] = [
            self.home_dir / "Desktop",
            self.home_dir / "Downloads",
            self.home_dir / "Documents",
            self.home_dir / "Pictures",
            self.home_dir / "Videos",
            self.home_dir / "Music",
            self.home_dir,
            Path("C:/"),
            Path("D:/"),
        ]

        self.direct_app_aliases: Dict[str, Path] = {}

        self.uwp_protocols: Dict[str, str] = {
            "whatsapp": "whatsapp:",
            "spotify": "spotify:",
            "calculator": "calc",
            "calc": "calc",
            "notepad": "notepad",
            "paint": "mspaint",
            "task manager": "taskmgr",
            "taskmgr": "taskmgr",
            "settings": "ms-settings:",
            "camera": "microsoft.windows.camera:",
            "chrome": "chrome",
            "google chrome": "chrome",
            "edge": "msedge",
            "explorer": "explorer",
            "file explorer": "explorer",
            "word": "winword",
            "ms word": "winword",
            "excel": "excel",
            "powerpoint": "powerpnt",
            "cmd": "cmd",
            "command prompt": "cmd",
            "powershell": "powershell",
            "code": "code",
            "vscode": "code",
            "vs code": "code",
            "photo": "ms-photos:",
            "photos": "ms-photos:",
        }

    # ============================================================
    # SCREENSHOT & CAMERA ACTIONS
    # ============================================================

    def take_screenshot(self, user_message: str = "") -> str:
        """Captures the screen and saves it into the Pictures/Screenshots directory."""
        if pyautogui is None:
            return "PyAutoGUI is not installed for taking screenshots."

        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            file_path = self.screenshots_dir / f"Screenshot_{timestamp}.png"
            screenshot = pyautogui.screenshot()
            screenshot.save(str(file_path))
            print(f"[SystemService] Screenshot saved: {file_path}")
            return f"Screenshot taken and saved to Screenshots folder."
        except Exception as e:
            return f"Failed to take screenshot: {e}"

    def take_photo(self, user_message: str = "") -> str:
        """Opens the Windows Camera application and takes a picture."""
        try:
            os.system("start microsoft.windows.camera:")
            time.sleep(1.2)
            if pyautogui:
                pyautogui.press("enter")
            return "Camera opened and photo captured."
        except Exception as e:
            return f"Failed to access camera: {e}"

    # ============================================================
    # GLOBAL TAB ACTIONS
    # ============================================================

    def open_new_tab(self, user_message: str = "") -> str:
        if pyautogui:
            pyautogui.hotkey("ctrl", "t")
            return "Opened new tab."
        return "Cannot perform keystroke."

    def close_current_tab(self, user_message: str = "") -> str:
        if pyautogui:
            pyautogui.hotkey("ctrl", "w")
            return "Closed current tab."
        return "Cannot perform keystroke."

    # ============================================================
    # CLEANING HELPERS
    # ============================================================

    def _clean_app_name(self, command: str) -> str:
        cleaned = command.lower().strip()
        for pattern in [
            r"^fridays\s+", r"^friday\s+", r"^open\s+", r"^launch\s+", r"^start\s+", r"^run\s+", r"^play\s+",
            r"^opening\s+", r"^show\s+", r"^go to\s+", r"^bring\s+",
            r"\s+app$", r"\s+application$", r"\s+game$"
        ]:
            cleaned = re.sub(pattern, "", cleaned).strip()
        for noise in ["please ", "friday ", "the ", "a ", "my "]:
            if cleaned.startswith(noise):
                cleaned = cleaned[len(noise):].strip()
        return " ".join(cleaned.split()).strip()

    def _normalize_query(self, query: str) -> str:
        """Universal normalizer that handles spoken words like 'underscore', 'dash', 'hyphen' and strips special chars."""
        q = query.lower()
        q = q.replace("underscore", "_").replace("dash", "-").replace("hyphen", "-").replace("dot", ".")
        return re.sub(r'[^a-z0-9]', '', q)

    # ============================================================
    # ADD PATH JSON FALLBACK DATABASE CHECKER
    # ============================================================

    def _check_add_path_json(self, query: str) -> Optional[str]:
        """Checks the add_path.json database for route name and path pairings with robust token matching."""
        json_path = Path(r"C:\Users\Harishan\Desktop\AI_ASSISTANT\database\add_path.json")
        if not json_path.exists():
            json_path = Path("database/add_path.json")
        
        if not json_path.exists():
            return None

        try:
            content = json_path.read_text(encoding="utf-8")
            data = json.loads(content)
            
            clean_q = self._clean_app_name(query)
            query_tokens = set(re.findall(r'[a-z0-9]+', clean_q.lower()))
            q_plain = self._normalize_query(clean_q)
            
            paths_to_check = []
            if isinstance(data, dict):
                if "paths" in data and isinstance(data["paths"], list):
                    paths_to_check = data["paths"]
                else:
                    paths_to_check = [{"route_name": k, "path": v} for k, v in data.items()]
            elif isinstance(data, list):
                paths_to_check = data

            for item in paths_to_check:
                r_name = str(item.get("route_name", "") or item.get("name", ""))
                f_path = str(item.get("path", "") or item.get("location", ""))
                if not r_name or not f_path:
                    continue
                
                route_tokens = set(re.findall(r'[a-z0-9]+', r_name.lower()))
                r_plain = self._normalize_query(r_name)
                
                matched = False
                if q_plain and r_plain and (q_plain in r_plain or r_plain in q_plain):
                    matched = True
                elif query_tokens and route_tokens and query_tokens.issubset(route_tokens):
                    matched = True
                elif query_tokens and route_tokens and route_tokens.issubset(query_tokens):
                    matched = True

                if matched:
                    p = Path(f_path)
                    if p.exists():
                        os.startfile(str(p))
                        if p.is_file():
                            return f"Opened file: {p.name}."
                        elif p.is_dir():
                            return f"Opened folder: {p.name}."
                        else:
                            return f"Opened {p.name}."
                    else:
                        print(f"[AddPath Error] Path specified in json does not exist on disk: {f_path}", flush=True)
        except Exception as e:
            print(f"[AddPath JSON Error]: {e}", flush=True)
        return None

    # ============================================================
    # 1. FOLDER OPENING
    # ============================================================

    def open_folder(self, folder_query: str) -> str:
        raw_target = self._clean_app_name(folder_query)
        for p in ["folder", "directory", "dir"]:
            raw_target = re.sub(rf"\b{p}\b", "", raw_target).strip()
        raw_target = " ".join(raw_target.split()).strip()

        if not raw_target:
            os.system("explorer")
            return "Opened File Explorer."

        known_dirs = {
            "downloads": self.home_dir / "Downloads",
            "download": self.home_dir / "Downloads",
            "documents": self.home_dir / "Documents",
            "document": self.home_dir / "Documents",
            "desktop": self.home_dir / "Desktop",
            "pictures": self.home_dir / "Pictures",
            "picture": self.home_dir / "Pictures",
            "videos": self.home_dir / "Videos",
            "video": self.home_dir / "Videos",
            "music": self.home_dir / "Music",
        }

        if raw_target in known_dirs and known_dirs[raw_target].exists():
            os.startfile(str(known_dirs[raw_target]))
            return f"Opened {raw_target.capitalize()} folder."

        target_plain = self._normalize_query(raw_target)
        for root in self.search_directories:
            if not root.exists():
                continue
            try:
                for item in root.iterdir():
                    if item.is_dir():
                        item_plain = self._normalize_query(item.name)
                        if target_plain in item_plain:
                            os.startfile(str(item))
                            return f"Opened folder: {item.name}."
            except (PermissionError, OSError):
                continue

        json_result = self._check_add_path_json(folder_query)
        if json_result:
            return json_result

        return f"'{folder_query}' folder not found"

    # ============================================================
    # 2. FILE OPENING (.PDF, .DOCX, .TXT, .EXE, ETC.)
    # ============================================================

    def open_file_explorer(self, user_message: str = "") -> str:
        """Launches the Windows File Explorer."""
        try:
            os.system("explorer")
            return "Opening File Explorer."
        except Exception as e:
            return f"Failed to open File Explorer: {e}"

    def open_file(self, file_query: str) -> str:
        raw_target = self._clean_app_name(file_query)
        for p in ["file", "document", "doc", "pdf"]:
            raw_target = re.sub(rf"\b{p}\b", "", raw_target).strip()
        raw_target = " ".join(raw_target.split()).strip()

        if not raw_target:
            raw_target = file_query

        target_plain = self._normalize_query(raw_target)

        # Prioritize key user folders where documents are stored safely
        priority_roots = [
            self.home_dir / "Downloads",
            self.home_dir / "Desktop",
            self.home_dir / "Documents",
        ]
        all_roots = priority_roots + [r for r in self.search_directories if r not in priority_roots]

        for root in all_roots:
            if not root.exists():
                continue
            try:
                # Check files directly in root directory
                for item in root.iterdir():
                    if item.is_file():
                        file_plain = self._normalize_query(item.name)
                        stem_plain = self._normalize_query(item.stem)
                        if target_plain in file_plain or target_plain in stem_plain:
                            os.startfile(str(item))
                            return f"Opened file: {item.name}."
                    elif item.is_dir():
                        # Check one level deep inside subfolders safely without throwing crashes
                        try:
                            for sub_item in item.iterdir():
                                if sub_item.is_file():
                                    file_plain = self._normalize_query(sub_item.name)
                                    stem_plain = self._normalize_query(sub_item.stem)
                                    if target_plain in file_plain or target_plain in stem_plain:
                                        os.startfile(str(sub_item))
                                        return f"Opened file: {sub_item.name}."
                        except (PermissionError, OSError):
                            continue
            except (PermissionError, OSError):
                continue

        # Check add_path.json fallback database by route name[cite: 5]
        json_result = self._check_add_path_json(file_query)
        if json_result:
            return json_result

        return f"'{file_query}' not found"

    # ============================================================
    # 3. SMART UNIVERSAL DYNAMIC DISCOVERY
    # ============================================================

    def _find_executable_dynamically(self, cleaned_name: str) -> Optional[Path]:
        query_plain = self._normalize_query(cleaned_name)
        if not query_plain:
            return None

        search_roots = [
            Path("D:/"),
            Path("C:/Games"),
            Path("C:/Program Files"),
            Path("C:/Program Files (x86)"),
            self.home_dir / "Desktop",
            self.home_dir / "Downloads"
        ]

        for base_path in search_roots:
            if not base_path.exists():
                continue
            try:
                for entry in base_path.iterdir():
                    if entry.is_dir():
                        for root, _, files in os.walk(entry):
                            for file in files:
                                if file.endswith(".exe") and "unins" not in file.lower() and "crash" not in file.lower() and "setup" not in file.lower():
                                    file_plain = self._normalize_query(file)
                                    folder_plain = self._normalize_query(Path(root).name)
                                    parent_plain = self._normalize_query(Path(root).parent.name)
                                    
                                    if query_plain in file_plain or query_plain in folder_plain or query_plain in parent_plain:
                                        return Path(root) / file
            except (PermissionError, OSError):
                continue
        return None

    def open_application(self, app_name: str) -> str:
        cleaned = self._clean_app_name(app_name)
        if not cleaned:
            json_result = self._check_add_path_json(app_name)
            if json_result:
                return json_result
            return f"'{app_name}' not found"

        # Handle compound app + search commands
        search_match = re.search(r"^(.*?)(?:\s+and\s+|\s+to\s+)(?:search|look\s+for|browse)\s+(.+)$", cleaned, re.IGNORECASE)
        if not search_match:
            search_match = re.search(r"^(.*?)\s+and\s+search\s+(.+)$", cleaned, re.IGNORECASE)

        if search_match:
            app_part = search_match.group(1).strip()
            query_part = search_match.group(2).strip()
            search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query_part)}"
            if "chrome" in app_part:
                os.system(f'start chrome "{search_url}"')
            elif "edge" in app_part:
                os.system(f'start msedge "{search_url}"')
            else:
                os.system(f'start "{search_url}"')
            return f"Opening browser and searching for '{query_part}', Harishan."

        if cleaned in self.direct_app_aliases:
            target_path = self.direct_app_aliases[cleaned]
            if target_path.exists():
                os.startfile(str(target_path))
                return f"Opening {cleaned.capitalize()}."

        if cleaned in self.uwp_protocols:
            protocol = self.uwp_protocols[cleaned]
            try:
                if protocol.endswith(":"):
                    os.system(f"start {protocol}")
                else:
                    os.system(f"start {protocol}")
                return f"Opening {cleaned.capitalize()}."
            except Exception:
                pass

        resolved = shutil.which(cleaned) or shutil.which(f"{cleaned}.exe")
        if resolved:
            try:
                os.startfile(resolved)
                return f"Opening {cleaned.capitalize()}."
            except Exception:
                pass

        reg_keys = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"
        ]
        for key_path in reg_keys:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as root_key:
                    num_subkeys = winreg.QueryInfoKey(root_key)[0]
                    for i in range(num_subkeys):
                        sub_name = winreg.EnumKey(root_key, i)
                        if cleaned in sub_name.lower():
                            with winreg.OpenKey(root_key, sub_name) as app_key:
                                exe_path, _ = winreg.QueryValueEx(app_key, "")
                                if exe_path and os.path.exists(exe_path):
                                    os.startfile(exe_path)
                                    return f"Opening {cleaned.capitalize()}."
            except Exception:
                continue

        dynamic_exe = self._find_executable_dynamically(cleaned)
        if dynamic_exe and dynamic_exe.exists():
            os.startfile(str(dynamic_exe))
            return f"Opening {dynamic_exe.name}, Harishan."

        try:
            os.startfile(cleaned)
            return f"Opening {cleaned.capitalize()}."
        except Exception:
            pass

        # Check add_path.json fallback database[cite: 5]
        json_result = self._check_add_path_json(app_name)
        if json_result:
            return json_result

        return f"'{app_name}' not found"

    def close_application(self, app_query: str) -> str:
        cleaned = self._clean_app_name(app_query)
        for p in ["close", "exit", "quit", "app", "application"]:
            cleaned = re.sub(rf"\b{p}\b", "", cleaned).strip()
        cleaned = " ".join(cleaned.split()).strip()
        
        if not cleaned:
            if pyautogui:
                pyautogui.hotkey("alt", "f4")
                return "Closed active window."
            return "No application specified."

        process_map = {
            "whatsapp": ["whatsapp.exe", "whatsapp.root.exe"],
            "chrome": ["chrome.exe"],
            "notepad": ["notepad.exe"],
            "spotify": ["spotify.exe"],
            "calculator": ["calc.exe"],
        }
        
        targets = process_map.get(cleaned, [f"{cleaned}.exe", f"{cleaned.replace(' ', '')}.exe"])
        killed = False
        for proc_name in targets:
            res = os.system(f"taskkill /f /im {proc_name} >nul 2>&1")
            if res == 0:
                killed = True
        
        if killed:
            return f"Closed {cleaned.capitalize()}, Harishan."
        
        if pyautogui:
            pyautogui.hotkey("alt", "f4")
            return f"Closed active window, Harishan."
            
        return f"'{app_query}' process not found."

    # ============================================================
    # DISPATCHER
    # ============================================================

    def execute(self, action: str = "", user_message: str = "", *args, **kwargs) -> str:
        target_action = action or kwargs.get("command") or ""
        target_message = user_message or kwargs.get("user_message") or ""

        clean = target_message.lower().strip()

        # Route document/file/resume requests directly to open_file first
        file_exts = [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".csv", ".png", ".jpg", ".md", ".exe"]
        if target_action == "open_file" or any(clean.endswith(ext) or ext in clean for ext in file_exts) or "file" in clean or "document" in clean or "resume" in clean or "cv" in clean:
            return self.open_file(target_message)

        if target_action and hasattr(self, target_action):
            method = getattr(self, target_action)
            if callable(method):
                try:
                    return method(target_message)
                except TypeError:
                    return method()

        if target_action == "open_file_explorer" or any(k in clean for k in ["file explorer", "files explorer", "windows explorer"]):
            return self.open_file_explorer(target_message)

        if target_action in ["open_folder", "open_path"] or "folder" in clean or "directory" in clean or bool(re.search(r"\b[A-Za-z]:[\\/]?$", clean)):
            drive_match = re.search(r"\b([A-Za-z]):[\\/]?", target_message)
            if drive_match:
                drive_root = f"{drive_match.group(1).upper()}:\\"
                if os.path.exists(drive_root):
                    os.startfile(drive_root)
                    return f"Opened drive {drive_match.group(1).upper()}."
            return self.open_folder(target_message)

        return self.open_application(target_message)


system_service = SystemService()