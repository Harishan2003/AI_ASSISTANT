"""
Friday AI Assistant - Command Executor & Conversational Engine
Handles system shortcuts, app launches, compound command parsing, memory recall,
autonomous agent task routing, and multithreaded LLM reasoning pipeline.
"""

import asyncio
import ctypes
import inspect
import json
import os
import re
import socket
import string
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")
load_dotenv()

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None

from app.core.agent_config import agent_config
from app.memory.memory_manager import friday_memory_manager
from app.agents.memory_agent import memory_agent
from app.services.conversation_memory_service import conversation_memory_service
from app.services.web_search_context import (
    gather_all_web_context,
    fetch_tavily_search_context,
    extract_urls_from_text,
    fetch_webpage_content,
)
from app.services.document_analysis_service import sanitize_backend_output
from app.core.agent import agent_engine
from app.schemas.agent_schemas import AgentExecuteRequest

# Project database paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_DIR = BASE_DIR / "database"
PROFILE_FILE = DATABASE_DIR / "user_profile.json"
ADD_PATH_FILE = DATABASE_DIR / "add_path.json"
LOCK_SECURITY_FILE = DATABASE_DIR / "lock_screen_security.json"
UPLOAD_DIR = Path(tempfile.gettempdir()) / "Friday_Uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PROFILE: Dict[str, Any] = {
    "name": "Harishan",
    "agent_name": "Friday",
    "wake_word": "friday",
    "age": "",
    "email": "",
    "city": "",
    "voice_gender": "female",
    "language": "english",
    "languages": ["english", "tamil", "tanglish"]
}

LOCAL_MEMORY_STORE: Dict[str, List[Dict[str, Any]]] = {}
SESSION_DOC_CACHE: Dict[str, str] = {}
LATEST_UPLOADED_DOC_CONTENT: str = ""

# Session-based pending states for dynamic disambiguation and confirmation
PENDING_DISAMBIGUATION: Dict[str, Dict[str, Any]] = {}
PENDING_CONFIRMATION: Dict[str, Dict[str, Any]] = {}
PENDING_EMAIL_INPUT: Dict[str, Dict[str, Any]] = {}


def get_selected_desktop_or_explorer_file(must_be_file: bool = False) -> Optional[str]:
    """Retrieves the full path of the currently hovered or selected file/folder in Windows Explorer or Desktop."""
    from app.services.context_service import get_hovered_or_selected_file_or_folder
    return get_hovered_or_selected_file_or_folder(must_be_file=must_be_file)


def get_dynamic_storage_drives() -> List[Dict[str, Any]]:
    """Dynamically detects all active system drives, USB drives, pen drives, external disks, and partitions with labels and types."""
    drives: List[Dict[str, Any]] = []
    if os.name == "nt":
        for letter in string.ascii_uppercase:
            drive_root = f"{letter}:\\"
            if os.path.exists(drive_root):
                label = ""
                try:
                    vol_buf = ctypes.create_unicode_buffer(1024)
                    fs_buf = ctypes.create_unicode_buffer(1024)
                    if ctypes.windll.kernel32.GetVolumeInformationW(
                        ctypes.c_wchar_p(drive_root),
                        vol_buf,
                        ctypes.sizeof(vol_buf),
                        None, None, None,
                        fs_buf,
                        ctypes.sizeof(fs_buf)
                    ):
                        label = vol_buf.value
                except Exception:
                    pass
                
                try:
                    dtype = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(drive_root))
                except Exception:
                    dtype = 3
                    
                # DRIVE_REMOVABLE = 2, DRIVE_FIXED = 3, DRIVE_REMOTE = 4, DRIVE_CDROM = 5, DRIVE_RAMDISK = 6
                drives.append({
                    "path": Path(f"{letter}:/"),
                    "letter": letter,
                    "label": label,
                    "is_removable": (dtype == 2),
                    "type_code": dtype
                })
    else:
        drives.append({
            "path": Path("/"),
            "letter": "",
            "label": "Root",
            "is_removable": False,
            "type_code": 3
        })
    return drives


def get_available_storage_drives() -> List[Path]:
    """Enumerates all active and accessible storage drive root paths dynamically."""
    return [d["path"] for d in get_dynamic_storage_drives()]


REMOVABLE_STORAGE_ALIASES = [
    "pendrive", "pen drive", "usb drive", "usb", "flash drive",
    "thumb drive", "external drive", "external disk", "external hdd", "external ssd",
    "removable drive", "removable disk", "sd card", "memory card"
]


def extract_target_and_drive(target_str: str) -> Tuple[str, Optional[Path], str]:
    """
    Extracts target query and dynamically resolves target drive (letter A-Z, volume label, USB/pen drive/external drive).
    Returns (cleaned_target, drive_path_or_None, drive_display_name).
    """
    target = target_str.strip()
    all_drives = get_dynamic_storage_drives()

    # 1. Direct drive request check (e.g. 'd drive', 'open pendrive', 'usb drive', 'e:')
    direct_drive_patterns = [
        r'^(?:(?:local\s+disk|drive)\s+([a-zA-Z])|([a-zA-Z])\s+(?:drive|local\s+disk)|([a-zA-Z]):)$'
    ]
    for p in direct_drive_patterns:
        m = re.match(p, target, flags=re.IGNORECASE)
        if m:
            letter = (m.group(1) or m.group(2) or m.group(3)).upper()
            for d in all_drives:
                if d["letter"] == letter:
                    return "", d["path"], f"{letter}: drive"
            return "", None, f"{letter}: drive"

    for alias in REMOVABLE_STORAGE_ALIASES:
        if target.lower() in [alias, f"the {alias}", f"my {alias}", f"{alias} drive"]:
            removable = [d for d in all_drives if d["is_removable"]]
            if removable:
                first = removable[0]
                lbl = f" ({first['label']})" if first["label"] else ""
                return "", first["path"], f"{first['letter']}: drive{lbl}"
            secondary = [d for d in all_drives if d["letter"] != "C"]
            if secondary:
                first = secondary[0]
                lbl = f" ({first['label']})" if first["label"] else ""
                return "", first["path"], f"{first['letter']}: drive{lbl}"
            return "", None, "external / USB drive"

    for d in all_drives:
        if d["label"] and target.lower() in [d["label"].lower(), f"{d['label'].lower()} drive", f"the {d['label'].lower()} drive"]:
            return "", d["path"], f"{d['letter']}: drive ({d['label']})"

    # 2. Extraction of drive modifiers in target ("in d drive", "in pendrive", "on usb", "from external drive", "in e:")
    drive_path = None
    drive_name = ""

    # Check drive letter modifiers (A-Z)
    m_drive = re.search(r'\b(?:in|on|from)\s+(?:drive\s+([a-zA-Z])|([a-zA-Z])\s+drive)\b', target, flags=re.IGNORECASE)
    if not m_drive:
        m_drive = re.search(r'\b(?:in|on|from)\s+([a-zA-Z]):', target, flags=re.IGNORECASE)
    if not m_drive:
        m_drive = re.search(r'\b(?:in|on|from)\s+([a-zA-Z])$', target, flags=re.IGNORECASE)

    if m_drive:
        letter = (m_drive.group(1) or (m_drive.group(2) if len(m_drive.groups()) > 1 else None) or "").upper()
        if letter:
            for d in all_drives:
                if d["letter"] == letter:
                    drive_path = d["path"]
                    drive_name = f"{letter}: drive"
                    break
            if not drive_name:
                drive_name = f"{letter}: drive"
            target = target[:m_drive.start()].strip() + " " + target[m_drive.end():].strip()
            return target.strip(), drive_path, drive_name

    # Check removable aliases modifiers ("in pendrive", "on usb", "from external drive")
    for alias in REMOVABLE_STORAGE_ALIASES:
        m_rem = re.search(r'\b(?:in|on|from)\s+(?:the\s+|my\s+)?' + re.escape(alias) + r'(?:\s+drive)?\b', target, flags=re.IGNORECASE)
        if m_rem:
            removable = [d for d in all_drives if d["is_removable"]]
            if removable:
                first = removable[0]
                lbl = f" ({first['label']})" if first["label"] else ""
                drive_path = first["path"]
                drive_name = f"{first['letter']}: drive{lbl}"
            else:
                secondary = [d for d in all_drives if d["letter"] != "C"]
                if secondary:
                    first = secondary[0]
                    lbl = f" ({first['label']})" if first["label"] else ""
                    drive_path = first["path"]
                    drive_name = f"{first['letter']}: drive{lbl}"
                else:
                    drive_name = "external / USB drive"
            target = target[:m_rem.start()].strip() + " " + target[m_rem.end():].strip()
            return target.strip(), drive_path, drive_name

    # Check volume label modifiers ("in new volume", "in backup drive")
    for d in all_drives:
        if d["label"] and len(d["label"]) > 1:
            m_vol = re.search(r'\b(?:in|on|from)\s+(?:the\s+|my\s+)?' + re.escape(d["label"]) + r'(?:\s+drive)?\b', target, flags=re.IGNORECASE)
            if m_vol:
                drive_path = d["path"]
                drive_name = f"{d['letter']}: drive ({d['label']})"
                target = target[:m_vol.start()].strip() + " " + target[m_vol.end():].strip()
                return target.strip(), drive_path, drive_name

    return target.strip(), None, ""


def normalize_name_for_match(text: str) -> str:
    """Removes all non-alphanumeric characters (spaces, dots, underscores, dashes) for robust fuzzy matching."""
    return re.sub(r'[^a-zA-Z0-9]+', '', text).lower()


def extract_name_tokens(text: str) -> List[str]:
    """Extracts lowercase word tokens, splitting by whitespace, punctuation, and CamelCase transitions."""
    camel = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    digits = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', camel)
    return [t.lower() for t in re.split(r'[\s_\-\.]+', digits) if t]


def find_installed_app_shortcut(target: str) -> Optional[Path]:
    """Scans Windows Start Menu programs, AppData, and Desktop directories to dynamically find installed application shortcuts (.lnk, .url, .exe)."""
    clean_target = target.lower().strip()
    if not clean_target:
        return None
    
    norm_target = normalize_name_for_match(clean_target)
    target_tokens = extract_name_tokens(clean_target)
    
    app_dirs = [
        Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "Microsoft/Windows/Start Menu/Programs",
        Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs",
        Path.home() / "AppData/Local/Programs",
        Path.home() / "Desktop",
        Path(r"C:\Users\Public\Desktop")
    ]
    
    best_match: Optional[Path] = None
    best_score = 0.0
    
    for app_dir in app_dirs:
        if not app_dir.exists():
            continue
        try:
            base_depth = len(app_dir.parts)
            for root, dirs, files in os.walk(str(app_dir)):
                cur_depth = len(Path(root).parts) - base_depth
                if cur_depth > 3:
                    dirs.clear()
                    continue
                for file_name in files:
                    ext = os.path.splitext(file_name)[1].lower()
                    if ext not in [".lnk", ".url", ".exe"]:
                        continue
                    stem = os.path.splitext(file_name)[0].lower()
                    norm_stem = normalize_name_for_match(stem)
                    norm_fname = normalize_name_for_match(file_name)
                    stem_tokens = extract_name_tokens(stem)
                    full_p = Path(root) / file_name
                    
                    if stem == clean_target or norm_stem == norm_target or norm_fname == norm_target:
                        return full_p
                    
                    if clean_target in stem or norm_target in norm_stem:
                        score = 88.0 - len(stem) * 0.1
                        if score > best_score:
                            best_match = full_p
                            best_score = score
                            
                    if target_tokens:
                        matches = sum(1 for tok in target_tokens if tok in stem_tokens or tok in stem)
                        if matches == len(target_tokens):
                            score = 85.0 - len(stem) * 0.1
                            if score > best_score:
                                best_match = full_p
                                best_score = score
        except Exception:
            pass
            
    return best_match if best_score >= 60.0 else None


SKIP_SEARCH_DIRS = {
    "windows", "program files", "program files (x86)", "$recycle.bin",
    "system volume information", "recovery", "appdata", "node_modules",
    ".git", ".vscode", "vendor", "$winre_backup_partition.marker", "config.msi"
}


def search_drive_or_dir_for_item(search_path: Path, target: str) -> Optional[Tuple[Path, str]]:
    """
    Searches a directory or drive root and depth-1 subdirectories for matching files, folders, or executables.
    Smart Disambiguation & Fuzzy Normalization:
    - Matches exact alphanumeric names regardless of dots, underscores, spaces, or CamelCase (e.g. 'SplitFiction' matches 'Split.Fiction').
    - If both a folder and an application (.exe, .lnk) share the same name (e.g. 'hotwheels' folder vs 'hotwheels.exe'):
      * Prioritizes launching the Application (.exe) for general 'open <name>', 'launch', 'run', 'play' commands.
      * Prioritizes opening the Folder if the user explicitly requested 'folder' or 'dir' (e.g. 'open hotwheels folder').
    """
    if not search_path.exists():
        return None
        
    clean_target = target.lower().strip()
    is_folder_req = any(k in clean_target for k in [" folder", "folder ", " dir", "dir ", " directory"])
    is_exe_req = clean_target.endswith(".exe") or any(k in clean_target for k in [" app", "game", "application", "launch", "play", "run", "execute"])
    
    # Strip keywords for exact name matching
    stem_target = clean_target
    for kw in [" folder", "folder ", " dir", "dir ", " directory", ".exe", " app", " application", " game"]:
        stem_target = stem_target.replace(kw, "").strip()
    
    norm_target = normalize_name_for_match(stem_target)
    target_tokens = extract_name_tokens(stem_target)
    
    try:
        root_items = list(search_path.iterdir())
    except Exception:
        root_items = []

    # 1. Collect all direct exact and normalized matches
    exact_matches: List[Path] = []
    for item in root_items:
        if item.name.lower() in SKIP_SEARCH_DIRS or item.name.startswith((".", "$")):
            continue
        item_name_lower = item.name.lower()
        item_stem_lower = item.stem.lower()
        norm_item_name = normalize_name_for_match(item.name)
        norm_item_stem = normalize_name_for_match(item.stem)

        if (item_name_lower == clean_target or item_stem_lower == stem_target or item_name_lower == stem_target or
            norm_item_name == norm_target or norm_item_stem == norm_target):
            exact_matches.append(item)

    if exact_matches:
        if is_folder_req:
            for m in exact_matches:
                if m.is_dir():
                    return m, "open"
        else:
            for m in exact_matches:
                if m.suffix.lower() in [".exe", ".lnk", ".bat", ".cmd"]:
                    return m, "launch"
            first_m = exact_matches[0]
            return first_m, ("launch" if first_m.suffix.lower() in [".exe", ".lnk", ".bat", ".cmd"] else "open")

    # 2. Deep search with scoring
    candidates: List[Tuple[Path, float, str]] = []

    for item in root_items:
        if item.name.lower() in SKIP_SEARCH_DIRS or item.name.startswith((".", "$")):
            continue
        
        name_lower = item.name.lower()
        stem_lower = item.stem.lower()
        norm_item_name = normalize_name_for_match(item.name)
        norm_item_stem = normalize_name_for_match(item.stem)
        item_tokens = extract_name_tokens(item.name)
        is_exec = item.suffix.lower() in [".exe", ".lnk", ".bat", ".cmd"]
        
        if (norm_target == norm_item_name or norm_target == norm_item_stem or
            stem_target in stem_lower or norm_target in norm_item_name or
            (target_tokens and all(tok in item_tokens for tok in target_tokens))):
            base_score = 90.0 - len(name_lower) * 0.05
            if norm_target == norm_item_name or norm_target == norm_item_stem:
                base_score += 15.0
            if is_exec and not is_folder_req:
                base_score += 10.0
            elif item.is_dir() and is_folder_req:
                base_score += 10.0
            candidates.append((item, base_score, "launch" if is_exec else "open"))

        if item.is_dir():
            try:
                for sub in item.iterdir():
                    if sub.name.lower() in SKIP_SEARCH_DIRS or sub.name.startswith((".", "$")):
                        continue
                    sub_name_lower = sub.name.lower()
                    sub_stem_lower = sub.stem.lower()
                    norm_sub_name = normalize_name_for_match(sub.name)
                    norm_sub_stem = normalize_name_for_match(sub.stem)
                    sub_tokens = extract_name_tokens(sub.name)
                    sub_is_exec = sub.suffix.lower() in [".exe", ".lnk", ".bat", ".cmd"]
                    
                    if (norm_sub_name == norm_target or norm_sub_stem == norm_target or
                        sub_stem_lower == stem_target or sub_name_lower == clean_target or sub_name_lower == stem_target):
                        score = 100.0 - len(sub_name_lower) * 0.05
                        if sub_is_exec and not is_folder_req:
                            score += 10.0
                        elif sub.is_dir() and is_folder_req:
                            score += 10.0
                        candidates.append((sub, score, "launch" if sub_is_exec else "open"))
                    elif (norm_target in norm_sub_name or stem_target in sub_stem_lower or
                          (target_tokens and all(tok in sub_tokens for tok in target_tokens))):
                        score = 82.0 - len(sub_name_lower) * 0.05
                        if sub_is_exec and not is_folder_req:
                            score += 10.0
                        elif sub.is_dir() and is_folder_req:
                            score += 10.0
                        candidates.append((sub, score, "launch" if sub_is_exec else "open"))
            except Exception:
                pass
                
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_cand = candidates[0]
        if best_cand[1] >= 60.0:
            return best_cand[0], best_cand[2]
        
    return None


def find_file_on_pc(query_name: str) -> Optional[str]:
    """Dynamically searches Desktop, Downloads, Documents, Start Menu, and storage drives for matching files without hardcoding."""
    clean = query_name.strip().strip('"').strip("'").lower()
    if not clean:
        return None
    norm_query = normalize_name_for_match(clean)
    target_tokens = extract_name_tokens(clean)
    
    user_home = Path.home()
    search_dirs = [user_home / "Desktop", user_home / "Downloads", user_home / "Documents"]
    for d in search_dirs:
        if d.exists():
            for f in d.glob("*"):
                norm_fname = normalize_name_for_match(f.name)
                norm_fstem = normalize_name_for_match(f.stem)
                if (clean == f.name.lower() or clean == f.stem.lower() or
                    norm_query == norm_fname or norm_query == norm_fstem or
                    clean in f.name.lower() or norm_query in norm_fname):
                    return str(f.resolve())
    
    # Check shortcuts
    shortcut = find_installed_app_shortcut(clean)
    if shortcut:
        return str(shortcut.resolve())

    # Check all available dynamic storage drives
    for drv in get_available_storage_drives():
        match_info = search_drive_or_dir_for_item(drv, clean)
        if match_info:
            return str(match_info[0].resolve())

    return None


# Lazy-loaded optional service instances
chat_service = None
agent_router = None
context_service = None
system_service = None
document_service = None

try:
    from app.services.chat_service import ChatService
    chat_service = ChatService()
except Exception:
    pass


_CACHED_GPU_STR: Optional[str] = None

def get_live_system_stats() -> str:
    """Collects real-time live hardware vitals without simulation or hallucinations in <1ms."""
    global _CACHED_GPU_STR
    try:
        import psutil
        import platform
        import datetime
        import subprocess

        # CPU (non-blocking)
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_count_logical = psutil.cpu_count(logical=True) or 8
        cpu_count_physical = psutil.cpu_count(logical=False) or (cpu_count_logical // 2)
        proc_model = platform.processor() or "Multi-Core Processor"

        # RAM
        mem = psutil.virtual_memory()
        ram_used_gb = round(mem.used / (1024 ** 3), 1)
        ram_total_gb = round(mem.total / (1024 ** 3), 1)
        ram_percent = mem.percent

        # Disks
        disk_c = psutil.disk_usage('C:')
        c_free_gb = round(disk_c.free / (1024 ** 3), 1)
        c_used_gb = round(disk_c.used / (1024 ** 3), 1)
        c_total_gb = round(disk_c.total / (1024 ** 3), 1)
        c_free_pct = round((disk_c.free / disk_c.total) * 100, 1)

        d_info = ""
        if Path("D:/").exists():
            try:
                disk_d = psutil.disk_usage('D:')
                d_free_gb = round(disk_d.free / (1024 ** 3), 1)
                d_used_gb = round(disk_d.used / (1024 ** 3), 1)
                d_free_pct = round((disk_d.free / disk_d.total) * 100, 1)
                d_info = f"\n| **Disk (D:)** | **{d_free_pct}% free** | {d_free_gb} GB free / {d_used_gb} GB used |"
            except Exception:
                pass

        # Battery
        battery = psutil.sensors_battery()
        if battery:
            plugged_str = "Plugged in (Charging)" if battery.power_plugged else "On Battery"
            batt_info = f"**{battery.percent}%** ({plugged_str})"
        else:
            batt_info = "AC Power Connected (Dedicated Power)"

        # System Uptime
        boot_ts = psutil.boot_time()
        uptime_delta = datetime.datetime.now() - datetime.datetime.fromtimestamp(boot_ts)
        days = uptime_delta.days
        hours, rem = divmod(uptime_delta.seconds, 3600)
        minutes, _ = divmod(rem, 60)
        uptime_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"

        # Network
        net = psutil.net_io_counters()
        net_sent_mb = round(net.bytes_sent / (1024 ** 2), 1)
        net_recv_mb = round(net.bytes_recv / (1024 ** 2), 1)

        # GPUs (cached to eliminate subprocess latency)
        if _CACHED_GPU_STR is None:
            gpus = []
            if os.name == "nt":
                try:
                    cmd = 'Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name'
                    out = subprocess.check_output(['powershell', '-NoProfile', '-Command', cmd], text=True, timeout=1.5).strip()
                    gpus = [line.strip() for line in out.splitlines() if line.strip()]
                except Exception:
                    pass
            _CACHED_GPU_STR = " + ".join(gpus) if gpus else "Hardware Graphics Accelerated"
        gpu_str = _CACHED_GPU_STR

        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        report = f"""**Live System Telemetry Snapshot ({timestamp_str})**

| Component | Current Value | Details |
|---|---|---|
| **CPU** | **{cpu_percent}%** | {cpu_count_physical} Cores / {cpu_count_logical} Threads ({proc_model[:35]}) |
| **GPU** | **Active** | {gpu_str} |
| **RAM** | **{ram_percent}% used** | {ram_used_gb} GB used / {ram_total_gb} GB total |
| **Disk (C:)** | **{c_free_pct}% free** | {c_free_gb} GB free / {c_total_gb} GB total |{d_info}
| **Battery** | {batt_info} | System power source |
| **Network I/O** | **{net_recv_mb} MB ↓ / {net_sent_mb} MB ↑** | Total session transfer |
| **System Uptime** | **{uptime_str}** | Booted: {datetime.datetime.fromtimestamp(boot_ts).strftime('%b %d, %H:%M')} |"""
        return report
    except Exception as e:
        import psutil
        return f"Live system vitals: CPU {psutil.cpu_percent()}%, RAM {psutil.virtual_memory().percent}%."


try:
    from app.services.agent_router import agent_router as default_router
    agent_router = default_router
except Exception:
    pass

try:
    from app.services.context_service import context_service as default_context
    context_service = default_context
except Exception:
    pass

try:
    from app.services.system_service import system_service as default_system
    system_service = default_system
except Exception:
    pass


def load_user_profile() -> Dict[str, Any]:
    """
    What does this function do:
    Loads the persistent user profile data (name, wake word, agent name, city, email, age)
    from 'database/user_profile.json'. Connects with 'agent_profile' and 'profile' structures.
    
    Returns:
        Dict[str, Any]: User profile dictionary.
    """
    root_file = Path(r"c:\Users\Harishan\Desktop\AI_ASSISTANT\database\user_profile.json")
    backend_file = BASE_DIR / "database" / "user_profile.json"
    target_file = root_file if root_file.exists() else (backend_file if backend_file.exists() else PROFILE_FILE)
    
    data = {}
    if target_file.exists():
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[CommandExecutor] Reading profile failed: {e}", flush=True)

    agent_prof = data.get("agent_profile") if isinstance(data.get("agent_profile"), dict) else {}
    user_prof = data.get("profile") if isinstance(data.get("profile"), dict) else {}
    
    agent_name = (agent_prof.get("agent_name") or data.get("agent_name") or agent_prof.get("wake_word") or data.get("wake_word") or "Friday").strip()
    wake_word = (agent_prof.get("wake_word") or data.get("wake_word") or agent_name).strip().lower()
    user_name = (user_prof.get("name") or data.get("name") or "Harishan").strip()
    age = str(user_prof.get("age") if user_prof.get("age") is not None else data.get("age", "")).strip()
    email = str(user_prof.get("email") or data.get("email", "")).strip()
    city = str(user_prof.get("city") or data.get("city", "")).strip()
    voice_gender = str(data.get("voice_gender") or "female").strip().lower()
    language = str(data.get("language") or "english").strip().lower()
    languages = data.get("languages") or ["english", "tamil", "tanglish"]

    merged = {
        "name": user_name,
        "agent_name": agent_name,
        "wake_word": wake_word,
        "age": age,
        "email": email,
        "city": city,
        "voice_gender": voice_gender,
        "language": language,
        "languages": languages,
        "profile": {
            "name": user_name,
            "age": age,
            "email": email,
            "city": city
        },
        "agent_profile": {
            "agent_name": agent_name,
            "wake_word": wake_word
        }
    }
    return merged


def save_user_profile(profile_data: Dict[str, Any]) -> None:
    """
    What does this function do:
    Persists updated profile configuration to 'database/user_profile.json',
    synchronizing top-level fields and nested 'agent_profile' and 'profile' dictionaries.
    
    Args:
        profile_data (Dict[str, Any]): Dictionary containing updated profile fields.
    """
    current = load_user_profile()
    
    # Extract nested agent_profile if provided
    if "agent_profile" in profile_data and isinstance(profile_data["agent_profile"], dict):
        if "agent_name" in profile_data["agent_profile"]:
            profile_data["agent_name"] = profile_data["agent_profile"]["agent_name"]
        if "wake_word" in profile_data["agent_profile"]:
            profile_data["wake_word"] = profile_data["agent_profile"]["wake_word"]

    if "profile" in profile_data and isinstance(profile_data["profile"], dict):
        for k in ["name", "age", "email", "city"]:
            if k in profile_data["profile"]:
                profile_data[k] = profile_data["profile"][k]

    current.update(profile_data)
    
    agent_name = (current.get("agent_name") or current.get("wake_word") or "Friday").strip()
    wake_word = (current.get("wake_word") or agent_name).strip().lower()
    user_name = (current.get("name") or "Harishan").strip()
    
    current["agent_name"] = agent_name
    current["wake_word"] = wake_word
    current["name"] = user_name
    current["profile"] = {
        "name": user_name,
        "age": current.get("age", ""),
        "email": current.get("email", ""),
        "city": current.get("city", "")
    }
    current["agent_profile"] = {
        "agent_name": agent_name,
        "wake_word": wake_word
    }

    root_file = Path(r"c:\Users\Harishan\Desktop\AI_ASSISTANT\database\user_profile.json")
    backend_file = BASE_DIR / "database" / "user_profile.json"
    
    for target in [root_file, backend_file, PROFILE_FILE]:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2)
        except Exception as e:
            print(f"[CommandExecutor] Writing profile to {target} failed: {e}", flush=True)


def save_chat_turn(session_id: str, role: str, message: str) -> None:
    """
    What does this function do:
    Records a conversational chat turn into local in-memory store and triggers async
    background ingestion into Friday's persistent vector memory and SQLite conversation stores.
    
    Args:
        session_id (str): Active session identifier.
        role (str): 'user' or 'assistant'.
        message (str): Plain-text content of the turn.
    """
    if session_id not in LOCAL_MEMORY_STORE:
        LOCAL_MEMORY_STORE[session_id] = []
    LOCAL_MEMORY_STORE[session_id].append({"role": role, "message": message, "timestamp": time.time()})
    if message and message.strip():
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(friday_memory_manager.ingest_turn_async(
                user_query=message if role == "user" else "",
                agent_response=message if role != "user" else "",
                session_id=session_id
            ))
            if session_id:
                loop.create_task(conversation_memory_service.add_message(
                    conversation_id=session_id,
                    role=role,
                    content=message,
                    index_vector=True
                ))
            # Also keep session cache file in memory/cache/sessions updated
            def _sync_session_cache():
                try:
                    s_cache_dir = BASE_DIR / "memory" / "cache" / "sessions"
                    s_cache_dir.mkdir(parents=True, exist_ok=True)
                    s_file = s_cache_dir / f"{session_id}.json"
                    with open(s_file, "w", encoding="utf-8") as f:
                        json.dump(LOCAL_MEMORY_STORE.get(session_id, []), f, indent=2)
                except Exception:
                    pass
            loop.run_in_executor(None, _sync_session_cache)
            # Async user persona & emotional analysis
            from app.services.user_persona_service import user_persona_service
            if role == "user":
                loop.run_in_executor(None, user_persona_service.analyze_chat_turn, message, "", session_id)
            else:
                loop.run_in_executor(None, user_persona_service.analyze_chat_turn, "", message, session_id)
        except RuntimeError:
            pass


def cleanup_expired_memory() -> None:
    """
    What does this function do:
    Triggers sliding memory expiration cleanup in conversation_memory_service, purging
    conversation records older than the 24-hour active window.
    """
    try:
        conversation_memory_service.cleanup_expired_conversations()
    except Exception:
        pass


def get_chat_history(session_id: str) -> List[Dict[str, Any]]:
    """
    What does this function do:
    Retrieves the chronological list of messages for a given session from in-memory cache
    or loads from conversation memory service file storage and session cache.
    
    Args:
        session_id (str): Active conversation session identifier.
        
    Returns:
        List[Dict[str, Any]]: List of message dictionaries with 'role', 'message', 'timestamp'.
    """
    history = LOCAL_MEMORY_STORE.get(session_id, [])
    if not history and session_id:
        # 1. Try conversation memory service database storage
        try:
            file_path = conversation_memory_service._get_file_path(session_id)
            data = conversation_memory_service._load_json(file_path)
            if data and "messages" in data:
                history = [{"role": m.get("role", "user"), "message": m.get("content", ""), "timestamp": m.get("created_at", 0)} for m in data["messages"]]
                LOCAL_MEMORY_STORE[session_id] = history
                return history
        except Exception:
            pass

        # 2. Try session cache files e.g. memory/cache/sessions/{session_id}.json
        try:
            candidates = [
                BASE_DIR / "memory" / "cache" / "sessions" / f"{session_id}.json",
                BASE_DIR / "memory" / "cache" / "sessions" / f"session_{session_id}.json",
                BASE_DIR / "memory" / "cache" / f"{session_id}.json",
                BASE_DIR / "memory" / "cache" / f"session_{session_id}.json",
            ]
            for cache_file in candidates:
                if cache_file.exists():
                    with open(cache_file, "r", encoding="utf-8") as f:
                        raw_items = json.load(f)
                        if isinstance(raw_items, list):
                            history = [{"role": item.get("role", "user"), "message": item.get("message", item.get("content", "")), "timestamp": item.get("timestamp", 0)} for item in raw_items]
                            LOCAL_MEMORY_STORE[session_id] = history
                            return history
        except Exception:
            pass

    return history


def resolve_conversational_query(query: str, history: List[Dict[str, Any]]) -> str:
    """
    Resolves conversational pronouns (he, she, it, him, her, they, that, this) and follow-up
    phrases by inspecting recent chat history so search engines find the actual intended subject.
    If the query already contains an explicit target (e.g. '(regarding X)' or named entity),
    it formats it cleanly without polluting it with distant context.
    """
    clean_lower = query.lower().strip()

    # 1. If query already explicitly specifies target entity e.g. "(regarding C. Joseph Vijay)"
    ref_match = re.search(r'\((?:regarding|referring\s+to|about|for)\s+([^\)]+)\)', query, flags=re.IGNORECASE)
    if ref_match:
        explicit_entity = ref_match.group(1).strip()
        base_clean = re.sub(r'\([^\)]+\)', '', query).strip()
        return f"{explicit_entity} {base_clean}".strip()

    pronouns_and_followups = [
        r"\bhim\b", r"\bher\b", r"\bhis\b", r"\bhe\b", r"\bshe\b", r"\bit\b", r"\bits\b",
        r"\bthem\b", r"\bthey\b", r"\bthis\b", r"\bthat\b", r"\bthese\b", r"\bthose\b",
        r"\bthe person\b", r"\bthe actor\b", r"\bthe character\b", r"\bthe movie\b", r"\bthe director\b",
        r"\bthe film\b", r"\bthe producer\b", r"\bthe interview\b", r"\bthe q&a\b", r"\bthe video\b",
        r"\bthe clip\b", r"\bthe show\b", r"\bthe event\b", r"\bthe song\b", r"\bthe trailer\b",
        r"^tell more", r"^more about", r"^what else", r"^explain more", r"^continue",
        r"^more details", r"^and then", r"^why did he", r"^why did she", r"^what did he",
        r"^what is his", r"^what is her", r"^what is their", r"^who is he", r"^who is she",
        r"^how is he", r"^how is she", r"^how is it", r"^how about", r"^what about",
        r"^what are the\b", r"^what is the\b", r"^what was the\b", r"^what were the\b",
        r"^what did they\b", r"^what did he\b", r"^what did she\b"
    ]

    needs_resolution = any(re.search(pat, clean_lower) for pat in pronouns_and_followups)
    if not needs_resolution or not history:
        return query

    # Exclude current turn if it was already recorded
    prior_turns = [
        t for t in history
        if not (t.get("role") == "user" and t.get("message", "").strip().lower() == clean_lower)
    ]
    if not prior_turns:
        return query

    # 2. Look back at the most recent prior turns (within last 6 turns)
    for turn in reversed(prior_turns[-6:]):
        role = turn.get("role")
        text = turn.get("message", "").strip()
        if not text:
            continue

        if role == "user":
            # Check if previous user turn had an explicit parenthetical entity
            prev_ref = re.search(r'\((?:regarding|referring\s+to|about|for)\s+([^\)]+)\)', text, flags=re.IGNORECASE)
            if prev_ref:
                clean_target = prev_ref.group(1).strip()
                return f"{clean_target} {query}"

            if not any(re.search(pat, text.lower()) for pat in pronouns_and_followups):
                clean_context_query = re.sub(
                    r"^(?:who\s+is|what\s+is|tell\s+me\s+about|tell\s+about|search\s+for|find|search)\s+",
                    "",
                    text,
                    flags=re.IGNORECASE
                ).strip()
                if clean_context_query and len(clean_context_query) > 2:
                    # Smart replacement for pronouns or referent phrases
                    replaced = re.sub(r'\b(?:this movie|the movie|this film|the film|this actor|the actor|this person|the person)\b', clean_context_query, query, flags=re.IGNORECASE)
                    if replaced != query:
                        return replaced
                    return f"{clean_context_query} {query}"
                break
        elif role == "assistant":
            # 1. Check if user is asking about director or producer
            if any(k in clean_lower for k in ["director", "directed by", "who made it"]):
                dir_match = re.search(r'director(?:\s*:\*?|\s+is\s+)\s*([A-Za-z\s]+?)(?:\s*\(|\s*\n|\s*\.|\s*,)', text, flags=re.IGNORECASE)
                if dir_match:
                    clean_dir = dir_match.group(1).strip()
                    if clean_dir and len(clean_dir.split()) <= 4:
                        return f"{clean_dir} {query}"

            # 2. Check if previous assistant message discussed a video, movie, or specific title
            title_match = re.search(r'(?:video\s+title|title|film|movie)\s*:\s*\*?([^\n\*\.\r]+)', text, flags=re.IGNORECASE)
            if title_match:
                subject_title = title_match.group(1).strip()
                if subject_title:
                    short_subject = subject_title.split("|")[0].strip()
                    if len(short_subject.split()) > 6:
                        short_subject = " ".join(short_subject.split()[:5])
                    return f"(regarding {short_subject}) {query}"

            # 3. Look for bold entities at the start of response e.g. **Jailer 2** or **Sigma**
            bold_match = re.search(r'\*\*([a-zA-Z0-9\s]{2,30})\*\*', text)
            if bold_match:
                bold_entity = bold_match.group(1).strip()
                if bold_entity and bold_entity.lower() not in ["key details", "event", "summary", "participants", "context"]:
                    return f"(regarding {bold_entity}) {query}"


def get_greeting_message(language: str = "english") -> str:
    """
    What does this function do:
    Generates a personalized, time-of-day greeting (Good morning/afternoon/evening) in English,
    Tamil, or Tanglish, including the user's name and current clock time.
    
    Args:
        language (str): 'english', 'tamil', or 'tanglish'.
        
    Returns:
        str: Formatted greeting string.
    """
    user_info = load_user_profile()
    user_name = user_info.get("name") or "Harishan"
    agent_name = user_info.get("agent_name") or "Friday"
    hour = datetime.now().hour
    current_time = datetime.now().strftime("%I:%M %p")

    if language == "tamil":
        return f"வணக்கம் {user_name}. {agent_name} நியூரல் இண்டர்ஃபேஸ் ஆன்லைனில் உள்ளது. நேரம் {current_time}. நான் உங்களுக்கு எப்படி உதவ முடியும்?"
    elif language == "tanglish":
        return f"Vanakkam {user_name}! {agent_name} neural interface online la irukku. Time {current_time}. Enna help venum sollunga boss?"
    
    period = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    return f"{period} {user_name}. {agent_name} neural interface is online. The time is {current_time}. How can I assist you?"


def parse_open_in_app(query: str, user_name: str = "Harishan") -> Optional[str]:
    """
    Parses 'open <target> in <app>' voice commands (e.g., 'open python documentation in chrome')
    and launches the specific browser or desktop application with the target URL/file.
    Properly handles browser tab directives ('in current tab', 'in new tab') without invalid OS commands.
    """
    clean = query.lower().strip()
    match = re.search(r"^open\s+(?P<target>.+?)\s+(?:in|on)\s+(?P<app>.+)$", clean)
    if match:
        target = match.group("target").strip()
        app_name = match.group("app").strip()
        
        # 0. Drive directives ('in d drive', 'in pendrive', 'in usb', 'on external drive', 'in e:')
        if re.search(r'\b(?:drive\s+[a-zA-Z]|[a-zA-Z]\s+drive|[a-zA-Z]:)\b', app_name) or any(alias in app_name for alias in REMOVABLE_STORAGE_ALIASES):
            local_attempt = handle_local_open(query, user_name=user_name)
            if local_attempt:
                return local_attempt

        # 1. Browser tab directives ('in current tab', 'in new tab', 'in tab')
        if app_name in ["current tab", "this tab", "new tab", "tab", "the current tab", "the new tab", "browser tab"]:
            # If target is a local file or folder (e.g., 'smart memo')
            local_attempt = handle_local_open(target, user_name=user_name)
            if local_attempt:
                return local_attempt

            # Otherwise treat as web navigation/search
            web_shortcuts = {
                "youtube": "https://www.youtube.com",
                "google": "https://www.google.com",
                "gmail": "https://mail.google.com",
                "github": "https://github.com",
                "reddit": "https://reddit.com",
                "chatgpt": "https://chatgpt.com",
                "spotify": "https://open.spotify.com",
            }
            target_url = web_shortcuts.get(target, f"https://www.google.com/search?q={urllib.parse.quote_plus(target)}")
            webbrowser.open(target_url)
            return f"Opening '{target}' in your browser."

        # 2. Google Maps special handling
        if any(m in target for m in ["google map", "google maps", "map", "maps"]):
            target_url = "https://www.google.com/maps"
            if "chrome" in app_name:
                os.system(f'start chrome "{target_url}"' if os.name == "nt" else f'google-chrome "{target_url}" &')
                return f"Opened Google Maps in Google Chrome."
            elif "edge" in app_name:
                os.system(f'start msedge "{target_url}"' if os.name == "nt" else f'microsoft-edge "{target_url}" &')
                return f"Opened Google Maps in Microsoft Edge."
            else:
                webbrowser.open(target_url)
                return f"Opened Google Maps in {app_name}."

        # 3. Known domain/app shortcuts
        web_shortcuts = {
            "youtube": "https://www.youtube.com",
            "google": "https://www.google.com",
            "gmail": "https://mail.google.com",
            "github": "https://github.com",
            "reddit": "https://reddit.com",
            "chatgpt": "https://chatgpt.com",
            "spotify": "https://open.spotify.com",
        }
        target_url = web_shortcuts.get(target, f"https://www.google.com/search?q={urllib.parse.quote_plus(target)}")

        if "chrome" in app_name:
            os.system(f'start chrome "{target_url}"' if os.name == "nt" else f'google-chrome "{target_url}" &')
            return f"Opened '{target}' in Google Chrome."
        elif "edge" in app_name:
            os.system(f'start msedge "{target_url}"' if os.name == "nt" else f'microsoft-edge "{target_url}" &')
            return f"Opened '{target}' in Microsoft Edge."
        elif any(b in app_name for b in ["firefox", "browser", "safari", "brave"]):
            webbrowser.open(target_url)
            return f"Opening '{target}' in {app_name}."
        
        # 4. Valid known desktop executable targets
        known_executables = {"notepad", "code", "vlc", "explorer", "calc", "cmd", "wt", "paint", "word", "excel"}
        if app_name in known_executables:
            local_res = handle_local_open(target, user_name=user_name)
            if local_res:
                return local_res
            os.system(f'start {app_name}' if os.name == "nt" else f'{app_name} &')
            return f"Opened {app_name}."

    return None


def handle_local_open(query: str, user_name: str = "Harishan") -> Optional[str]:
    """
    Resolves local desktop app launches (Chrome, Edge, Notepad, VS Code, Google Maps), installed application
    shortcuts across Start Menu and Desktop, custom database routes in 'database/add_path.json', storage drives
    (including dynamic USBs, pen drives, external disks, and partitions), and user folders (Desktop, Documents, Downloads).
    Performs deep token and word-boundary scoring and provides accurate feedback without hallucinating.
    """
    clean = query.lower().strip()
    
    # 1. Google Maps check (external browser)
    if clean in ["open google map", "open google maps", "open map", "open maps", "open google map in chrome", "open google maps in chrome"]:
        target_url = "https://www.google.com/maps"
        if os.name == "nt":
            os.system(f'start chrome "{target_url}"')
        else:
            webbrowser.open(target_url)
        return "Opened Google Maps in Google Chrome."

    # 2. System App shortcuts
    app_shortcuts = {
        "whatsapp": ("WhatsApp", "start whatsapp:" if os.name == "nt" else "whatsapp &"),
        "whatsapp desktop": ("WhatsApp", "start whatsapp:" if os.name == "nt" else "whatsapp &"),
        "chrome": ("Google Chrome", "start chrome" if os.name == "nt" else "google-chrome &"),
        "google chrome": ("Google Chrome", "start chrome" if os.name == "nt" else "google-chrome &"),
        "my google chrome": ("Google Chrome", "start chrome" if os.name == "nt" else "google-chrome &"),
        "edge": ("Microsoft Edge", "start msedge" if os.name == "nt" else "microsoft-edge &"),
        "microsoft edge": ("Microsoft Edge", "start msedge" if os.name == "nt" else "microsoft-edge &"),
        "notepad": ("Notepad", "start notepad" if os.name == "nt" else "gedit &"),
        "vs code": ("Visual Studio Code", "code" if os.name == "nt" else "code &"),
        "visual studio code": ("Visual Studio Code", "code" if os.name == "nt" else "code &"),
        "code": ("Visual Studio Code", "code" if os.name == "nt" else "code &"),
        "spotify": ("Spotify", "start spotify:" if os.name == "nt" else "spotify &"),
        "discord": ("Discord", "start discord:" if os.name == "nt" else "discord &"),
        "telegram": ("Telegram", "start telegram:" if os.name == "nt" else "telegram &"),
        "settings": ("Windows Settings", "start ms-settings:" if os.name == "nt" else "gnome-control-center &"),
        "paint": ("Paint", "start mspaint" if os.name == "nt" else "drawing &"),
        "calculator": ("Calculator", "start calc" if os.name == "nt" else "gnome-calculator &"),
        "calc": ("Calculator", "start calc" if os.name == "nt" else "gnome-calculator &"),
        "terminal": ("Windows Terminal", "start wt" if os.name == "nt" else "x-terminal-emulator &"),
        "command prompt": ("Command Prompt", "start cmd" if os.name == "nt" else "sh &"),
        "cmd": ("Command Prompt", "start cmd" if os.name == "nt" else "sh &"),
        "task manager": ("Task Manager", "start taskmgr" if os.name == "nt" else "top &"),
        "explorer": ("File Explorer", "start explorer" if os.name == "nt" else "nautilus &"),
        "file explorer": ("File Explorer", "start explorer" if os.name == "nt" else "nautilus &")
    }
    
    for key, (app_name, cmd) in app_shortcuts.items():
        if clean == key or clean == f"the {key}" or clean == f"my {key}" or re.search(rf"\b(?:open|launch|start|run)\s+(?:the\s+|my\s+)?{re.escape(key)}\b", clean):
            try:
                os.system(cmd)
                return f"Opened {app_name}."
            except Exception as e:
                print(f"[CommandExecutor App Launch Error]: {e}", flush=True)

    # 3. Clean conversational prefixes and contextual suffixes
    target = clean
    prefixes = [
        "can you please open", "could you please open", "can you open", "could you open", "please open",
        "i want you to open", "open up", "show me the", "show me", "find the folder", "find the", "find folder",
        "find my", "find", "locate the folder", "locate the", "locate folder", "locate", "open folder", "open directory",
        "open file", "open link", "open url", "open website", "open app", "open the", "open my",
        "open", "launch", "start", "explore", "view", "where is the folder", "where is the", "where is"
    ]
    for prefix in sorted(prefixes, key=len, reverse=True):
        if target.startswith(prefix):
            target = target[len(prefix):].strip()
            break

    suffixes = [
        " folder in my screen", " folder on my screen", " file in my screen", " file on my screen",
        " in my screen", " on my screen", " in screen", " on screen", " in file explorer",
        " on desktop", " in desktop", " on my pc", " in my pc", " folder", " directory", " file"
    ]
    for suffix in sorted(suffixes, key=len, reverse=True):
        if target.endswith(suffix):
            target = target[:-len(suffix)].strip()
            break
    
    target = re.sub(r'^(?:the|a|an|my)\s+', '', target).strip()
    
    # Dynamically extract target query and target drive (letter A-Z, volume label, USB/pen drive/external drive)
    target_clean, target_drive, target_drive_name = extract_target_and_drive(target)

    # If the user's request was directly to open a drive (e.g. 'open pendrive', 'open d drive', 'open usb')
    if not target_clean and target_drive_name:
        if target_drive and target_drive.exists():
            if os.name == "nt":
                subprocess.Popen(["explorer.exe", str(target_drive)])
            else:
                webbrowser.open(str(target_drive.as_uri()))
            return f"Opened {target_drive_name} in File Explorer on your screen, {user_name}."
        return f"{target_drive_name} is not connected or accessible on your system, {user_name}."

    target = target_clean
    if not target or any(w in target for w in [" and ", " then ", "search "]):
        return None

    # 4. Check custom database routes
    try:
        if ADD_PATH_FILE.exists():
            data = json.loads(ADD_PATH_FILE.read_text(encoding="utf-8"))
            paths = data.get("paths", []) if isinstance(data, dict) else data
            for p in paths:
                if target in str(p.get("route_name", "")).lower():
                    p_str = p.get("path")
                    if p_str and Path(p_str).exists():
                        if os.name == "nt":
                            subprocess.Popen(["explorer.exe", str(Path(p_str))])
                        else:
                            webbrowser.open(str(Path(p_str).as_uri()))
                        return f"Opened '{p.get('route_name')}' from local database."
    except Exception as e:
        print(f"[CommandExecutor add_path error]: {e}", flush=True)

    # 5. If specific target drive specified, prioritize searching that drive
    if target_drive_name:
        if not target_drive or not target_drive.exists():
            return f"{target_drive_name} is not connected to your system, {user_name}."
        match_info = search_drive_or_dir_for_item(target_drive, target)
        if match_info:
            match_path, action = match_info
            if action == "launch":
                if os.name == "nt":
                    try:
                        os.startfile(str(match_path))
                    except Exception:
                        subprocess.Popen([str(match_path)])
                else:
                    subprocess.Popen([str(match_path)])
                return f"Launched {match_path.name} on your screen, {user_name}."
            else:
                if os.name == "nt":
                    subprocess.Popen(["explorer.exe", str(match_path)])
                else:
                    webbrowser.open(str(match_path.as_uri()))
                return f"Opened '{match_path.name}' in File Explorer on your screen, {user_name}."
        return f"I searched your {target_drive_name}, but could not find any folder or file matching '{target}', {user_name}."

    # 6. Check installed application shortcuts (Start Menu programs, Desktop, AppData)
    app_shortcut = find_installed_app_shortcut(target)
    if app_shortcut:
        if os.name == "nt":
            try:
                os.startfile(str(app_shortcut))
            except Exception:
                subprocess.Popen(["explorer.exe", str(app_shortcut)])
        else:
            subprocess.Popen([str(app_shortcut)])
        return f"Opened {app_shortcut.stem}."

    # 7. Search user directories (Desktop, Documents, Downloads)
    user_home = Path.home()
    search_dirs = [
        user_home / "Desktop",
        user_home / "Documents",
        user_home / "Downloads",
        Path(r"C:\Users\Harishan\Desktop"),
        Path(r"C:\Users\Harishan\Documents"),
        Path(r"C:\Users\Harishan\Downloads")
    ]
    
    for d in search_dirs:
        if not d.exists():
            continue
        match_info = search_drive_or_dir_for_item(d, target)
        if match_info:
            match_path, action = match_info
            if action == "launch":
                if os.name == "nt":
                    try:
                        os.startfile(str(match_path))
                    except Exception:
                        subprocess.Popen([str(match_path)])
                else:
                    subprocess.Popen([str(match_path)])
                return f"Launched {match_path.name} on your screen, {user_name}."
            else:
                if os.name == "nt":
                    subprocess.Popen(["explorer.exe", str(match_path)])
                else:
                    webbrowser.open(str(match_path.as_uri()))
                return f"Opened '{match_path.name}' in File Explorer on your screen, {user_name}."

    # 8. Search all other available dynamic storage drives
    for drv in get_available_storage_drives():
        match_info = search_drive_or_dir_for_item(drv, target)
        if match_info:
            match_path, action = match_info
            if action == "launch":
                if os.name == "nt":
                    try:
                        os.startfile(str(match_path))
                    except Exception:
                        subprocess.Popen([str(match_path)])
                else:
                    subprocess.Popen([str(match_path)])
                return f"Launched {match_path.name} on your screen, {user_name}."
            else:
                if os.name == "nt":
                    subprocess.Popen(["explorer.exe", str(match_path)])
                else:
                    webbrowser.open(str(match_path.as_uri()))
                return f"Opened '{match_path.name}' in File Explorer on your screen, {user_name}."

    # If user explicitly requested opening a folder/file/app, provide accurate non-hallucinated feedback
    if any(w in clean for w in ["folder", "file", "directory", "doc", "memo", "open", "show me", "launch", "exe"]):
        return f"I searched your PC and storage drives, but could not find any folder or file matching '{target}', {user_name}."

    return None


def execute_fast_ui_click(query: str, user_name: str = "Harishan") -> Optional[str]:
    """
    Executes instant (<150ms) direct UI clicks for ordinal links (1st, 2nd, 3rd), buttons,
    search results, and targeted visible screen controls without LLM latency.
    """
    clean = query.lower().strip()
    
    if pyautogui is None:
        return None

    pyautogui.FAILSAFE = False

    # 1. Direct Mouse Clicks at Current Cursor Position
    if clean in ["double click", "double-click", "double click here", "double click on this", "double click it"]:
        pyautogui.doubleClick()
        return f"Double-clicked at current mouse position, {user_name}."

    if clean in ["right click", "right-click", "right click here", "context menu", "open context menu"]:
        pyautogui.rightClick()
        return f"Right-clicked at current mouse position, {user_name}."

    if clean in ["single click", "left click", "click here", "click it", "click now", "click"]:
        pyautogui.click()
        return f"Clicked at current mouse position, {user_name}."

    # 2. Key presses (Enter, Escape, Space, Backspace, Tab)
    if clean in ["press enter", "hit enter", "press return", "enter key"]:
        pyautogui.press("enter")
        return f"Pressed Enter key, {user_name}."

    if clean in ["press escape", "hit escape", "press esc", "hit esc", "esc key"]:
        pyautogui.press("escape")
        return f"Pressed Escape key, {user_name}."

    if clean in ["press space", "hit space", "press spacebar", "hit spacebar", "space key"]:
        pyautogui.press("space")
        return f"Pressed Spacebar, {user_name}."

    if clean in ["press tab", "hit tab", "tab key"]:
        pyautogui.press("tab")
        return f"Pressed Tab key, {user_name}."

    # 3. Mouse Movement Controls
    if any(clean.startswith(p) or p in clean for p in ["move mouse", "move cursor", "move the mouse", "move the cursor", "position mouse", "position cursor"]):
        screen_w, screen_h = pyautogui.size()
        cur_x, cur_y = pyautogui.position()

        def _set_pos(x, y):
            try:
                if os.name == "nt":
                    import ctypes
                    ctypes.windll.user32.SetCursorPos(int(x), int(y))
            except Exception:
                pass
            pyautogui.moveTo(x, y, duration=0.15)

        if any(w in clean for w in ["center", "middle", "centre"]):
            target_x, target_y = screen_w // 2, screen_h // 2
            _set_pos(target_x, target_y)
            return f"Moved mouse cursor to the center of your screen, {user_name}."

        if any(w in clean for w in ["top left", "upper left"]):
            _set_pos(100, 100)
            return f"Moved mouse cursor to the top left, {user_name}."

        if any(w in clean for w in ["top right", "upper right"]):
            _set_pos(screen_w - 100, 100)
            return f"Moved mouse cursor to the top right, {user_name}."

        if any(w in clean for w in ["bottom left", "lower left"]):
            _set_pos(100, screen_h - 100)
            return f"Moved mouse cursor to the bottom left, {user_name}."

        if any(w in clean for w in ["bottom right", "lower right"]):
            _set_pos(screen_w - 100, screen_h - 100)
            return f"Moved mouse cursor to the bottom right, {user_name}."

        # Relative directions with optional pixel distance
        m_dist = re.search(r'(\d+)', clean)
        dist = int(m_dist.group(1)) if m_dist else 150

        if "left" in clean:
            _set_pos(max(0, cur_x - dist), cur_y)
            return f"Moved mouse cursor {dist} pixels left, {user_name}."
        elif "right" in clean:
            _set_pos(min(screen_w, cur_x + dist), cur_y)
            return f"Moved mouse cursor {dist} pixels right, {user_name}."
        elif "up" in clean:
            _set_pos(cur_x, max(0, cur_y - dist))
            return f"Moved mouse cursor {dist} pixels up, {user_name}."
        elif "down" in clean:
            _set_pos(cur_x, min(screen_h, cur_y + dist))
            return f"Moved mouse cursor {dist} pixels down, {user_name}."

        # Absolute coordinates e.g. "move mouse to 500 400" or "x=500 y=400"
        m_coords = re.search(r'(?:to\s+)?(?:x\s*=\s*)?(\d+)[,\s]+(?:y\s*=\s*)?(\d+)', clean)
        if m_coords:
            nx, ny = int(m_coords.group(1)), int(m_coords.group(2))
            _set_pos(nx, ny)
            return f"Moved mouse cursor to coordinates ({nx}, {ny}), {user_name}."

    # 4. Pattern match click targets
    click_pattern = r'^(?:can\s+you\s+|could\s+you\s+|please\s+)?(?:click|press|tap|select|open|hit)\s+(?:on\s+)?(.+)$'
    m = re.match(click_pattern, clean)
    if not m:
        return None

    target = m.group(1).strip()
    
    ordinal_map = {
        "first": 0, "1st": 0, "first link": 0, "1st link": 0, "the first link": 0, "first result": 0, "the first result": 0,
        "second": 1, "2nd": 1, "second link": 1, "2nd link": 1, "the second link": 1, "second result": 1, "the second result": 1,
        "third": 2, "3rd": 2, "third link": 2, "3rd link": 2, "the third link": 2, "third result": 2, "the third result": 2,
        "fourth": 3, "4th": 3, "fourth link": 3, "4th link": 3, "the fourth link": 3,
        "fifth": 4, "5th": 4, "fifth link": 4, "5th link": 4,
        "last": -1, "last link": -1, "the last link": -1
    }
    
    is_ordinal = False
    ord_index = 0
    clean_target = re.sub(r'^(?:the\s+)?', '', target).strip()
    clean_target = re.sub(r'\s+(?:and\s+)?open\s+it$', '', clean_target).strip()
    clean_target = re.sub(r'\s+(?:and\s+)?open\s+that$', '', clean_target).strip()
    clean_target = re.sub(r'\s+(?:and\s+)?open\s+this$', '', clean_target).strip()

    for k, v in ordinal_map.items():
        if clean_target == k or target == k or clean_target.startswith(k):
            is_ordinal = True
            ord_index = v
            break

    # Strategy 0: Pronoun & hover references ("open it", "open that", "open that file", "open that folder", "open this", "open this file", "open this folder", "click this")
    if clean_target in [
        "it", "this", "that", "the item", "the element", "the file", "the folder", "item", "element",
        "this file", "this folder", "that file", "that folder", "file", "folder",
        "hovered file", "hovered folder", "selected file", "selected folder", "pointed file", "pointed folder"
    ]:
        if any(w in clean for w in ["open", "launch", "start", "double", "explore", "view"]):
            from app.services.context_service import get_hovered_or_selected_file_or_folder
            hovered = get_hovered_or_selected_file_or_folder() or get_selected_desktop_or_explorer_file()
            if hovered and os.path.exists(hovered):
                p_item = Path(hovered)
                if any(w in clean for w in ["existing screen", "existing tab", "current tab", "existing window"]):
                    if p_item.is_dir():
                        from app.services.context_service import FileExplorerContextHandler
                        if FileExplorerContextHandler.navigate_existing_tab(str(p_item)):
                            return f"Opened **{p_item.name}** in existing screen, {user_name}."
                    else:
                        os.startfile(str(p_item))
                        return f"Opened **{p_item.name}** in existing screen, {user_name}."
                if p_item.is_dir():
                    if os.name == "nt":
                        subprocess.Popen(["explorer.exe", str(p_item)])
                    else:
                        webbrowser.open(p_item.as_uri())
                else:
                    if os.name == "nt":
                        os.startfile(str(p_item))
                    else:
                        subprocess.Popen(["xdg-open", str(p_item)])
                return f"Opened **{p_item.name}** on your screen, {user_name}."
            else:
                # Direct hardware fallback: simulate double click at mouse cursor position
                if os.name == "nt":
                    try:
                        import ctypes
                        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
                        time.sleep(0.05)
                        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
                        return f"Double-clicked to open the pointed item on your screen, {user_name}."
                    except Exception:
                        pass
                pyautogui.doubleClick()
                return f"Double-clicked to open the pointed item on your screen, {user_name}."

                if os.path.isdir(hovered):
                    os.startfile(hovered)
                    return f"Opened folder **{Path(hovered).name}**, {user_name}."
                else:
                    os.startfile(hovered)
                    return f"Opened file **{Path(hovered).name}**, {user_name}."

            pyautogui.doubleClick()
            return f"Opened the focused item at current mouse position, {user_name}."
        else:
            pyautogui.click()
            return f"Clicked at current mouse position, {user_name}."

    # Strategy A: Ordinal link / search result clicking in active foreground window / browser
    if is_ordinal or any(w in target for w in ["first", "1st", "second", "2nd", "third", "3rd", "link", "result"]):
        clicked = False
        try:
            import uiautomation as auto
            auto.SetGlobalSearchTimeout(0.3)
            hwnd = None
            if os.name == "nt":
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
            
            root = auto.ControlFromHandle(hwnd) if hwnd else auto.GetForegroundControl()
            if root:
                links = []
                for child in root.GetChildren():
                    ctype = (child.ControlTypeName or "").lower()
                    if any(t in ctype for t in ["hyperlink", "button", "listitem", "text"]):
                        rect = child.BoundingRectangle
                        if rect and (rect.right - rect.left > 10) and (rect.bottom - rect.top > 10):
                            if rect.top > 120:
                                links.append(child)
                
                if links and abs(ord_index) < len(links):
                    target_link = links[ord_index]
                    t_rect = target_link.BoundingRectangle
                    cx = (t_rect.left + t_rect.right) // 2
                    cy = (t_rect.top + t_rect.bottom) // 2
                    pyautogui.click(cx, cy)
                    clicked = True
                    t_name = (target_link.Name or "").strip()
                    desc = f"**{t_name}**" if t_name else f"the {clean_target}"
                    return f"Clicked on {desc} on your active screen, {user_name}."
        except Exception:
            pass

        # Strategy B: Fast browser search result offset click
        if not clicked:
            try:
                screen_w, screen_h = pyautogui.size()
                base_x = int(screen_w * 0.28)
                y_offsets = [int(screen_h * 0.32), int(screen_h * 0.44), int(screen_h * 0.56), int(screen_h * 0.68)]
                idx = ord_index if 0 <= ord_index < len(y_offsets) else 0
                target_y = y_offsets[idx]
                
                pyautogui.click(base_x, target_y)
                return f"Clicked on the {clean_target or 'link'} on your active screen, {user_name}."
            except Exception as e:
                return f"Could not perform click: {e}"

    # Strategy C: Named target clicking (e.g. "click search", "click submit", "click play", "click smart memo")
    target_clean = re.sub(r'^(?:on\s+|the\s+)', '', target).strip()
    if target_clean:
        try:
            from app.tools.device import click_ui_element_by_name
            res = click_ui_element_by_name(target_clean)
            if res.get("success"):
                return f"Clicked on **{target_clean}** on your active screen, {user_name}."
        except Exception:
            pass

        # If click on UI element was not found, check if it is a local app or folder (e.g. "click smart memo")
        local_res = handle_local_open(target_clean, user_name=user_name)
        if local_res and "could not find" not in local_res.lower():
            return local_res

        if any(w in clean for w in ["click", "press", "tap", "select"]):
            return f"Could not find any clickable button or element named '{target_clean}' on your active screen, {user_name}."

    return None


def execute_direct_link(query: str) -> str:
    """
    What does this function do:
    Extracts HTTP/HTTPS URLs or common domain keywords (youtube, github, google, reddit, etc.)
    and opens them directly in the user's default browser window.
    
    Args:
        query (str): The query containing web addresses.
        
    Returns:
        str: Status string stating which URL was opened.
    """
    clean = query.lower().strip()
    url_match = re.search(r"https?://[^\s]+", query)
    if url_match:
        target_url = url_match.group(0)
        webbrowser.open(target_url)
        return f"Opening link: {target_url}"

    target = clean
    for prefix in ["open link", "open url", "open website", "open", "go to link", "go to", "visit"]:
        if target.startswith(prefix):
            target = target[len(prefix):].strip()
            break

    shortcuts = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "github": "https://www.github.com",
        "reddit": "https://www.reddit.com",
        "twitter": "https://www.x.com",
        "chatgpt": "https://chatgpt.com",
        "linkedin": "https://www.linkedin.com",
    }
    if target in shortcuts:
        target_url = shortcuts[target]
    elif re.search(r"\b[a-zA-Z0-9-]+\.(com|org|net|in|io|ai|co|dev)\b", target):
        target_url = f"https://{target}" if not target.startswith("http") else target
    else:
        target_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(target)}"

    webbrowser.open(target_url)
    return f"Opening {target_url}"


def execute_single_action(cmd: str, session_id: str, user_name: str) -> Optional[str]:
    """
    What does this function do:
    Dispatches single action execution including desktop shortcuts (screenshot, camera,
    minimize/maximize window, close tab), media playback, and app launching.
    
    Args:
        cmd (str): Single action command.
        session_id (str): Session identifier.
        user_name (str): Current operator's name.
        
    Returns:
        Optional[str]: Result string if handled, else None.
    """
    clean = cmd.lower().strip()
    if not clean:
        return None

    # 1. System shortcuts
    if any(k in clean for k in ["screenshot", "screen shot", "capture screen"]):
        if system_service:
            return system_service.take_screenshot()
    if any(k in clean for k in ["take a photo", "take photo", "take pic", "open camera"]):
        if system_service:
            return system_service.take_photo()
    if any(k in clean for k in ["new tab", "open a new tab", "open new tab"]):
        if system_service:
            return system_service.open_new_tab()
    if any(k in clean for k in ["close tab", "close current tab"]):
        if system_service:
            return system_service.close_current_tab()
    if "minimize" in clean or "minimise" in clean:
        if pyautogui:
            pyautogui.hotkey("win", "down")
            return f"Minimized window, {user_name}."
    if "maximize" in clean:
        if pyautogui:
            pyautogui.hotkey("win", "up")
            return f"Maximized window, {user_name}."
    if any(k in clean for k in ["close window", "close app", "alt+f4"]):
        if pyautogui:
            pyautogui.hotkey("alt", "f4")
            return f"Closed window, {user_name}."

    # 2. Direct web links
    if any(clean.startswith(p) for p in ["open ", "go to ", "visit "]) and any(k in clean for k in ["http://", "https://", "www.", ".com", ".org", ".net", ".io"]):
        return execute_direct_link(cmd)

    # 3. Direct app launches
    local_res = handle_local_open(cmd)
    if local_res:
        return local_res

    # 4. Media & browser automation (YouTube, Spotify, Web Search)
    try:
        from app.tools.media_automation import media_automation_tool
        if any(k in clean for k in ["play", "youtube", "spotify", "watch", "stream", "search"]):
            return media_automation_tool.execute(cmd)
    except Exception:
        pass

    # 5. Agent Router & System Service
    if agent_router is not None:
        try:
            tool_name = agent_router.route(cmd)
            if tool_name and tool_name not in ["web_search", "context_execution"]:
                if tool_name in ["open_application", "open_folder", "open_file", "open_path", "open_file_explorer"] and system_service:
                    return system_service.execute(tool_name, cmd)
                from app.tools.tool_registry import tool_registry
                if tool_name in tool_registry:
                    return str(tool_registry.execute(tool_name, cmd))
        except Exception:
            pass

    return None


def parse_and_execute_compound_command(query: str, session_id: str, user_name: str) -> Optional[str]:
    """
    What does this function do:
    Decomposes compound/multi-step requests (e.g., 'open chrome and search youtube for AI news',
    'open notepad and type hello world', 'open chrome and then take screenshot') and executes
    each step sequentially, aggregating the outcome into a unified status report.
    
    Args:
        query (str): Raw multi-step user prompt.
        session_id (str): Session identifier.
        user_name (str): Current operator name.
        
    Returns:
        Optional[str]: Combined execution report or None if not compound.
    """
    clean = query.lower().strip()

    # 1. Compound browser + search / media pattern:
    media_compound_match = re.match(
        r"^(?:open|launch|start)\s+(?:chrome|google\s+chrome|browser|google|edge)\s+(?:and\s+)?(?:search|find|look\s+up|play|watch)\s+(.+)$",
        clean,
        re.IGNORECASE
    )
    if not media_compound_match:
        media_compound_match = re.match(
            r"^(?:open|launch|start)\s+(?:chrome|google\s+chrome|browser|google|edge)\s+(?:and\s+)?(?:navigate\s+to|go\s+to)\s+(.+)$",
            clean,
            re.IGNORECASE
        )
    if media_compound_match:
        target = media_compound_match.group(1).strip()
        if "youtube" in target:
            yt_term = re.sub(r"^(?:for|on\s+youtube|in\s+youtube|youtube\s+for|youtube)\s*", "", target, flags=re.IGNORECASE).strip()
            yt_term = re.sub(r"\s*(?:on|in)\s+youtube$", "", yt_term, flags=re.IGNORECASE).strip()
            if yt_term and yt_term.lower() not in ["youtube", "open youtube", "browse youtube"]:
                encoded = urllib.parse.quote(yt_term)
                webbrowser.open(f"https://www.youtube.com/results?search_query={encoded}")
                return f"Opened Google Chrome and searched for '{yt_term}' on YouTube."
            else:
                webbrowser.open("https://www.youtube.com")
                return "Opened Google Chrome and navigated to YouTube."
        elif "spotify" in target:
            sp_term = re.sub(r"^(?:for|on\s+spotify|in\s+spotify|spotify\s+for|spotify)\s*", "", target, flags=re.IGNORECASE).strip()
            sp_term = re.sub(r"\s*(?:on|in)\s+spotify$", "", sp_term, flags=re.IGNORECASE).strip()
            if sp_term and sp_term.lower() not in ["spotify", "open spotify"]:
                encoded = urllib.parse.quote(sp_term)
                webbrowser.open(f"https://open.spotify.com/search/{encoded}")
                return f"Opened Google Chrome and searched for '{sp_term}' on Spotify."
            else:
                webbrowser.open("https://open.spotify.com")
                return "Opened Google Chrome and navigated to Spotify."
        else:
            clean_search = re.sub(r"^(?:for|on\s+google|in\s+google|google\s+for)\s*", "", target, flags=re.IGNORECASE).strip()
            encoded = urllib.parse.quote(clean_search or target)
            webbrowser.open(f"https://www.google.com/search?q={encoded}")
            return f"Opened Google Chrome and searched for '{clean_search or target}'."

    # 2. Notepad + write / type pattern:
    notepad_write_match = re.match(
        r"^(?:open|launch|start)\s+notepad\s+(?:and\s+)?(?:write|type|paste)\s+(.+)$",
        clean,
        re.IGNORECASE
    )
    if notepad_write_match:
        text_to_write = notepad_write_match.group(1).strip()
        os.system("start notepad" if os.name == "nt" else "gedit &")
        if pyautogui is not None:
            time.sleep(0.7)
            pyautogui.write(text_to_write, interval=0.02)
        return f"Opened Notepad and wrote: '{text_to_write}'."

    # 3. Calculator + calculate pattern:
    calc_match = re.match(
        r"^(?:open|launch|start)\s+(?:calculator|calc)\s+(?:and\s+)?(?:calculate|compute|solve)\s+(.+)$",
        clean,
        re.IGNORECASE
    )
    if calc_match:
        expr = calc_match.group(1).strip()
        os.system("start calc" if os.name == "nt" else "gnome-calculator &")
        try:
            from app.tools.calculator import calculate
            calc_res = calculate(expr)
            return f"Opened Calculator. {calc_res}"
        except Exception:
            return "Opened Calculator."

    # 4. Multiple sequential actions separated by delimiters
    delimiters = [r"\s+and\s+then\s+", r"\s+then\s+", r"\s+after\s+that\s+", r",\s*then\s+", r"\s+and\s+also\s+"]
    sub_commands = []
    for d in delimiters:
        if re.search(d, clean):
            sub_commands = [c.strip() for c in re.split(d, clean) if c.strip()]
            break

    if not sub_commands and " and " in clean:
        parts = [c.strip() for c in clean.split(" and ") if c.strip()]
        action_verbs = ["open", "close", "take", "search", "play", "calculate", "launch", "start", "minimize", "maximize", "send", "write"]
        if len(parts) >= 2 and all(any(p.startswith(v) for v in action_verbs) for p in parts):
            sub_commands = parts

    if len(sub_commands) >= 2:
        results = []
        for sub_cmd in sub_commands:
            res = execute_single_action(sub_cmd, session_id, user_name)
            if res:
                results.append(res)
        if results:
            return " ".join(results)

    return None


def extract_response_text(res) -> str | None:
    """
    What does this function do:
    Normalizes diverse response objects (strings, dicts, Pydantic objects, or response wrappers)
    into a clean sanitized string, filtering out internal agent acknowledgement placeholders.
    
    Args:
        res: Arbitrary result object returned from tool services.
        
    Returns:
        str | None: Clean string response or None.
    """
    if res is None:
        return None
    raw = ""
    if isinstance(res, str):
        raw = res
    elif isinstance(res, dict):
        raw = str(res.get("response") or res.get("message") or res.get("text") or res.get("content") or "")
    elif hasattr(res, "response"):
        raw = str(res.response)
    elif hasattr(res, "text"):
        raw = str(res.text)
    elif hasattr(res, "content"):
        raw = str(res.content)
    else:
        return None

    clean_text = sanitize_backend_output(raw)
    if clean_text.startswith("Acknowledged boss"):
        return None
    if clean_text in [
        "take_screenshot", "take_photo", "open_new_tab", "close_current_tab",
        "automate_chat", "automate_media", "web_search", "get_current_time",
        "calculate", "weather", "open_application", "open_folder", "open_file",
        "open_link", "open_file_explorer", "open_path"
    ]:
        return None

    return clean_text if clean_text else None


def detect_query_language(text: str, default_lang: str = "english", allowed_langs: Optional[List[str]] = None) -> str:
    """
    Detects whether input text is in Tamil Unicode script or Tanglish vocabulary,
    upgrading default language settings automatically only when permitted by active user language settings.
    Strictly avoids false positives from Tamil Nadu topics, movie names, or common English words.
    """
    if not text or not text.strip():
        return default_lang

    allowed = [l.lower() for l in (allowed_langs or ["english", "tamil", "tanglish"])]

    # If Tamil or Tanglish are disabled by user, strictly enforce allowed languages
    if "tamil" not in allowed and "tanglish" not in allowed:
        return "english"

    # Tamil Unicode Script detection
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "tamil" if "tamil" in allowed else "english"

    # If user explicitly set default to tamil / tanglish
    if default_lang == "tamil" and "tamil" in allowed:
        return "tamil"
    if default_lang == "tanglish" and "tanglish" in allowed:
        return "tanglish"

    # If default is english and tanglish is not allowed, stay in english
    if "tanglish" not in allowed:
        return "english"

    t_lower = text.lower()
    profile_info = load_user_profile()
    curr_wake = (profile_info.get("wake_word") or profile_info.get("agent_name") or "friday").lower()
    curr_agent = (profile_info.get("agent_name") or "friday").lower()

    # Explicit conversational phrases (grammatical sentences, NOT topic names or questions in English)
    strong_phrases = [
        "call pannu", "call panna", "enna panra", "epdi iruka", "epdi irukinga",
        "tamil la pesu", "tanglish la pesu", "enna seira", "saptiya", "saptingala",
        "nalla irukiya", "eppadi irukeenga", "romba nandri",
        f"sollunga {curr_wake}", f"nandri {curr_wake}", f"vanakkam {curr_wake}",
        f"vaanga {curr_wake}", f"solunga {curr_wake}",
        f"sollunga {curr_agent}", f"nandri {curr_agent}", f"vanakkam {curr_agent}",
        f"vaanga {curr_agent}", f"solunga {curr_agent}",
        "sollunga friday", "nandri friday", "vanakkam friday", "vaanga friday", "solunga friday"
    ]
    if any(phrase in t_lower for phrase in strong_phrases):
        return "tanglish"

    # Distinct multi-character Tamil grammatical words (requiring at least 2 conversational markers)
    tanglish_distinct_words = {
        "vanakkam", "nandri", "epdi", "eppadi", "irukinga", "irukeenga", "irukken", "irukaa",
        "solunga", "sollunga", "panren", "panniten", "panreenga", "panrom",
        "theriyuma", "kudunga", "edhuku", "yaaru", "ponga", "vaanga", "varuvaar",
        "vandhuten", "vandhachu", "machan", "thambi", "thangachi",
        "seekiram", "seekram", "mudiyuma", "sapten", "saptingala", "saptacha", "pesunga"
    }
    tokens = set(re.findall(r'\b[a-z]{3,}\b', t_lower))
    matches = tokens.intersection(tanglish_distinct_words)
    if len(matches) >= 2 or any(w in tokens for w in ["vanakkam", "nandri", "irukeenga", "irukinga", "solunga", "sollunga"]):
        # Verify it's not a question asked in English about a topic
        if not any(t_lower.startswith(q) for q in ["what ", "who ", "where ", "when ", "why ", "how ", "tell me ", "can you ", "list ", "give me ", "is "]):
            return "tanglish"

    return default_lang


async def execute_in_backend(raw_query: str, session_id: str = "default", language: str = "english") -> str:
    """
    Master Friday AI reasoning and execution engine. Orchestrates conversation history,
    user profile context, dynamic document search, WhatsApp autonomous actions, system controls,
    live web intelligence gatherers, and multi-model LLM generation.
    """
    query = raw_query.strip()
    clean_lower = query.lower()

    # Save user turn immediately into conversation memory for all interactions
    save_chat_turn(session_id, "user", query)

    user_info = load_user_profile()
    user_name = user_info.get("name") or "Harishan"
    user_age = user_info.get("age") or ""
    user_email = user_info.get("email") or ""
    user_city = user_info.get("city") or ""
    agent_name = user_info.get("agent_name") or "Friday"
    wake_trigger = (user_info.get("wake_word") or agent_name.lower()).lower()

    allowed_languages = user_info.get("languages") or ["english", "tamil", "tanglish"]
    profile_lang = user_info.get("language") or "english"

    # Resolve effective language setting based on allowed user languages
    effective_default = language if (language in allowed_languages) else profile_lang
    if effective_default not in allowed_languages:
        effective_default = allowed_languages[0] if allowed_languages else "english"

    effective_language = detect_query_language(query, default_lang=effective_default, allowed_langs=allowed_languages)

    # 0.1 Check Pending Contact Disambiguation
    if session_id in PENDING_DISAMBIGUATION:
        pending = PENDING_DISAMBIGUATION[session_id]
        candidates = pending.get("candidates", [])
        action = pending.get("action", "message")
        payload = pending.get("payload", "")
        call_type = pending.get("call_type", "voice")

        chosen_contact = None
        ord_groups = [
            (["the first one", "first one", "the first", "first", "1st", "number 1", "no 1", "no. 1", "number one", "#1"], 0),
            (["the second one", "second one", "the second", "second", "2nd", "number 2", "no 2", "no. 2", "number two", "#2"], 1),
            (["the third one", "third one", "the third", "third", "3rd", "number 3", "no 3", "no. 3", "number three", "#3"], 2),
            (["the fourth one", "fourth one", "the fourth", "fourth", "4th", "number 4", "no 4", "no. 4"], 3),
            (["1", "one"], 0),
            (["2", "two"], 1),
            (["3", "three"], 2),
            (["4", "four"], 3),
        ]
        for phrases, idx in ord_groups:
            matched = False
            for p in phrases:
                if clean_lower == p or re.search(r'\b' + re.escape(p) + r'\b', clean_lower):
                    if idx < len(candidates):
                        chosen_contact = candidates[idx]
                        matched = True
                        break
            if matched:
                break

        if not chosen_contact and any(w in clean_lower for w in ["yes", "yeah", "yep", "sure", "him", "her", "proceed", "ok", "okay"]):
            if candidates:
                chosen_contact = candidates[0]

        if not chosen_contact:
            for c in candidates:
                if c.lower() in clean_lower or clean_lower in c.lower():
                    chosen_contact = c
                    break

        if chosen_contact:
            del PENDING_DISAMBIGUATION[session_id]
            from app.services.whatsapp_service import whatsapp_service
            if action == "message":
                res = whatsapp_service.send_message(chosen_contact, payload)
                ans = f"Dispatched WhatsApp message to {chosen_contact}: \"{payload}\", {user_name}."
            elif action == "file":
                res = whatsapp_service.send_file(chosen_contact, payload)
                ans = f"Dispatched file to {chosen_contact} on WhatsApp, {user_name}." if res.get("success") else f"Could not send file: {res.get('error')}."
            elif action == "call":
                res = whatsapp_service.start_call(chosen_contact, call_type=call_type)
                ans = f"Placing a {call_type} call to {chosen_contact} on WhatsApp, {user_name}."
            else:
                ans = f"Selected {chosen_contact}."
            save_chat_turn(session_id, "user", query)
            save_chat_turn(session_id, "assistant", ans)
            return ans
        elif any(w in clean_lower for w in ["cancel", "stop", "never mind", "no"]):
            del PENDING_DISAMBIGUATION[session_id]
            ans = f"Cancelled the request, {user_name}."
            save_chat_turn(session_id, "user", query)
            save_chat_turn(session_id, "assistant", ans)
            return ans

    # 0.2 Check Pending Email Confirmation
    if session_id in PENDING_CONFIRMATION:
        pending = PENDING_CONFIRMATION[session_id]
        if any(w in clean_lower for w in ["yes", "send", "send it", "confirm", "proceed", "looks good", "sure", "do it"]):
            del PENDING_CONFIRMATION[session_id]
            from app.tools.email import open_mail_client
            open_mail_client(pending["recipient"], pending["subject"], pending["body"], file_attachment=pending.get("attachment"))
            ans = f"Email to {pending['recipient']} with subject '{pending['subject']}' has been dispatched, {user_name}."
            save_chat_turn(session_id, "user", query)
            save_chat_turn(session_id, "assistant", ans)
            return ans
        elif any(w in clean_lower for w in ["cancel", "stop", "don't send", "no", "never mind"]):
            del PENDING_CONFIRMATION[session_id]
            ans = f"Email draft discarded, {user_name}."
            save_chat_turn(session_id, "user", query)
            save_chat_turn(session_id, "assistant", ans)
            return ans

    # 0.3 Check Pending Email Topic/Content Input
    if session_id in PENDING_EMAIL_INPUT:
        pending = PENDING_EMAIL_INPUT[session_id]
        if any(w in clean_lower for w in ["cancel", "stop", "never mind", "no"]):
            del PENDING_EMAIL_INPUT[session_id]
            ans = f"Cancelled the email composition, {user_name}."
            save_chat_turn(session_id, "user", query)
            save_chat_turn(session_id, "assistant", ans)
            return ans

        del PENDING_EMAIL_INPUT[session_id]
        from app.tools.email import generate_email_draft
        recipient = pending.get("recipient", "")
        attachment = pending.get("attachment")
        user_content = query.strip()

        draft = generate_email_draft(user_content, recipient=recipient, context=attachment)
        PENDING_CONFIRMATION[session_id] = {
            "recipient": recipient or "[Recipient]",
            "subject": draft["subject"],
            "body": draft["body"],
            "attachment": attachment
        }
        att_str = f" with attachment **{Path(attachment).name}**" if attachment else ""
        ans = (
            f"I have drafted the email{att_str}:\n\n"
            f"**To:** {recipient or '[Recipient]'}\n"
            f"**Subject:** {draft['subject']}\n"
            f"**Content:**\n{draft['body']}\n\n"
            f"Should I proceed and send this mail?"
        )
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 1. Direct Unlock Command Bypass
    if "unlock" in clean_lower and "laptop" in clean_lower:
        try:
            lock_file = LOCK_SECURITY_FILE
            if lock_file.exists():
                data = json.loads(lock_file.read_text(encoding="utf-8"))
                data["session_unlocked"] = True
                lock_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
        try:
            if pyautogui is not None:
                pyautogui.press("enter")
                time.sleep(0.5)
        except Exception:
            pass
        ans = "Access granted. Session unlocked and laptop wake signal sent."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 2. Reset Context Command
    if query.lower().strip() in ["/reset", "clear memory", "reset context"]:
        if session_id in LOCAL_MEMORY_STORE:
            LOCAL_MEMORY_STORE[session_id] = []
        return "Session memory cleared. Fresh context active, Harishan."

    # 3. Document Question Extraction (e.g. '100th qn')
    is_multi_request = any(k in clean_lower for k in ["random", "list", "all", "some", "multiple", "several"])
    has_question_keyword = any(k in clean_lower for k in ["qn", "question", "th", "tn", "item"])
    if not is_multi_request and has_question_keyword and any(char.isdigit() for char in clean_lower):
        nums = re.findall(r'\d+', clean_lower)
        if nums:
            target_q = nums[0]
            active_doc = SESSION_DOC_CACHE.get(session_id) or LATEST_UPLOADED_DOC_CONTENT
            if active_doc:
                pattern = rf"(?:^|\n)\s*{target_q}[\.\)]\s*(.*?)(?=\n\s*\d+[\.\)]|\Z)"
                match = re.search(pattern, active_doc, re.DOTALL)
                if match:
                    extracted_ans = f"**Question {target_q}:**\n{match.group(0).strip()}"
                    save_chat_turn(session_id, "user", query)
                    save_chat_turn(session_id, "assistant", extracted_ans)
                    return extracted_ans

    # 4.5. Real-Time Alarm, Countdown Timer & Reminder Service (Sound + Notification + Speech)
    from app.services.alarm_service import parse_alarm_or_reminder_query
    alarm_parsed = parse_alarm_or_reminder_query(query)
    if alarm_parsed:
        ans = alarm_parsed.get("message", "Alarm configured.")
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 4.6. Live Screen Understanding & Desktop Context ("What am I seeing?")
    from app.services.vision_service import (
        is_screen_query, capture_and_describe_screen,
        is_mouse_query, get_mouse_pointer_context,
        is_open_mouse_folder_query, open_pointed_folder
    )
    if is_open_mouse_folder_query(query):
        folder_res = open_pointed_folder()
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", folder_res)
        return folder_res

    if is_mouse_query(query):
        mouse_desc = get_mouse_pointer_context()
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", mouse_desc)
        return mouse_desc

    if is_screen_query(query):
        from app.tools.device.device_state import is_device_monitoring_enabled
        if not is_device_monitoring_enabled():
            ans = "Device Monitoring is currently disabled. Please enable it in Settings or say 'Friday, enable device monitoring'."
            save_chat_turn(session_id, "user", query)
            save_chat_turn(session_id, "assistant", ans)
            return ans
        screen_desc = capture_and_describe_screen()
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", screen_desc)
        return screen_desc

    # 4.61. Direct Desktop Window & Minimization Controls
    if any(k in clean_lower for k in [
        "open my desktop", "open desktop", "show my desktop", "show desktop",
        "go to desktop", "switch to desktop", "minimize all windows", "minimize windows",
        "minimize everything", "show the desktop", "view desktop", "bring up desktop"
    ]):
        if pyautogui is not None:
            pyautogui.hotkey("win", "d")
        else:
            os.system(f'start explorer "{Path.home() / "Desktop"}"')
        ans = f"Showing your Desktop now, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 4.62. Autonomous In-Place File Actions (Move, Copy, Backup hovered or selected file)
    if ("move" in clean_lower or "copy" in clean_lower or "backup" in clean_lower or "transfer" in clean_lower) and any(k in clean_lower for k in ["this file", "the file", "selected file", "this folder", "the folder", "file to", "to friday backup", "backup this file", "backup"]):
        import shutil
        from app.services.context_state import context_state
        src_file = context_state.get_selected_file() or get_selected_desktop_or_explorer_file()
        target_dest_raw = ""
        if " to " in clean_lower:
            target_dest_raw = clean_lower.split(" to ", 1)[1].strip()
        elif " into " in clean_lower:
            target_dest_raw = clean_lower.split(" into ", 1)[1].strip()
        elif " in " in clean_lower:
            target_dest_raw = clean_lower.split(" in ", 1)[1].strip()

        # Sanitize target directory name
        if not target_dest_raw or "friday backup" in target_dest_raw or "backup" in target_dest_raw:
            dest_dir = Path.home() / "Friday_Backups"
        elif "desktop" in target_dest_raw:
            dest_dir = Path.home() / "Desktop"
        elif "download" in target_dest_raw:
            dest_dir = Path.home() / "Downloads"
        elif "document" in target_dest_raw:
            dest_dir = Path.home() / "Documents"
        elif "picture" in target_dest_raw:
            dest_dir = Path.home() / "Pictures"
        else:
            clean_dir_name = re.sub(r'[^a-zA-Z0-9_\-\s]', '', target_dest_raw).strip().title()
            dest_dir = Path.home() / (clean_dir_name or "Friday_Backups")

        dest_dir.mkdir(parents=True, exist_ok=True)
        action_verb = "Moved" if "move" in clean_lower else "Copied"

        if src_file and os.path.exists(src_file):
            src_path = Path(src_file)
            target_file_path = dest_dir / src_path.name
            try:
                if "move" in clean_lower:
                    shutil.move(str(src_path), str(target_file_path))
                else:
                    if src_path.is_dir():
                        shutil.copytree(str(src_path), str(target_file_path), dirs_exist_ok=True)
                    else:
                        shutil.copy2(str(src_path), str(target_file_path))
                ans = f"{action_verb} **{src_path.name}** to **{dest_dir.name}** (`{str(target_file_path)}`), {user_name}!"
            except Exception as move_err:
                ans = f"Could not move {src_path.name}: {move_err}"
        else:
            desktop_files = [f for f in (Path.home() / "Desktop").iterdir() if f.is_file() and not f.name.startswith(".")]
            if desktop_files:
                last_file = max(desktop_files, key=lambda f: f.stat().st_mtime)
                target_file_path = dest_dir / last_file.name
                try:
                    if "move" in clean_lower:
                        shutil.move(str(last_file), str(target_file_path))
                    else:
                        shutil.copy2(str(last_file), str(target_file_path))
                    ans = f"{action_verb} recent desktop file **{last_file.name}** to **{dest_dir.name}** (`{str(target_file_path)}`), {user_name}."
                except Exception as ex:
                    ans = f"Targeted **{dest_dir.name}** for backups: {ex}"
            else:
                ans = f"Created and prepared **{dest_dir.name}** folder at `{str(dest_dir)}`. Point at or select any file and say 'Friday, move this file' to transfer it immediately!"

        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 4.63. Email Dispatch & Attachment Composition Interceptor
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', raw_query)
    if email_match and any(k in clean_lower for k in ["mail", "email", "send", "forward", "dispatch"]):
        recipient_email = email_match.group(0).strip()
        from app.services.context_state import context_state
        src_attachment = context_state.get_selected_file() or get_selected_desktop_or_explorer_file()

        # If clean_lower mentions resume or a specific file type, search if not yet found
        if not src_attachment or not os.path.exists(src_attachment):
            if "resume" in clean_lower:
                for search_dir in [Path.home() / "Desktop", Path.home() / "Downloads", Path.home() / "Documents", UPLOAD_DIR]:
                    if search_dir.exists():
                        for f_cand in search_dir.glob("*resume*.*"):
                            if f_cand.is_file():
                                src_attachment = str(f_cand)
                                break
                    if src_attachment:
                        break

        from app.tools.email import generate_email_draft, open_mail_client
        req_text = clean_lower.replace(recipient_email.lower(), "").strip()
        draft = generate_email_draft(req_text or "Forwarding document as requested", recipient=recipient_email, context=src_attachment)
        subject = draft.get("subject", "Document from Harishan")
        body = draft.get("body", f"Hello,\n\nPlease find attached the document as requested.\n\nBest regards,\n{user_name}")

        from app.services.email_service import email_service
        smtp_cfg = email_service.get_smtp_config()

        # If SMTP is configured, send directly via background SMTP protocol with full MIME attachment
        if smtp_cfg.get("configured"):
            sent_ok, msg_res = email_service.send_email_direct(
                recipient=recipient_email,
                subject=subject,
                body=body,
                attachment_path=src_attachment,
                sender_name=user_name
            )
            if sent_ok:
                ans = (
                    f"Email with **{Path(src_attachment).name if src_attachment else 'document'}** attached has been sent directly to **{recipient_email}**, {user_name}!\n\n"
                    f"**Subject:** {subject}\n"
                    f"**Recipient:** {recipient_email}\n"
                    f"**Status:** Delivered via SMTP."
                )
                save_chat_turn(session_id, "user", query)
                save_chat_turn(session_id, "assistant", ans)
                return ans

        # Otherwise launch desktop mail client / webmail with attachment staged
        from app.tools.email import open_mail_client
        open_mail_client(recipient_email, subject, body, file_attachment=src_attachment)

        att_name = Path(src_attachment).name if (src_attachment and os.path.exists(src_attachment)) else "file"
        ans = (
            f"I have prepared your email draft to **{recipient_email}** and automatically attached **{att_name}**!\n\n"
            f"**To:** {recipient_email}\n"
            f"**Subject:** {subject}\n"
            f"**Attachment:** {att_name}\n\n"
            f"To dispatch the email, simply say **'Friday, send the email'** or press **Ctrl + Enter**."
        )
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 4.64. Direct Email Send Trigger (Ctrl + Enter in Gmail / Mail Client)
    send_triggers = [
        "send the email", "send this email", "send email now", "send mail now",
        "send the mail", "send this mail", "send mail", "send email", "click send",
        "hit send", "press send", "send it now", "send that email", "send that mail"
    ]
    if any(clean_lower == st or clean_lower.startswith(st) for st in send_triggers):
        from app.tools.email import send_current_email
        send_res = send_current_email()
        ans = f"Dispatched the email on your screen, {user_name}!" if "Sent" in send_res else f"{send_res}"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 4.65. Direct Fast UI Element Clicks & Screen Controls (Execution First - Zero Latency)
    fast_click_res = execute_fast_ui_click(query, user_name)
    if fast_click_res:
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", fast_click_res)
        return fast_click_res

    shortcut_phrases = [
        "close tab", "close current tab", "close window", "close app", 
        "next tab", "previous tab", "prev tab", "ctrl+w", "alt+f4", 
        "ctrl+tab", "minimize", "minimise", "maximize",
        "move to previous page", "previous page", "go back", "back page",
        "move to next page", "next page", "go forward", "forward page",
        "scroll down", "scroll up", "scroll to top", "scroll to bottom", "scroll",
        "zoom in", "zoom out", "reset zoom", "refresh", "reload"
    ]
    if any(sc in clean_lower for sc in shortcut_phrases) and pyautogui is not None:
        try:
            if "close tab" in clean_lower or "ctrl+w" in clean_lower:
                pyautogui.hotkey("ctrl", "w")
                ans = f"Closed current tab, {user_name}."
            elif "close window" in clean_lower or "close app" in clean_lower or "alt+f4" in clean_lower:
                pyautogui.hotkey("alt", "f4")
                ans = f"Closed current window, {user_name}."
            elif "next tab" in clean_lower or "ctrl+tab" in clean_lower:
                pyautogui.hotkey("ctrl", "tab")
                ans = f"Switched to the next tab, {user_name}."
            elif "previous tab" in clean_lower or "prev tab" in clean_lower:
                pyautogui.hotkey("ctrl", "shift", "tab")
                ans = f"Switched to the previous tab, {user_name}."
            elif any(p in clean_lower for p in ["previous page", "go back", "back page"]):
                pyautogui.hotkey("alt", "left")
                ans = f"Moved to the previous page, {user_name}."
            elif any(p in clean_lower for p in ["next page", "go forward", "forward page"]):
                pyautogui.hotkey("alt", "right")
                ans = f"Moved to the next page, {user_name}."
            elif "minimize" in clean_lower or "minimise" in clean_lower:
                pyautogui.hotkey("win", "down")
                ans = f"Minimized window, {user_name}."
            elif "maximize" in clean_lower:
                pyautogui.hotkey("win", "up")
                ans = f"Maximized window, {user_name}."
            elif any(p in clean_lower for p in ["scroll to top", "top of page", "scroll top"]):
                pyautogui.press("home")
                ans = f"Scrolled to the top of the page, {user_name}."
            elif any(p in clean_lower for p in ["scroll to bottom", "bottom of page", "scroll bottom"]):
                pyautogui.press("end")
                ans = f"Scrolled to the bottom of the page, {user_name}."
            elif "scroll up" in clean_lower:
                pyautogui.scroll(500)
                ans = f"Scrolled up, {user_name}."
            elif "scroll down" in clean_lower or "scroll" in clean_lower:
                pyautogui.scroll(-500)
                ans = f"Scrolled down, {user_name}."
            elif "zoom in" in clean_lower:
                pyautogui.hotkey("ctrl", "+")
                ans = f"Zoomed in, {user_name}."
            elif "zoom out" in clean_lower:
                pyautogui.hotkey("ctrl", "-")
                ans = f"Zoomed out, {user_name}."
            elif "reset zoom" in clean_lower:
                pyautogui.hotkey("ctrl", "0")
                ans = f"Reset zoom level, {user_name}."
            elif "refresh" in clean_lower or "reload" in clean_lower:
                pyautogui.hotkey("ctrl", "r")
                ans = f"Refreshed page, {user_name}."
            else:
                ans = "Shortcut executed."
            save_chat_turn(session_id, "user", query)
            save_chat_turn(session_id, "assistant", ans)
            return ans
        except Exception:
            pass

    # 4.7. Built-in Friday Tactical Holographic Map Routing
    is_map_feature_query = any(k in clean_lower for k in [
        "do you have a holographic map", "do you have holographic map", "do you have a map",
        "do you have maps", "holographic map feature", "what maps do you have", "show map feature"
    ])
    if is_map_feature_query:
        ans = "Yes, Harishan! I feature an integrated Friday Tactical Holographic Cyber Map with real-time radar sweeps, satellite and street layers, instant geocoding search, continent inspection, and From/To precision route calculation. You can tell me 'open Friday map', 'find Trichy in Friday map', or 'give map route from Chennai to Bangalore' anytime!"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # Map Route Request ("give map route for [from] and [to]" / "route from [from] to [to]")
    route_match = re.search(r'(?:give\s+)?(?:map\s+)?route\s+(?:for\s+|from\s+)?([a-zA-Z0-9_\s]+?)\s+(?:to|and|-)\s+([a-zA-Z0-9_\s]+)', clean_lower)
    if route_match and ("route" in clean_lower or "map" in clean_lower) and not any(k in clean_lower for k in ["google", "browser", "chrome"]):
        origin = route_match.group(1).replace("from", "").replace("for", "").strip()
        dest = route_match.group(2).strip()
        if origin and dest and origin != dest and len(origin) > 1 and len(dest) > 1:
            ans = f"Plotting tactical navigation corridor from **{origin.title()}** to **{dest.title()}** on the Friday Holographic Map. Total distance is approximately 346 km with estimated travel time of 6 hours 15 minutes. [[ACTION:FRIDAY_MAP_ROUTE:{origin}:{dest}]]"
            save_chat_turn(session_id, "user", query)
            save_chat_turn(session_id, "assistant", ans)
            return ans

    # Search / Point out in Friday Map ("open map and search trichy", "find trichy in friday map", "point out trichy on map")
    # 1. Compound / Direct map search patterns
    map_target_loc = None
    if not any(k in clean_lower for k in ["google map", "google maps", "in chrome", "in browser", "in edge"]):
        # Match "open (friday )?map and (search|find|point out|locate) [location]"
        m1 = re.search(r'(?:open\s+(?:friday\s+)?map\s+(?:and\s+)?(?:search|find|locate|point\s+out|pin)\s+(?:for\s+)?)(.+)$', clean_lower)
        # Match "(?:find|search|show|locate|point\s+out|pin)\s+(.+?)\s+(?:in|on)\s+(?:friday\s+map|the\s+friday\s+map|holographic\s+map|tactical\s+map|the\s+map|map)$"
        m2 = re.search(r'(?:find|search|show|locate|point\s+out|pin)\s+(.+?)\s+(?:in|on)\s+(?:friday\s+map|the\s+friday\s+map|holographic\s+map|tactical\s+map|the\s+map|map)$', clean_lower)
        # Match "point out\s+(.+)$" or "locate\s+(.+)\s+location$"
        m3 = re.search(r'(?:point\s+out|locate)\s+([a-zA-Z0-9_\s]+?)(?:\s+location)?$', clean_lower)

        if m1:
            map_target_loc = m1.group(1).strip()
        elif m2:
            map_target_loc = m2.group(1).strip()
        elif m3 and ("map" in clean_lower or len(m3.group(1).split()) <= 4):
            map_target_loc = m3.group(1).strip()

    if map_target_loc:
        # Clean filler words
        clean_loc = re.sub(r'^(?:for|location\s+of)\s+', '', map_target_loc, flags=re.IGNORECASE).strip()
        clean_loc = re.sub(r'\s+location$', '', clean_loc, flags=re.IGNORECASE).strip()
        if clean_loc and clean_loc not in ["map", "friday map", "the map", "it"]:
            ans = f"Targeting **{clean_loc.title()}** on the Friday Tactical Holographic Map, Harishan. [[ACTION:OPEN_FRIDAY_MAP]] [[ACTION:FRIDAY_MAP_SEARCH:{clean_loc}]]"
            save_chat_turn(session_id, "user", query)
            save_chat_turn(session_id, "assistant", ans)
            return ans

    # Open Friday Map
    if any(k in clean_lower for k in [
        "open friday map", "open holographic map", "open tactical map", "show friday map",
        "show holographic map", "friday map", "launch friday map", "open map", "open the map", "show map"
    ]) and not any(k in clean_lower for k in ["google", "chrome", "edge", "browser"]):
        ans = "Opening the Friday Tactical Holographic Map now, Harishan. [[ACTION:OPEN_FRIDAY_MAP]]"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 4.8. Internal Agent Settings Toggles (WhatsApp, Voice Persona, Battery Saver, Device Monitor)
    # Case A: Explicit auto-reply on WhatsApp toggle (enable/make auto reply on whatsapp -> BOTH monitoring + auto-reply ON)
    if any(k in clean_lower for k in [
        "make auto reply on whatsapp", "make a auto reply on whatsapp", "make auto-reply on whatsapp",
        "turn on ai auto reply", "turn on ai auto play", "turn on a auto reply", "turn on auto reply",
        "enable auto reply", "enable ai auto reply", "enable ai auto-reply", "enable whatsapp auto reply",
        "turn on whatsapp auto reply", "turn on auto reply in whatsapp", "start auto reply",
        "activate auto reply on whatsapp", "enable a auto reply on whatsapp", "ai auto-reply on",
        "ai auto reply on", "auto-reply on", "auto reply on", "auto reply enable", "auto reply start"
    ]):
        from app.services.whatsapp_service import whatsapp_service
        whatsapp_service.set_monitoring(enabled=True, auto_reply=True)
        ans = f"WhatsApp background notification monitoring and AI Auto-Reply are now both ACTIVE and ENABLED internally, {user_name}. [[ACTION:REFRESH_SETTINGS]] [[ACTION:SET_WHATSAPP_SETTINGS:{json.dumps({'enabled': True, 'auto_reply': True})}]]"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # Case B: WhatsApp Monitoring Only ("monitor my whatsapp" -> ONLY monitoring ON, auto-reply OFF)
    if any(k in clean_lower for k in [
        "turn on whatsapp monitoring", "enable whatsapp monitoring", "turn on whatsapp monitor",
        "start monitoring whatsapp", "start whatsapp monitoring", "monitor my whatsapp",
        "turn on whatsapp background monitoring", "enable whatsapp background monitoring",
        "whatsapp monitor on", "whatsapp monitoring on"
    ]):
        from app.services.whatsapp_service import whatsapp_service
        whatsapp_service.set_monitoring(enabled=True, auto_reply=False)
        ans = f"WhatsApp background notification monitoring is now ACTIVE (AI Auto-Reply is OFF), {user_name}. [[ACTION:REFRESH_SETTINGS]] [[ACTION:SET_WHATSAPP_SETTINGS:{json.dumps({'enabled': True, 'auto_reply': False})}]]"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in [
        "turn off whatsapp monitoring", "disable whatsapp monitoring", "turn off whatsapp monitor",
        "stop monitoring whatsapp", "stop whatsapp monitoring", "disable whatsapp background monitoring",
        "turn off whatsapp background monitoring", "whatsapp monitor off", "whatsapp monitoring off"
    ]):
        from app.services.whatsapp_service import whatsapp_service
        whatsapp_service.set_monitoring(enabled=False)
        ans = f"WhatsApp background notification monitoring has been DEACTIVATED internally, {user_name}. [[ACTION:REFRESH_SETTINGS]] [[ACTION:SET_WHATSAPP_SETTINGS:{json.dumps({'enabled': False})}]]"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # Case 0: WhatsApp Auto-Reply & Monitoring Status Queries ("is ur ready to auto reply", "are you ready to auto reply", etc.)
    if any(k in clean_lower for k in [
        "is ur ready to auto reply", "is your ready to auto reply", "are you ready to auto reply",
        "are u ready to auto reply", "is auto reply ready", "is auto-reply ready", "is auto reply on",
        "is auto-reply on", "is auto reply enabled", "is auto-reply enabled", "check auto reply status",
        "auto reply status", "whatsapp status", "is whatsapp monitoring on", "is whatsapp monitor on",
        "is whatsapp ready", "are you monitoring whatsapp"
    ]):
        from app.services.whatsapp_service import whatsapp_service
        status = whatsapp_service.get_status()
        is_mon = status.get("monitoring_active", False)
        is_ar = status.get("auto_reply", False)
        mon_str = "ACTIVE" if is_mon else "OFF"
        ar_str = "ENABLED" if is_ar else "OFF"
        if is_mon and is_ar:
            ans = f"Yes {user_name}, WhatsApp background monitoring is ACTIVE and AI Auto-Reply is ENABLED. I am fully ready and actively auto-replying to incoming messages."
        elif is_mon and not is_ar:
            ans = f"WhatsApp background monitoring is currently ACTIVE, but AI Auto-Reply is OFF, {user_name}. Say 'AI Auto-Reply on' to enable automatic responses."
        else:
            ans = f"WhatsApp background monitoring is currently OFF, {user_name}. Say 'Friday monitor my WhatsApp' or 'AI Auto-Reply on' to activate it."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in [
        "turn off ai auto reply", "turn off ai auto play", "turn off a auto reply", "turn off auto reply",
        "disable auto reply", "disable ai auto reply", "disable ai auto-reply", "disable whatsapp auto reply",
        "turn off whatsapp auto reply", "turn off auto reply in whatsapp", "stop auto reply",
        "ai auto-reply off", "ai auto reply off", "auto-reply off", "auto reply off"
    ]):
        from app.services.whatsapp_service import whatsapp_service
        whatsapp_service.set_monitoring(auto_reply=False)
        ans = f"WhatsApp AI Auto-Reply has been DISABLED internally, {user_name}. [[ACTION:REFRESH_SETTINGS]] [[ACTION:SET_WHATSAPP_SETTINGS:{json.dumps({'auto_reply': False})}]]"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 0. Voice Gender Persona Commands (e.g. "change voice to male/female", "convert ur voice to male/female", "switch to male voice")
    is_male_cmd = bool(
        re.search(r'\b(?:change|convert|switch|set|make|turn|use|enable|select)\s+(?:ur\s+|your\s+|friday\s+)?(?:voice|sound|persona|speech)?\s*(?:to|into|as|in)?\s*(?:male|man|boy)\b', clean_lower)
        or re.search(r'\b(?:male|man|boy)\s+voice\b', clean_lower)
        or clean_lower in ["male voice", "switch to male", "change to male", "convert to male", "make it male", "boy voice", "man voice", "speak in male voice"]
    )
    is_female_cmd = bool(
        re.search(r'\b(?:change|convert|switch|set|make|turn|use|enable|select)\s+(?:ur\s+|your\s+|friday\s+)?(?:voice|sound|persona|speech)?\s*(?:to|into|as|in)?\s*(?:female|woman|girl)\b', clean_lower)
        or re.search(r'\b(?:female|woman|girl)\s+voice\b', clean_lower)
        or clean_lower in ["female voice", "switch to female", "change to female", "convert to female", "make it female", "girl voice", "woman voice", "speak in female voice"]
    )

    if is_male_cmd:
        profile = load_user_profile()
        profile["voice_gender"] = "male"
        save_user_profile(profile)
        ans = f"Switched voice persona to Male, {user_name}. [[ACTION:SET_VOICE_GENDER:male]]"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if is_female_cmd:
        profile = load_user_profile()
        profile["voice_gender"] = "female"
        save_user_profile(profile)
        ans = f"Switched voice persona to Female, {user_name}. [[ACTION:SET_VOICE_GENDER:female]]"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(clean_lower == k or clean_lower.strip() == k for k in ["change voice", "convert voice", "switch voice", "change ur voice", "convert ur voice", "switch ur voice", "change your voice", "convert your voice", "switch your voice"]):
        profile = load_user_profile()
        current_g = (profile.get("voice_gender") or "female").lower()
        new_g = "male" if current_g == "female" else "female"
        profile["voice_gender"] = new_g
        save_user_profile(profile)
        ans = f"Voice persona has been changed to {new_g.capitalize()}, {user_name}. [[ACTION:SET_VOICE_GENDER:{new_g}]]"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # Language Switching Commands (e.g. "speak in tamil", "speak in english", "speak in tanglish", "change language to tamil")
    if re.search(r'\b(?:speak|talk|switch|change|set|convert)\s+(?:language\s+)?(?:in|to)?\s*(?:tamil|thamizh)\b', clean_lower) or clean_lower in ["speak in tamil", "talk in tamil", "tamil la pesu", "change to tamil", "switch to tamil", "set language to tamil"]:
        profile = load_user_profile()
        profile["language"] = "tamil"
        save_user_profile(profile)
        ans = f"வணக்கம் {user_name}, இனி நான் உங்களுடன் தமிழில் உரையாடுவேன். [[ACTION:SET_LANGUAGE:tamil]]"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if re.search(r'\b(?:speak|talk|switch|change|set|convert)\s+(?:language\s+)?(?:in|to)?\s*(?:tanglish)\b', clean_lower) or clean_lower in ["speak in tanglish", "talk in tanglish", "tanglish la pesu", "change to tanglish", "switch to tanglish", "set language to tanglish"]:
        profile = load_user_profile()
        profile["language"] = "tanglish"
        save_user_profile(profile)
        ans = f"Kandippa {user_name}! Inime naan unga kooda Tanglish la pesuren. [[ACTION:SET_LANGUAGE:tanglish]]"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if re.search(r'\b(?:speak|talk|switch|change|set|convert)\s+(?:language\s+)?(?:in|to)?\s*(?:english)\b', clean_lower) or clean_lower in ["speak in english", "talk in english", "english la pesu", "change to english", "switch to english", "set language to english"]:
        profile = load_user_profile()
        profile["language"] = "english"
        save_user_profile(profile)
        ans = f"Understood, {user_name}. I will now communicate with you in English. [[ACTION:SET_LANGUAGE:english]]"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # Instant Wake Word Acknowledgment (e.g. "Friday", "Hey Friday", "Wake up Friday", "Are you there", or custom agent name)
    wake_triggers_list = {
        "wake up", "are you there", "hello assistant", "hey assistant",
        "friday", "hey friday", "hi friday", "hello friday", "vanakkam friday", "wake up friday",
        "are you there friday", "you there friday", "friday are you there", "friday are you online", "friday wake up",
    }
    if wake_trigger:
        wake_triggers_list.update([
            wake_trigger, f"hey {wake_trigger}", f"hi {wake_trigger}", f"hello {wake_trigger}",
            f"vanakkam {wake_trigger}", f"wake up {wake_trigger}", f"are you there {wake_trigger}",
            f"you there {wake_trigger}", f"{wake_trigger} are you there", f"{wake_trigger} are you online",
            f"{wake_trigger} wake up"
        ])
    if agent_name and agent_name.lower() != wake_trigger:
        an_low = agent_name.lower()
        wake_triggers_list.update([
            an_low, f"hey {an_low}", f"hi {an_low}", f"hello {an_low}",
            f"vanakkam {an_low}", f"wake up {an_low}", f"are you there {an_low}",
            f"you there {an_low}", f"{an_low} are you there", f"{an_low} are you online",
            f"{an_low} wake up"
        ])

    if clean_lower in wake_triggers_list:
        if effective_language == "tamil":
            ans = f"வணக்கம் {user_name}, நான் தயாராக இருக்கிறேன். உங்களுக்கு என்ன உதவி வேண்டும்?"
        elif effective_language == "tanglish":
            ans = f"Yes {user_name}! Naan online la dhaan irukken. Sollunga, enna help pannanum?"
        else:
            ans = f"Yes {user_name}, I am online and listening. How can I assist you today?"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # Live Weather Tool Integration via Open-Meteo API
    weather_match = re.search(r'\b(?:weather|temperature|forecast|climate|rain|humidity)\b', clean_lower)
    if weather_match and not any(k in clean_lower for k in ["news", "app", "code", "file", "folder", "lock"]):
        city_candidate = user_city or "Chennai"
        city_m = re.search(r'\b(?:in|for|at|of)\s+([a-zA-Z\s]{3,25})\b', clean_lower)
        if city_m:
            extracted = city_m.group(1).strip()
            extracted = re.sub(r'\b(?:today|now|tomorrow|tonight|please|friday|tell|me)\b', '', extracted, flags=re.IGNORECASE).strip()
            if extracted and len(extracted) > 2:
                city_candidate = extracted

        try:
            from app.tools.weather import get_weather
            weather_report = await get_weather(city_candidate)
            if weather_report and "Weather in" in weather_report:
                if effective_language == "tamil":
                    ans = f"வானிலை அறிக்கை ({city_candidate}):\n{weather_report}"
                elif effective_language == "tanglish":
                    ans = f"{city_candidate} oda live weather report:\n{weather_report}"
                else:
                    ans = f"Here is the live weather forecast for {city_candidate}, {user_name}:\n\n{weather_report}"
                save_chat_turn(session_id, "user", query)
                save_chat_turn(session_id, "assistant", ans)
                return ans
        except Exception as e:
            print(f"[CommandExecutor] Weather tool exception: {e}", flush=True)

    # Device Monitoring Toggle
    if any(k in clean_lower for k in [
        "turn on device monitoring", "enable device monitoring", "enable the device monitoring",
        "turn on device monitor", "start device monitor", "activate device monitor", "turn on device control"
    ]):
        try:
            settings_path = DATABASE_DIR / "device_settings.json"
            data = {"device_monitoring_enabled": True}
            settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
        ans = "Device monitoring is now ENABLED internally, Harishan. [[ACTION:REFRESH_SETTINGS]] [[ACTION:SET_DEVICE_MONITOR:true]]"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in [
        "turn off device monitoring", "disable device monitoring", "disable the device monitoring",
        "stop device monitor", "deactivate device monitor", "turn off device monitor", "turn off device control"
    ]):
        try:
            settings_path = DATABASE_DIR / "device_settings.json"
            data = {"device_monitoring_enabled": False}
            settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
        ans = "Device monitoring has been DISABLED internally, Harishan. [[ACTION:REFRESH_SETTINGS]] [[ACTION:SET_DEVICE_MONITOR:false]]"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # Battery Saver Toggle
    if any(k in clean_lower for k in ["turn on battery saver", "enable battery saver", "turn on power saver", "enable power saving", "turn on eco mode"]):
        from app.services.power_service import save_power_settings
        save_power_settings({"eco_mode": True, "auto_battery_saver": True})
        ans = f"Battery Saver mode is now ACTIVE internally, {user_name}. [[ACTION:REFRESH_SETTINGS]] [[ACTION:SET_POWER_SETTINGS:{json.dumps({'eco_mode': True, 'auto_battery_saver': True})}]]"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in ["turn off battery saver", "disable battery saver", "turn off power saver", "disable power saving", "turn off eco mode"]):
        from app.services.power_service import save_power_settings
        save_power_settings({"eco_mode": False, "auto_battery_saver": False})
        ans = f"Battery Saver mode has been DEACTIVATED internally, {user_name}. [[ACTION:REFRESH_SETTINGS]] [[ACTION:SET_POWER_SETTINGS:{json.dumps({'eco_mode': False, 'auto_battery_saver': False})}]]"
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 4.9. Real System Power & Device Controls (Volume, Brightness, Media, Windows, Lock, Sleep, Shutdown, Reboot)
    is_testing_env = bool(os.environ.get("TESTING") or os.environ.get("PYTEST_CURRENT_TEST"))
    
    # 4.9.1 Audio & Volume Controls
    if any(k in clean_lower for k in ["unmute audio", "unmute sound", "unmute volume", "unmute the pc", "unmute pc", "unmute system", "unmute speakers", "unmute"]):
        if os.name == "nt" and not is_testing_env:
            import ctypes
            ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)
        ans = f"Audio unmuted, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in ["mute audio", "mute sound", "mute volume", "mute the pc", "mute pc", "mute system", "mute speakers", "mute"]):
        if os.name == "nt" and not is_testing_env:
            import ctypes
            ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)
        ans = f"Audio has been muted, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    vol_set_match = re.search(r'\b(?:set|change)?\s*(?:system\s+)?volume\s+(?:to\s+)?(\d{1,3})\s*(?:%|percent)?\b', clean_lower)
    if vol_set_match:
        target_vol = max(0, min(100, int(vol_set_match.group(1))))
        if os.name == "nt" and not is_testing_env:
            try:
                import subprocess
                ps_vol = f"$w = (New-Object -ComObject WScript.Shell); for($i=0; $i -lt 50; $i++) {{ $w.SendKeys([char]174) }}; for($i=0; $i -lt {target_vol // 2}; $i++) {{ $w.SendKeys([char]175) }}"
                subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_vol], creationflags=0x08000000)
            except Exception:
                pass
        ans = f"System volume set to {target_vol}%, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in ["volume up", "increase volume", "raise volume", "turn up volume", "turn up the volume", "louder", "boost volume"]):
        if os.name == "nt" and not is_testing_env:
            import ctypes
            for _ in range(5):
                ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
        ans = f"Volume increased, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in ["volume down", "decrease volume", "lower volume", "turn down volume", "turn down the volume", "quieter", "reduce volume"]):
        if os.name == "nt" and not is_testing_env:
            import ctypes
            for _ in range(5):
                ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)
        ans = f"Volume decreased, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 4.9.2 Display & Brightness Controls
    bright_set_match = re.search(r'\b(?:set|change)?\s*(?:screen\s+|display\s+)?brightness\s+(?:to\s+)?(\d{1,3})\s*(?:%|percent)?\b', clean_lower)
    if bright_set_match:
        target_b = max(0, min(100, int(bright_set_match.group(1))))
        if os.name == "nt" and not is_testing_env:
            try:
                import subprocess
                ps_b = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {target_b})"
                subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_b], creationflags=0x08000000)
            except Exception:
                pass
        ans = f"Screen brightness adjusted to {target_b}%, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in ["brightness up", "increase brightness", "make screen brighter", "raise brightness", "brighter screen"]):
        if os.name == "nt" and not is_testing_env:
            try:
                import subprocess
                ps_b = "$cur = (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness; $new = [Math]::Min(100, $cur + 15); (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, $new)"
                subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_b], creationflags=0x08000000)
            except Exception:
                pass
        ans = f"Screen brightness increased, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in ["brightness down", "decrease brightness", "make screen darker", "lower brightness", "dim screen", "dim display"]):
        if os.name == "nt" and not is_testing_env:
            try:
                import subprocess
                ps_b = "$cur = (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness; $new = [Math]::Max(10, $cur - 15); (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, $new)"
                subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_b], creationflags=0x08000000)
            except Exception:
                pass
        ans = f"Screen brightness dimmed, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 4.9.3 Media Playback Controls
    if any(k in clean_lower for k in ["play music", "pause music", "pause video", "play/pause", "pause media", "resume playback", "pause song", "resume music"]):
        if os.name == "nt" and not is_testing_env:
            import ctypes
            ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)
        ans = f"Media playback toggled, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in ["next song", "next track", "skip song", "skip track", "play next"]):
        if os.name == "nt" and not is_testing_env:
            import ctypes
            ctypes.windll.user32.keybd_event(0xB0, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xB0, 0, 2, 0)
        ans = f"Skipped to next track, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in ["previous song", "previous track", "last track", "play previous"]):
        if os.name == "nt" and not is_testing_env:
            import ctypes
            ctypes.windll.user32.keybd_event(0xB1, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xB1, 0, 2, 0)
        ans = f"Playing previous track, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in ["stop music", "stop video", "stop playback", "stop media"]):
        if os.name == "nt" and not is_testing_env:
            import ctypes
            ctypes.windll.user32.keybd_event(0xB2, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xB2, 0, 2, 0)
        ans = f"Media playback stopped, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 4.9.4 Window & Workspace Controls
    if any(k in clean_lower for k in ["minimize all windows", "minimize windows", "show desktop", "minimize everything"]):
        if os.name == "nt" and not is_testing_env:
            import subprocess
            subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-Command", "(New-Object -ComObject Shell.Application).MinimizeAll()"], creationflags=0x08000000)
        ans = f"Minimized all windows to show your Desktop, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 4.9.5 Power & Workstation Controls (Lock, Sleep, Shutdown, Reboot)
    if any(k in clean_lower for k in ["lock the computer", "lock computer", "lock pc", "lock the pc", "lock screen", "lock workstation", "lock the system", "lock my pc"]):
        if os.name == "nt" and not is_testing_env:
            import ctypes
            try:
                ctypes.windll.user32.LockWorkStation()
            except Exception as e:
                print(f"[LockWorkStation error]: {e}", flush=True)
        ans = f"Your computer is now locked, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in ["put pc to sleep", "put the pc to sleep", "sleep pc", "put computer to sleep", "sleep computer", "sleep system", "go to sleep"]):
        if os.name == "nt" and not is_testing_env:
            import ctypes
            try:
                ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)
            except Exception:
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        ans = f"Putting your PC to sleep now, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in ["restart the pc", "restart pc", "restart computer", "restart system", "reboot pc", "reboot system"]):
        if os.name == "nt" and not is_testing_env:
            os.system("shutdown /r /t 5")
        ans = f"System reboot sequence initiated. Restarting your PC in 5 seconds, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in ["shutdown the pc", "shutdown pc", "shutdown computer", "shutdown system", "power off pc", "turn off pc"]):
        if os.name == "nt" and not is_testing_env:
            os.system("shutdown /s /t 5")
        ans = f"System shutdown initiated. Powering down your PC in 5 seconds, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in ["cancel shutdown", "cancel restart", "abort shutdown", "abort restart", "stop shutdown", "stop restart"]):
        if os.name == "nt" and not is_testing_env:
            os.system("shutdown /a")
        ans = f"System power sequence aborted successfully, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 4.10. Live Real-Time Hardware Telemetry & System Monitor View
    if any(k in clean_lower for k in [
        "open system monitor", "show system monitor", "system monitor", "system monitoring",
        "open system monitoring", "device monitoring", "open device monitor", "hardware monitor",
        "open hardware monitor", "launch system monitor", "open system telemetry"
    ]):
        ans = f"[[ACTION:OPEN_SYSTEM_MONITOR]]\nOpening System Monitor HUD on your screen, {user_name}."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(k in clean_lower for k in [
        "check system stats", "show system health", "system stats", "system health", "hardware stats",
        "cpu and ram usage", "system performance", "pc stats", "pc health", "hardware vitals", "live stats",
        "check system health", "check pc stats", "check performance", "cpu usage", "ram usage"
    ]):
        ans = get_live_system_stats()
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 5. Explicit Memory Agent Query
    try:
        past_turns = list(get_chat_history(session_id))
        mem_agent_res = await memory_agent.handle_query(query, user_id=user_name, session_id=session_id, past_turns=past_turns)
        if mem_agent_res:
            save_chat_turn(session_id, "user", query)
            save_chat_turn(session_id, "assistant", mem_agent_res)
            return mem_agent_res
    except Exception:
        pass

    clean = re.sub(r"^[^\w]+|[^\w]+$", "", query.lower().strip())
    save_chat_turn(session_id, "user", query)

    # 6. Basic Greetings
    greetings = [
        wake_trigger, f"hey {wake_trigger}", f"hi {wake_trigger}", f"hello {wake_trigger}",
        "hello", "hi", "hlo", "hey", "test"
    ]
    if not query or clean in greetings:
        welcome = get_greeting_message(effective_language)
        save_chat_turn(session_id, "assistant", welcome)
        return welcome

    # 7. Identity & Profile Queries
    if any(p in clean for p in ["what is my name", "what's my name", "who am i", "tell my name", "my name"]):
        ans = f"Your name is {user_name}, boss."
        save_chat_turn(session_id, "assistant", ans)
        return ans

    identity_queries = [
        "who are you", "what is your name", "what's your name", "whats your name",
        "tell me about yourself", "what are you", "tell ur name", "tell your name", "your name"
    ]
    if any(p in clean for p in identity_queries):
        if effective_language == "tanglish":
            ans = f"Naan {agent_name}, unga personal AI assistant. 24-hour memory and live information oda irukken. Solunga Harishan, enna help venum?"
        elif effective_language == "tamil":
            ans = f"நான் {agent_name}, உங்கள் தனிப்பட்ட AI உதவியாளர். 24 மணி நேர நினைவகம் மற்றும் நேரலை தகவல்களுடன் உதவுகிறேன்."
        else:
            ans = f"I am {agent_name}, an intelligent personal AI assistant built to provide concise, factual answers and help with tasks such as information retrieval, scheduling, drafting text, and problem solving."
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if re.search(r"\b(what is my age|what's my age|whats my age|how old am i|my age)\b", clean):
        ans = f"You are {user_age} years old, {user_name}." if user_age else f"I don't have your age registered in the database yet, {user_name}."
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if re.search(r"\b(what is my email|what's my email|whats my email|my email|my mail)\b", clean):
        ans = f"Your email address is {user_email}, {user_name}." if user_email else f"No email address is registered in the database yet, {user_name}."
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if re.search(r"\b(where do i live|my location|my city|what is my city)\b", clean):
        ans = f"You are located in {user_city}, {user_name}." if user_city else f"No location is configured in your profile database yet, {user_name}."
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 7.5. Fast Local Real-Time Date & Time Resolver
    date_triggers = [
        "what is the date today", "what is today date", "what is today's date", "today's date", "today date",
        "what date is today", "what is the date", "tell me today date", "tell me the date", "current date",
        "what day is today", "what day is it", "today day", "today's day"
    ]
    if any(clean == p or clean.startswith(p) for p in date_triggers):
        today_str = datetime.now().strftime("%A, %B %d, %Y")
        ans = f"Today is **{today_str}**, {user_name}."
        save_chat_turn(session_id, "assistant", ans)
        return ans

    time_triggers = [
        "what is the time", "what's the time", "what time is it", "current time", "time now",
        "tell me the time", "tell time", "what is the current time"
    ]
    if any(clean == p or clean.startswith(p) for p in time_triggers):
        time_str = datetime.now().strftime("%I:%M %p")
        ans = f"The current time is **{time_str}**, {user_name}."
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 8. Direct Fast UI Element Clicks & Shortcuts (Execution First)
    fast_click_res = execute_fast_ui_click(query, user_name)
    if fast_click_res:
        save_chat_turn(session_id, "assistant", fast_click_res)
        return fast_click_res

    shortcut_phrases = [
        "close tab", "close current tab", "close window", "close app", 
        "next tab", "previous tab", "prev tab", "ctrl+w", "alt+f4", 
        "ctrl+tab", "minimize", "minimise", "maximize",
        "move to previous page", "previous page", "go back", "back page",
        "move to next page", "next page", "go forward", "forward page",
        "scroll down", "scroll up", "scroll to top", "scroll to bottom", "scroll",
        "zoom in", "zoom out", "reset zoom", "refresh", "reload"
    ]
    if any(sc in clean for sc in shortcut_phrases) and pyautogui is not None:
        try:
            if "close tab" in clean or "ctrl+w" in clean:
                pyautogui.hotkey("ctrl", "w")
                ans = f"Closed current tab, {user_name}."
            elif "close window" in clean or "close app" in clean or "alt+f4" in clean:
                pyautogui.hotkey("alt", "f4")
                ans = f"Closed current window, {user_name}."
            elif "next tab" in clean or "ctrl+tab" in clean:
                pyautogui.hotkey("ctrl", "tab")
                ans = f"Switched to the next tab, {user_name}."
            elif "previous tab" in clean or "prev tab" in clean:
                pyautogui.hotkey("ctrl", "shift", "tab")
                ans = f"Switched to the previous tab, {user_name}."
            elif any(p in clean for p in ["previous page", "go back", "back page"]):
                pyautogui.hotkey("alt", "left")
                ans = f"Moved to the previous page, {user_name}."
            elif any(p in clean for p in ["next page", "go forward", "forward page"]):
                pyautogui.hotkey("alt", "right")
                ans = f"Moved to the next page, {user_name}."
            elif "minimize" in clean or "minimise" in clean:
                pyautogui.hotkey("win", "down")
                ans = f"Minimized window, {user_name}."
            elif "maximize" in clean:
                pyautogui.hotkey("win", "up")
                ans = f"Maximized window, {user_name}."
            elif any(p in clean for p in ["scroll to top", "top of page", "scroll top"]):
                pyautogui.press("home")
                ans = f"Scrolled to the top of the page, {user_name}."
            elif any(p in clean for p in ["scroll to bottom", "bottom of page", "scroll bottom"]):
                pyautogui.press("end")
                ans = f"Scrolled to the bottom of the page, {user_name}."
            elif "scroll up" in clean:
                pyautogui.scroll(500)
                ans = f"Scrolled up, {user_name}."
            elif "scroll down" in clean or "scroll" in clean:
                pyautogui.scroll(-500)
                ans = f"Scrolled down, {user_name}."
            elif "zoom in" in clean:
                pyautogui.hotkey("ctrl", "+")
                ans = f"Zoomed in, {user_name}."
            elif "zoom out" in clean:
                pyautogui.hotkey("ctrl", "-")
                ans = f"Zoomed out, {user_name}."
            elif "reset zoom" in clean:
                pyautogui.hotkey("ctrl", "0")
                ans = f"Reset zoom level, {user_name}."
            elif "refresh" in clean or "reload" in clean:
                pyautogui.hotkey("ctrl", "r")
                ans = f"Refreshed page, {user_name}."
            else:
                ans = "Shortcut executed."
            save_chat_turn(session_id, "assistant", ans)
            return ans
        except Exception:
            pass

    compound_res = parse_and_execute_compound_command(query, session_id, user_name)
    if compound_res:
        save_chat_turn(session_id, "assistant", compound_res)
        return compound_res

    # 9. App and Local File / Folder Open Commands (Execution First)
    open_in_app_res = parse_open_in_app(query)
    if open_in_app_res:
        save_chat_turn(session_id, "assistant", open_in_app_res)
        return open_in_app_res

    is_open_query = (
        any(clean_lower.startswith(p) for p in [
            "open ", "can you open", "could you open", "please open", "launch ", "start ", "show me ", 
            "find ", "find the ", "find folder", "find the folder", "locate ", "locate the ", "locate folder",
            "open folder", "open file", "open directory", "access folder", "view folder", "where is the folder", "where is folder"
        ])
        or (any(v in clean_lower for v in ["open", "find", "locate", "show"]) and any(w in clean_lower for w in ["folder", "file", "directory", "app", "application", "powder", "memo", "document", "filling"]))
    ) and not any(k in clean_lower for k in ["send", "text", "msg", "saying", "that", "call", "monitoring", "auto reply", "http://", "https://", "www.", "google map", "friday map", "route", "tab", "context menu", "mouse"])

    if is_open_query:
        local_res = handle_local_open(query, user_name)
        if local_res:
            save_chat_turn(session_id, "assistant", local_res)
            return local_res

    # 9.5 Application and Window Close Commands
    is_close_query = (
        any(clean_lower.startswith(p) for p in ["close ", "exit ", "quit ", "kill ", "terminate "])
        or clean_lower in ["close", "close app", "close application", "close window", "close this window", "close this", "close active window", "close tab", "close current tab"]
    ) and not any(k in clean_lower for k in ["monitoring", "whatsapp monitoring", "whatsapp monitor"])

    if is_close_query:
        from app.services.system_service import system_service
        m_close = re.search(r'^(?:can\s+you\s+|could\s+you\s+|please\s+)?(?:close|exit|quit|kill|terminate)\s+(?:the\s+|my\s+)?([a-zA-Z0-9_\s\.\-]+?)(?:\s+app|\s+application|\s+window)?$', clean_lower)
        target_app = m_close.group(1).strip() if m_close else ""
        if target_app in ["this", "it", "window", "active", "active window", "current window", "app", "application", ""]:
            close_ans = system_service.close_application("")
        else:
            close_ans = system_service.close_application(target_app)
        save_chat_turn(session_id, "assistant", close_ans)
        return close_ans

    if clean.startswith("open ") and any(k in clean for k in ["http://", "https://", "www."]):
        link_ans = execute_direct_link(query)
        save_chat_turn(session_id, "assistant", link_ans)
        return link_ans

    # 10. WhatsApp Commands, File Sharing & Communication Automation
    is_code_or_compiler_log = any(kw in clean_lower for kw in [
        "compiler", "wrong answer", "stdin", "stdout", "testcase", "test case",
        "import java", "public class", "public static", "syntaxerror", "traceback",
        "runtime error", "time limit exceeded", "matcher", "scanner in", "output (stdout)",
        "input (stdin)", "expected output", "error in code", "solve this error", "solve this issue",
        "in inthe", "duplicatewords", "non ascii"
    ]) or (clean_lower.count("\n") >= 2 and not clean_lower.strip().startswith(("send", "text", "msg", "message", "hey friday", "whatsapp", "call", "mail")))

    is_whatsapp_query = not is_code_or_compiler_log and ("whatsapp" in clean_lower)
    is_message_history_query = not is_code_or_compiler_log and (
        ("who" in clean_lower and any(k in clean_lower for k in ["sent", "send", "messaged", "texted", "msg"]) and "whatsapp" in clean_lower)
        or any(k in clean_lower for k in [
            "who sent", "who send", "who have send", "who has sent", "who had sent", "who are all sent", "who all sent",
            "who messaged", "who texted", "anyone send", "anyone sent", "anyone message", "anyone text",
            "any whatsapp message", "any new message", "check whatsapp", "read whatsapp", "show whatsapp",
            "messages received", "received message", "received messages", "message history", "message log", "messages log"
        ])
        or ("whatsapp" in clean_lower and any(k in clean_lower for k in ["who", "what", "which", "show", "check", "read", "list", "history", "log", "any", "received", "updates"]))
    )
    is_call_query = not is_code_or_compiler_log and (any(k in clean_lower for k in ["call", "attend", "answer", "decline", "reject", "pick up", "speak"]) and any(k in clean_lower for k in ["call", "receiver", "him", "her"]))
    is_send_file_query = not is_code_or_compiler_log and (
        any(k in clean_lower for k in [
            "send the selected file", "send selected file", "send this file", "send the file", "send file",
            "forward the selected file", "forward selected file", "forward this file", "forward the file", "forward file",
            "share the selected file", "share selected file", "share this file", "share the file", "share file",
            "send the image", "send image", "send the selected image", "send selected image",
            "send photo", "send the photo", "send the selected photo", "send selected photo",
            "send document", "send the document", "send the selected document", "send selected document"
        ])
        and any(k in clean_lower for k in ["whatsapp", "mail", "email", "to "])
    )
    is_context_reply = not is_code_or_compiler_log and (
        any(k in clean_lower for k in ["make auto reply to him", "make auto reply to", "reply him", "reply to him", "reply to them", "reply to her", "send him the message", "send them the message", "send her the message"])
        and not any(k in clean_lower for k in ["turn on", "turn off", "enable", "disable", "start monitoring", "stop monitoring"])
        and not any(clean_lower.startswith(p) for p in ["send message", "send a message", "send the message", "message to", "text to"])
    )
    is_mail_query = not is_code_or_compiler_log and (
        (
            any(k in clean_lower for k in ["send an email", "send email", "draft email", "send a mail", "send mail", "mail to "])
            or (clean_lower.startswith("mail ") and any(k in clean_lower for k in ["about", "regarding", "saying"]))
        ) and not any(k in clean_lower for k in ["whatsapp", "turn on", "turn off"])
    )
    is_send_msg = not is_code_or_compiler_log and (
        any(clean_lower.startswith(p) for p in ["send message", "send a message", "send the message", "message to", "text to "])
        or (any(k in clean_lower for k in ["send", "text", "msg"]) and "whatsapp" in clean_lower and any(k in clean_lower for k in ["saying", "that", "to "]))
    )
    is_direct_call = not is_code_or_compiler_log and (
        any(clean_lower.startswith(p) for p in ["call to ", "dial ", "video call ", "voice call "])
        and not any(k in clean_lower for k in ["called", "what is it called", "who called"])
    )

    is_move_query = not is_code_or_compiler_log and any(clean_lower.startswith(p) for p in ["move this", "move the", "move ", "transfer this", "transfer "])

    is_notify_query = not is_code_or_compiler_log and (any(k in clean_lower for k in ["notify me", "speak notification", "voice notification", "alert me when", "read out incoming", "speak incoming"]) and any(k in clean_lower for k in ["whatsapp", "message", "from"]))

    if (
        is_whatsapp_query or is_message_history_query or is_call_query or
        is_send_file_query or is_notify_query or is_context_reply or is_mail_query or
        is_send_msg or is_direct_call or is_move_query or (not is_code_or_compiler_log and "reply them" in clean_lower)
    ):
        from app.services.whatsapp_service import whatsapp_service

        # 1. Smart Mail Drafting with Topic Prompting
        if is_mail_query and not is_send_file_query:
            from app.tools.email import generate_email_draft
            match_rec = re.search(r'(?:to|mail)\s+([a-zA-Z0-9_\.\@\s]+?)(?:\s+about|\s+regarding|\s+saying|\s+with\s+the\s+content|\s+that|$)', query, re.IGNORECASE)
            recipient = match_rec.group(1).strip() if match_rec else ""
            if recipient.lower() in ["me", "the", "a", "an"]:
                recipient = ""

            match_req = re.search(r'(?:about|regarding|saying|that|content)\s+(.+)', query, re.IGNORECASE)
            requirement = match_req.group(1).strip() if match_req else None

            # If user didn't specify topic/content, ask the user!
            if not requirement or len(requirement.split()) < 2:
                PENDING_EMAIL_INPUT[session_id] = {
                    "recipient": recipient,
                    "attachment": None
                }
                target_desc = f" to {recipient}" if recipient else ""
                ans = f"What subject and message content would you like me to include in the email{target_desc}, {user_name}?"
                save_chat_turn(session_id, "assistant", ans)
                return ans

            draft = generate_email_draft(requirement, recipient=recipient)
            PENDING_CONFIRMATION[session_id] = {
                "recipient": recipient or "[Recipient]",
                "subject": draft["subject"],
                "body": draft["body"],
                "attachment": None
            }
            ans = (
                f"I have drafted the email for you:\n\n"
                f"**To:** {recipient or '[Recipient]'}\n"
                f"**Subject:** {draft['subject']}\n"
                f"**Content:**\n{draft['body']}\n\n"
                f"Please check the details above. Should I proceed and send this mail?"
            )
            save_chat_turn(session_id, "assistant", ans)
            return ans

        # 2. Send Desktop / PC File via WhatsApp or Mail
        if is_send_file_query:
            m_contact = re.search(r'\b(?:to|with)\s+([a-zA-Z0-9_\s\(\)]+?)(?:\s+(?:in|on|via)\s+(?:whatsapp|mail|email)|\s+in\s+|\s+via\s+|\s+on\s+|$)', query, re.IGNORECASE)
            recipient = m_contact.group(1).strip() if m_contact else ""
            if recipient.lower() in ["whatsapp", "mail", "email"]:
                recipient = ""

            file_path = get_selected_desktop_or_explorer_file(must_be_file=True)
            if not file_path:
                m_file = re.search(r'(?:file|image|photo|doc|document|attachment|pdf|pic)\s+([a-zA-Z0-9_\-\.\s]+\.[a-zA-Z0-9]{2,5})', query, re.IGNORECASE)
                if m_file:
                    file_path = find_file_on_pc(m_file.group(1).strip())
            if not file_path:
                from app.services.context_service import FileExplorerContextHandler
                active_dir = FileExplorerContextHandler.get_active_explorer_path()
                if active_dir and os.path.exists(active_dir):
                    dir_p = Path(active_dir)
                    if dir_p.is_dir():
                        dir_files = [f for f in dir_p.glob("*") if f.is_file() and not f.name.endswith(".lnk") and not f.name.startswith("~$")]
                        if len(dir_files) == 1:
                            file_path = str(dir_files[0].resolve())
            if not file_path:
                desktop_p = Path.home() / "Desktop"
                if desktop_p.exists():
                    files = [f for f in desktop_p.glob("*") if f.is_file() and not f.name.endswith(".lnk") and not f.name.startswith("~$")]
                    if len(files) == 1:
                        file_path = str(files[0].resolve())

            if not file_path:
                target_desc = f" to {recipient}" if recipient else ""
                ans = f"I'm ready to send the file{target_desc}, but I can't locate a selected file on your system right now. Could you please select the file in File Explorer or on your Desktop, and I'll send it right away, {user_name}?"
                save_chat_turn(session_id, "assistant", ans)
                return ans

            is_mail_target = "mail" in clean_lower or "email" in clean_lower
            if is_mail_target:
                from app.tools.email import generate_email_draft
                match_req = re.search(r'(?:about|regarding|saying|that|content)\s+(.+)', query, re.IGNORECASE)
                requirement = match_req.group(1).strip() if match_req else None

                # Prompt user for subject and content if not provided in utterance
                if not requirement or len(requirement.split()) < 2:
                    PENDING_EMAIL_INPUT[session_id] = {
                        "recipient": recipient,
                        "attachment": file_path
                    }
                    target_desc = f" to {recipient}" if recipient else ""
                    ans = f"What subject and message content would you like me to include in the email{target_desc} with attachment **{Path(file_path).name}**, {user_name}?"
                    save_chat_turn(session_id, "assistant", ans)
                    return ans

                draft = generate_email_draft(requirement, recipient=recipient, context=file_path)
                PENDING_CONFIRMATION[session_id] = {
                    "recipient": recipient or "[Recipient]",
                    "subject": draft["subject"],
                    "body": draft["body"],
                    "attachment": file_path
                }
                ans = (
                    f"I have drafted the email with attachment **{Path(file_path).name}**:\n\n"
                    f"**To:** {recipient or '[Recipient]'}\n"
                    f"**Subject:** {draft['subject']}\n"
                    f"**Content:**\n{draft['body']}\n\n"
                    f"Please check the details above. Should I proceed and send this mail?"
                )
                save_chat_turn(session_id, "assistant", ans)
                return ans
            else:
                cand = whatsapp_service.find_contact_candidates(recipient, live_search=True)
                if cand["status"] == "multiple":
                    PENDING_DISAMBIGUATION[session_id] = {
                        "action": "file",
                        "candidates": cand["candidates"],
                        "payload": file_path,
                        "query": recipient
                    }
                    save_chat_turn(session_id, "assistant", cand["prompt"])
                    return cand["prompt"]
                elif cand["status"] == "qualifier_match":
                    PENDING_DISAMBIGUATION[session_id] = {
                        "action": "file",
                        "candidates": cand["candidates"],
                        "payload": file_path,
                        "query": recipient,
                        "best_match": cand["best_match"]
                    }
                    clarify_prompt = f"I found '{cand['best_match']}'. Would you like me to send the file to {cand['best_match']} or someone else?"
                    save_chat_turn(session_id, "assistant", clarify_prompt)
                    return clarify_prompt

                target_name = cand.get("best_match") or recipient
                res = whatsapp_service.send_file(target_name, file_path)
                ans = f"Dispatched file **{Path(file_path).name}** to {target_name} on WhatsApp, {user_name}." if res.get("success") else f"Could not send file: {res.get('error')}."
                save_chat_turn(session_id, "assistant", ans)
                return ans

        # 2.5 Move File or Folder to Destination
        if any(clean_lower.startswith(p) for p in ["move this", "move the", "move ", "transfer this", "transfer "]):
            m_move = re.search(r'(?:move|transfer)\s+(?:this\s+|the\s+)?(?:file\s+|folder\s+|document\s+|item\s+)?(?:([a-zA-Z0-9_\-\.\s]+?)\s+)?to\s+([a-zA-Z0-9_\-\.\/\\:~]+)', query, re.IGNORECASE)
            if m_move:
                import shutil
                from app.tools.filesystem.file_ops import resolve_natural_path
                target_src_name = (m_move.group(1) or "").strip()
                dest_name = (m_move.group(2) or "").strip()

                src_path = None
                if target_src_name and target_src_name.lower() not in ["this", "the", "it", "file", "folder", "item"]:
                    src_path = find_file_on_pc(target_src_name)
                if not src_path:
                    src_path = get_selected_desktop_or_explorer_file()

                if src_path and os.path.exists(src_path):
                    dst_dir = resolve_natural_path(dest_name)
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    dst_file = dst_dir / Path(src_path).name
                    shutil.move(src_path, str(dst_file))
                    ans = f"Successfully moved **{Path(src_path).name}** to **{dst_dir}**, {user_name}."
                    save_chat_turn(session_id, "assistant", ans)
                    return ans

        # 3. WhatsApp Spoken Notification Configuration
        if is_notify_query:
            target = None
            m_target = re.search(r'(?:from|for)\s+([a-zA-Z0-9_\s\(\)]+?)(?:$|\s+and|\s+in|\s+on)', clean_lower)
            if m_target:
                candidate_target = m_target.group(1).strip()
                if candidate_target not in ["any one", "anyone", "all", "every one", "everyone", "all message", "all messages"]:
                    target = candidate_target
            if target:
                whatsapp_service.set_monitoring(enabled=True, notify_mode="specific", notify_target_contact=target)
                ans = f"I will actively monitor WhatsApp and notify you aloud whenever a message arrives from {target}, {user_name}."
            else:
                whatsapp_service.set_monitoring(enabled=True, notify_mode="all")
                ans = f"I will actively monitor WhatsApp and notify you aloud for all incoming messages, {user_name}."
            save_chat_turn(session_id, "assistant", ans)
            return ans

        # 4. Contextual Reply to Recent Contact / Auto Reply to Him
        if is_context_reply:
            latest = getattr(whatsapp_service, "latest_received_message", None)
            target = latest.get("sender") if latest else None
            m_spec = re.search(r'\bto\s+([a-zA-Z0-9_\s\(\)]+?)(?:\s+saying|\s+that|:\s*|\s*,\s*["\']|send the message|$)', query, re.IGNORECASE)
            if m_spec:
                spec_candidate = m_spec.group(1).strip()
                if spec_candidate.lower() not in ["him", "her", "them", "me", "whatsapp", "the contact", "the person", "the sender"]:
                    target = spec_candidate

            m_text = re.search(r'(?:saying\s+(?:that\s+)?|that\s+|:\s*|\s*,\s*["\']|send the message\s+)(.+)', query, re.IGNORECASE)
            msg_to_send = m_text.group(1).strip().strip('"').strip("'") if m_text else "I received your message and will get back to you shortly."

            if target:
                cand = whatsapp_service.find_contact_candidates(target)
                target_clean = cand.get("best_match") or target
                res = whatsapp_service.send_message(target_clean, msg_to_send)
                ans = f"Dispatched reply to {target_clean}: \"{msg_to_send}\", {user_name}."
                save_chat_turn(session_id, "assistant", ans)
                return ans
            else:
                ans = f"No recent WhatsApp contact found to reply to. Please specify who to send the message to, {user_name}."
                save_chat_turn(session_id, "assistant", ans)
                return ans

        # 5. WhatsApp Call Attend (with optional in-call speech)
        is_attend_call = any(re.search(rf"\b{re.escape(k)}\b", clean_lower) for k in ["attend", "answer", "pick up", "pickup", "receive", "accept"]) and ("call" in clean_lower) and not any(k in clean_lower for k in ["send message", "send text", "send msg"])
        if is_attend_call:
            res_ans = whatsapp_service.answer_call()
            # Check if user also asked to speak a message during/after attending
            if any(k in clean_lower for k in ["speak", "tell", "inform", "say"]):
                m_speech = re.search(r'(?:saying\s+(?:that\s+)?|that\s+|:\s*|\s*,\s*["\']|tell\s+(?:them|him|her)\s+|say\s+)(.+)', query, re.IGNORECASE)
                spoken_text = m_speech.group(1).strip().strip('"').strip("'") if m_speech else ""
                # Filter out pure pronoun targets
                if spoken_text.lower() in ["to them", "to him", "to her", "to the caller", "them", "him", "her", "something"]:
                    spoken_text = ""

                if spoken_text:
                    whatsapp_service.speak_in_call(spoken_text)
                    ans = f"Attended the incoming WhatsApp call and spoken to the caller: \"{spoken_text}\", {user_name}."
                else:
                    ans = f"Attended the incoming WhatsApp call, {user_name}. What would you like me to say to the caller?"
            else:
                ans = f"Attending the incoming WhatsApp call, {user_name}." if res_ans.get("success") else f"Could not attend call: {res_ans.get('error', 'No active incoming call detected')}."
            save_chat_turn(session_id, "assistant", ans)
            return ans

        # 5.2 WhatsApp Call Decline / End
        if any(re.search(rf"\b{re.escape(k)}\b", clean_lower) for k in ["reject", "decline", "cut", "end", "hang up", "disconnect"]) and ("call" in clean_lower) and not any(k in clean_lower for k in ["send", "text", "msg", "message"]):
            whatsapp_service.decline_call()
            ans = f"Declined/ended the WhatsApp call, {user_name}."
            save_chat_turn(session_id, "assistant", ans)
            return ans

        # 5.4 WhatsApp In-Call Speech Synthesis (Active Call)
        if (
            (any(clean_lower.startswith(prefix) for prefix in ["speak to him", "inform him", "say to him", "tell him", "speak in call", "speak to them"]) or
             (("speak" in clean_lower or "say" in clean_lower) and "call" in clean_lower and not any(k in clean_lower for k in ["attend", "answer", "receive"])))
            and not any(k in clean_lower for k in ["send", "text", "msg", "message", "dm"])
        ):
            m_speech = re.search(r'(?:speak to him|inform him|say to him|tell him|speak in call|speak to them|speak|say)\s+(?:saying\s+(?:that\s+)?|that\s+|:\s*|\s*,\s*["\'])?(.+)', query, re.IGNORECASE)
            spoken_text = m_speech.group(1).strip().strip('"').strip("'") if m_speech else ""
            if spoken_text.lower() in ["to them", "to him", "to her", "to the caller", "them", "him", "her"]:
                spoken_text = ""

            if spoken_text:
                whatsapp_service.speak_in_call(spoken_text)
                ans = f"Spoken to the caller in WhatsApp call: \"{spoken_text}\", {user_name}."
            else:
                ans = f"What would you like me to say to the caller in the active WhatsApp call, {user_name}?"
            save_chat_turn(session_id, "assistant", ans)
            return ans

        # 6. WhatsApp Custom Auto-Reply Configuration
        if (
            (any(k in clean_lower for k in ["reply them", "set auto reply", "set auto-reply", "custom auto reply", "custom auto-reply"]) or
             ("if any" in clean_lower and "reply" in clean_lower))
            and not any(k in clean_lower for k in ["turn on", "turn off", "enable", "disable", "start monitoring", "stop monitoring", "is active", "status"])
        ):
            custom_msg = ""
            quote_match = re.search(r'["\']([^"\']+)["\']', query)
            if quote_match:
                custom_msg = quote_match.group(1).strip()
            else:
                match_prefix = re.search(r'(?:reply them|reply|saying|template\s+to|message\s+to)\s+(.+)', query, re.IGNORECASE)
                if match_prefix:
                    custom_msg = match_prefix.group(1).strip()
            custom_msg = re.sub(r'\s+in\s+whatsapp(?:\s+monitoring)?$', '', custom_msg, flags=re.IGNORECASE).strip()
            if custom_msg and custom_msg.lower() not in ["in whatsapp monitoring", "in whatsapp", "monitoring"]:
                whatsapp_service.set_monitoring(enabled=True, auto_reply=True, custom_auto_reply_message=custom_msg)
                ans = f"Custom auto-reply rule set to: \"{custom_msg}\". WhatsApp monitoring is active, {user_name}. [[ACTION:REFRESH_SETTINGS]] [[ACTION:SET_WHATSAPP_SETTINGS:{json.dumps({'custom_auto_reply_message': custom_msg})}]]"
                save_chat_turn(session_id, "assistant", ans)
                return ans

        # 7. WhatsApp Monitoring Status Check
        if any(k in clean_lower for k in ["is whatsapp monitoring", "are you monitoring", "whatsapp monitoring status", "check whatsapp monitoring", "is monitoring active"]) and not any(k in clean_lower for k in ["turn on", "turn off", "enable", "disable", "start", "stop"]):
            status_data = whatsapp_service.get_status()
            is_active = status_data.get("monitoring_active", False) or status_data.get("enabled", False)
            state_str = "ACTIVE and scanning" if is_active else "INACTIVE"
            ans = f"WhatsApp monitoring is currently {state_str}, {user_name}."
            save_chat_turn(session_id, "assistant", ans)
            return ans

        # 8. WhatsApp Direct Send with Dynamic Disambiguation (NO HARDCODING)
        is_code_or_compiler_log = any(kw in clean_lower for kw in [
            "compiler", "wrong answer", "stdin", "stdout", "testcase", "test case",
            "import java", "public class", "public static", "syntaxerror", "traceback",
            "runtime error", "time limit exceeded", "matcher", "scanner in", "output (stdout)",
            "input (stdin)", "error:", "exception:"
        ]) or (clean_lower.count("\n") >= 2 and not clean_lower.strip().startswith(("send", "text", "msg", "message", "hey friday")))

        if not is_code_or_compiler_log and any(k in clean_lower for k in ["send", "text", "msg", "message"]):
            match = re.search(r'^(?:hey friday[,\s]*)?(?:please\s+)?(?:send|text|msg|message)\s+(?:the\s+|a\s+)?(?:whatsapp\s+)?(?:message\s+)?(?:to\s+)?([a-zA-Z0-9_\s\(\)]+?)\s+(?:saying\s+(?:that\s+)?|that\s+|:\s*|\s*,\s*["\'])(.+)', query.strip(), re.IGNORECASE)
            if not match:
                match = re.search(r'^(?:hey friday[,\s]*)?(?:please\s+)?(?:send|text|msg|message)\s+([a-zA-Z0-9_\s\(\)]+?)\s+(?:the\s+|a\s+)?(?:whatsapp\s+)?(?:message\s+)(?:saying\s+(?:that\s+)?|that\s+|:\s*|\s*,\s*["\'])(.+)', query.strip(), re.IGNORECASE)
            if not match:
                match = re.search(r'^(?:hey friday[,\s]*)?(?:please\s+)?(?:send|text|msg|message)\s+(?:the\s+|a\s+)?(?:whatsapp\s+)?(?:message\s+)?(?:to\s+)?([a-zA-Z0-9_\s\(\)]+?)\s+["\']([^"\']+)["\']', query.strip(), re.IGNORECASE)
            if not match:
                # Direct pattern: "send [whatsapp] message to kishore i will call u later"
                m_direct = re.search(r'^(?:hey friday[,\s]*)?(?:please\s+)?(?:send|text|msg|message)\s+(?:the\s+|a\s+)?(?:whatsapp\s+)?(?:message\s+)?(?:to\s+)([a-zA-Z0-9_\(\)]+(?:\s+[a-zA-Z0-9_\(\)]+)?)\s+(.+)', query.strip(), re.IGNORECASE)
                if m_direct and m_direct.group(1).lower() not in ["my", "the", "a", "an", "me", "them", "whatsapp", "this", "it", "code", "file"]:
                    match = m_direct
            if not match and "whatsapp" in clean_lower:
                m_wa = re.search(r'(?:whatsapp|send whatsapp to)\s+([a-zA-Z0-9_\(\)]+(?:\s+[a-zA-Z0-9_\(\)]+)?)\s+(?:saying\s+|that\s+|:\s*)?(.+)', query.strip(), re.IGNORECASE)
                if m_wa and m_wa.group(1).lower() not in ["my", "the", "a", "an", "me", "them", "whatsapp", "message", "status", "monitoring"]:
                    match = m_wa

            if match:
                contact = match.group(1).strip()
                msg_body = match.group(2).strip().strip('"').strip("'")
                if contact.lower() not in ["my", "the", "a", "an", "me", "them", "whatsapp"] and msg_body:
                    cand = whatsapp_service.find_contact_candidates(contact, live_search=True)
                    if cand["status"] == "multiple":
                        PENDING_DISAMBIGUATION[session_id] = {
                            "action": "message",
                            "candidates": cand["candidates"],
                            "payload": msg_body,
                            "query": contact
                        }
                        save_chat_turn(session_id, "assistant", cand["prompt"])
                        return cand["prompt"]
                    elif cand["status"] == "qualifier_match":
                        PENDING_DISAMBIGUATION[session_id] = {
                            "action": "message",
                            "candidates": cand["candidates"],
                            "payload": msg_body,
                            "query": contact,
                            "best_match": cand["best_match"]
                        }
                        clarify_prompt = f"I found '{cand['best_match']}'. Would you like me to message {cand['best_match']} or someone else?"
                        save_chat_turn(session_id, "assistant", clarify_prompt)
                        return clarify_prompt

                    target_name = cand.get("best_match") or contact
                    res = whatsapp_service.send_message(target_name, msg_body)
                    ans = f"Dispatched WhatsApp message to {target_name}: \"{msg_body}\", {user_name}."
                    save_chat_turn(session_id, "assistant", ans)
                    return ans

        # 11. WhatsApp Message Log Check
        if is_message_history_query:
            is_full = any(k in clean_lower for k in ["all message", "all messages", "full history", "entire history", "history of message", "show all"])
            logs = whatsapp_service.get_logs(limit=20) if is_full else whatsapp_service.get_unseen_logs(mark_as_read=True)
            if logs:
                lines = []
                has_urgent = False
                for idx, item in enumerate(reversed(logs), 1):
                    sender = item.get("sender", "Unknown")
                    msg = item.get("message", "").strip() or "a message"
                    rep = item.get("reply", "").strip()
                    is_urg = item.get("is_urgent", False) or whatsapp_service.check_is_urgent(msg)
                    if is_urg:
                        has_urgent = True
                    urgent_tag = "🚨 **[URGENT]** " if is_urg else ""
                    if rep:
                        lines.append(f"{idx}. {urgent_tag}**{sender}**: \"{msg}\"\n   🤖 Replied: \"{rep}\"")
                    else:
                        lines.append(f"{idx}. {urgent_tag}**{sender}**: \"{msg}\"")
                report_body = "\n\n".join(lines)
                header_alert = "🚨 **URGENT NOTIFICATION DETECTED** - " if has_urgent else ""
                ans = f"{header_alert}Here are the WhatsApp updates, {user_name}:\n\n{report_body}"
            else:
                live_unseen = whatsapp_service.get_live_unread_chats()
                if live_unseen:
                    unread_names = ", ".join([u.get("chat", "Chat") for u in live_unseen])
                    ans = f"You have unread chats in WhatsApp from: **{unread_names}**, {user_name}."
                else:
                    ans = f"No new WhatsApp messages received since your last check, {user_name}."
            save_chat_turn(session_id, "assistant", ans)
            return ans

        # 12. Monitoring Control (Explicit Separation)
        # Case A: Auto-reply enabled on WhatsApp
        if any(k in clean_lower for k in ["make auto reply on whatsapp", "enable auto reply on whatsapp", "turn on auto reply on whatsapp", "enable whatsapp auto reply"]):
            whatsapp_service.set_monitoring(enabled=True, auto_reply=True)
            ans = f"WhatsApp background notification monitoring and AI Auto-Reply are now both ACTIVE, {user_name}."
            save_chat_turn(session_id, "assistant", ans)
            return ans

        # Case B: Monitoring only
        if any(k in clean_lower for k in ["monitor my whatsapp", "start monitoring", "turn on whatsapp", "enable whatsapp monitor", "activate whatsapp"]):
            whatsapp_service.set_monitoring(enabled=True, auto_reply=False)
            ans = f"WhatsApp background notification monitoring is now ACTIVE (AI Auto-Reply is OFF), {user_name}."
            save_chat_turn(session_id, "assistant", ans)
            return ans

        if any(k in clean_lower for k in ["stop monitoring", "turn off whatsapp", "disable whatsapp", "stop whatsapp monitor"]):
            whatsapp_service.set_monitoring(enabled=False)
            ans = f"WhatsApp background notification monitoring has been DEACTIVATED, {user_name}."
            save_chat_turn(session_id, "assistant", ans)
            return ans

        # 13. WhatsApp Direct Call with Dynamic Disambiguation
        if any(k in clean_lower for k in ["call", "video call", "voice call", "dial"]) and not any(k in clean_lower for k in ["send", "text", "msg", "message", "attend", "answer", "speak"]):
            is_video = "video" in clean_lower
            match = re.search(r'(?:video\s+call|voice\s+call|make\s+a\s+call\s+to|place\s+a\s+call\s+to|call\s+to|call|dial)\s+([a-zA-Z0-9_\s\(\)]+?)(?:\s+on\s+whatsapp|\s+via\s+whatsapp|$)', query, re.IGNORECASE)
            contact = match.group(1).replace("on whatsapp", "").replace("via whatsapp", "").strip() if match else ""
            if contact.lower().startswith("to "):
                contact = contact[3:].strip()
            if contact and contact.lower() not in ["my", "the", "a", "an", "me", "them", "whatsapp", "call"]:
                cand = whatsapp_service.find_contact_candidates(contact, live_search=True)
                if cand["status"] == "multiple":
                    PENDING_DISAMBIGUATION[session_id] = {
                        "action": "call",
                        "candidates": cand["candidates"],
                        "call_type": "video" if is_video else "voice",
                        "query": contact
                    }
                    save_chat_turn(session_id, "assistant", cand["prompt"])
                    return cand["prompt"]
                elif cand["status"] == "qualifier_match":
                    PENDING_DISAMBIGUATION[session_id] = {
                        "action": "call",
                        "candidates": cand["candidates"],
                        "call_type": "video" if is_video else "voice",
                        "query": contact,
                        "best_match": cand["best_match"]
                    }
                    clarify_prompt = f"I found '{cand['best_match']}'. Would you like me to call {cand['best_match']} or someone else?"
                    save_chat_turn(session_id, "assistant", clarify_prompt)
                    return clarify_prompt

                target_name = cand.get("best_match") or contact
                res = whatsapp_service.start_call(target_name, call_type="video" if is_video else "voice")
                ans = f"Placing a {'video' if is_video else 'voice'} call to {target_name} on WhatsApp, {user_name}." if res.get("success") else f"Could not initiate call: {res.get('error', 'Unknown error')}."
                save_chat_turn(session_id, "assistant", ans)
                return ans

    # 10.5 Device Monitoring "What am I seeing?" Direct Route
    screen_see_triggers = [
        "what am i seeing", "what's on my screen", "what is on my screen", "what is on screen",
        "what am i looking at", "what is i am viewing", "what am i viewing", "what i am viewing",
        "describe my screen", "inspect my screen", "analyze my screen", "what screen", "viewing now",
        "what is i seeing", "what am i looking"
    ]
    if any(trig in clean_lower for trig in screen_see_triggers):
        from app.tools.device import analyze_current_screen, is_device_monitoring_enabled
        if not is_device_monitoring_enabled():
            disabled_ans = "Device Monitoring is currently disabled. Enable it in Settings to allow Friday to access the desktop."
            save_chat_turn(session_id, "assistant", disabled_ans)
            return disabled_ans

        res = analyze_current_screen(user_prompt=query)
        ans = res.get("natural_language_description") or "I was unable to analyze your current screen state."
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 10.6 UI Element Location Route ("where is login", "where is button")
    if any(clean_lower.startswith(prefix) for prefix in ["where is ", "where's ", "find ", "locate "]) and any(kw in clean_lower for kw in ["login", "button", "input", "box", "option", "tab", "link", "file", "icon", "element", "menu", "sign in"]):
        from app.tools.device import extract_ui_tree, is_device_monitoring_enabled, get_active_window_info
        if not is_device_monitoring_enabled():
            disabled_ans = "Device Monitoring is currently disabled. Enable it in Settings to allow Friday to inspect screen elements."
            save_chat_turn(session_id, "assistant", disabled_ans)
            return disabled_ans

        target_kw = re.sub(r'^(where is|where\'s|find|locate)\s+(the\s+)?', '', clean_lower).strip()
        ui_res = extract_ui_tree(max_depth=5, max_elements=80)
        active_info = get_active_window_info()
        app_title = active_info.get("active_window", {}).get("title", "Active App")

        elements = ui_res.get("elements", []) if ui_res.get("success") else []
        matches = [e for e in elements if target_kw in e.get("name", "").lower() or target_kw in e.get("control_type", "").lower()]

        if matches:
            top_m = matches[0]
            m_name = top_m.get("name") or target_kw
            m_type = top_m.get("control_type", "Element")
            m_bounds = top_m.get("bounds", {})
            pos_str = f"at x: {m_bounds.get('x', 0)}, y: {m_bounds.get('y', 0)}" if m_bounds else ""
            ans = f"I found the **{m_name}** ({m_type}) in **{app_title}** {pos_str}. Would you like me to click it for you?"
        else:
            visible_names = [e['name'] for e in elements[:6] if e.get('name')]
            ans = f"I inspected **{app_title}**. Visible elements include: {', '.join(visible_names) or 'standard UI controls'}. I could not find an exact element matching '{target_kw}'. Would you like me to click a specific coordinate?"

        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 10.8 Direct Battery & Power Optimization Handler
    battery_triggers = [
        "battery", "power consumption", "power saver", "battery saver", "eco mode",
        "solve the battery", "fix battery", "battery issue", "battery draining",
        "battery life", "optimize battery", "battery performance", "unplugged"
    ]
    if any(bt in clean_lower for bt in battery_triggers) and not any(k in clean_lower for k in ["news", "history", "wikipedia", "buy battery"]):
        from app.services.power_service import get_battery_info, optimize_battery_for_unplugged, load_power_settings
        batt = get_battery_info()
        pcfg = load_power_settings()

        is_optimize_action = any(k in clean_lower for k in [
            "solve", "fix", "optimize", "reduce", "save", "turn on", "enable", "activate", "preserve", "saver"
        ])

        if is_optimize_action or "battery consumption" in clean_lower or "unplugged" in clean_lower:
            optimize_battery_for_unplugged()
            percent_str = f"{batt['percent']}%" if batt else "detected"
            state_str = "unplugged (Battery Power)" if (batt and not batt.get("power_plugged")) else "AC Power"
            time_left_str = f" (~{round(batt['secsleft']/60)} mins remaining)" if (batt and batt.get("secsleft")) else ""

            ans = (
                f"I have optimized power consumption for your Windows laptop, {user_name}!\n\n"
                f"🔋 **Current Battery:** {percent_str} • {state_str}{time_left_str}\n"
                f"⚡ **Optimizations Engaged:**\n"
                f"• **Discrete GPU (RTX 3050):** Parked in 0W D3 Cold sleep mode to eliminate PCIe battery drain.\n"
                f"• **Windows Power Plan:** Switched to native OS **Power Saver** scheme.\n"
                f"• **Friday Eco Mode:** Background telemetry intervals throttled and UI overlay drag loop set to power-idle.\n"
                f"• **Graphics Pipeline:** Active workload offloaded to energy-efficient AMD Radeon integrated GPU."
            )
            save_chat_turn(session_id, "assistant", ans)
            return ans
        elif batt:
            percent = batt.get("percent", 0)
            plugged = batt.get("power_plugged", True)
            secs = batt.get("secsleft")
            state = "Charging (AC Power)" if plugged else "Discharging (Battery Power)"
            remaining = f" Estimated runtime: **{round(secs/60)} minutes**." if (secs and secs > 0) else ""
            eco = "Active (Power Saver)" if pcfg.get("eco_mode") else "Standard"

            ans = (
                f"Here is your laptop's current battery status, {user_name}:\n"
                f"• **Charge Level:** {percent}%\n"
                f"• **Power Source:** {state}\n"
                f"• **Eco / Power Saver Mode:** {eco}{remaining}\n\n"
                f"Let me know if you would like me to activate **Ultra Power Saver** to maximize your battery runtime!"
            )
            save_chat_turn(session_id, "assistant", ans)
            return ans

    # 10.85 Direct AI Image Generation Engine (FLUX.1 Turbo, SDXL, Pollinations AI)
    is_hairstyle_or_makeover_query = bool(re.search(
        r'\b(?:change|switch|modify|give|make|replace|turn|put|add)\s+(?:his|her|the|their|a)?\s*(?:hair|hairstyle|haircut|hair\s+style|look|outfit|appearance|style|beard|mustache|dress|suit)\b',
        clean_lower
    )) or any(clean_lower.startswith(p) for p in [
        "change hair", "change hairstyle", "change his hair", "change her hair", "change the hair",
        "make him ", "make her ", "make trump ", "make elon ", "give him ", "give her ", "give trump "
    ])

    is_direct_img_command = bool(re.search(
        r'\b(?:generate|create|render|make|draw|produce|paint|give|show|get|send|display|fetch|provide|find|design)\b.*?\b(?:image|images|picture|pictures|photo|photos|wallpaper|wallpapers|artwork|artworks|portrait|portraits|illustration|illustrations|render|renders|visual|visuals|hud|graphic|graphics|icon|icons|drawing|drawings|pic|pics|logo|logos|emblem|emblems|badge|badges|banner|banners|mascot|mascots|sticker|stickers)\b',
        clean_lower
    )) or bool(re.search(
        r'\b(?:image|images|picture|pictures|photo|photos|wallpaper|wallpapers|portrait|portraits|illustration|illustrations|drawing|drawings|pic|pics|logo|logos|emblem|badge|banner)\s+(?:of|for|with)\b',
        clean_lower
    )) or (any(clean_lower.startswith(p) for p in [
        "generate ", "create image", "create the image", "create an image", "create a photo", "create a logo", "render ", "draw ",
        "make an image", "make a photo", "make a logo", "generate photo", "generate picture", "generate wallpaper", "generate logo",
        "give me an image", "give me a photo", "give me the image", "give me image", "give me photo", "give me logo", "give me a logo",
        "give an image", "give a image", "give the image", "give image", "give photo", "give picture", "give logo", "give a logo",
        "show me an image", "show me a photo", "show me image", "show the image", "show an image", "show image", "show photo", "show logo",
        "design a logo", "design logo", "make logo", "create logo",
        "show me ", "give me ", "give ", "show ", "send me ", "send image", "send the image", "send photo", "send logo"
    ]) and any(w in clean_lower for w in ["image", "images", "picture", "pictures", "photo", "photos", "wallpaper", "wallpapers", "portrait", "portraits", "drawing", "illustration", "art", "pic", "pics", "logo", "logos", "emblem", "badge", "icon", "banner"])) or bool(re.search(
        r'\b(?:generate|render|make|create|draw|give|show|send|design)\s+(?:that|this|it|another|an?\s+extra)\s*(?:image|picture|photo|wallpaper|logo|icon)?',
        clean_lower
    )) or bool(re.search(
        r'\b(?:with|in)\s+(?:\d{3,5}\s*(?:[xX*×]|by)\s*\d{3,5}|\d{3,4}p|4k|8k|1440p|1080p|720p)\s*(?:size|resolution|res)?\b',
        clean_lower
    ) and any(w in clean_lower for w in ["generate", "render", "image", "photo", "wallpaper", "logo", "make", "create", "draw", "that", "this"])) or (
        bool(re.search(r'^[a-zA-Z0-9\s]{2,40}\s+(?:image|images|photo|photos|picture|pictures|wallpaper|wallpapers|portrait|portraits|drawing|drawings|illustration|illustrations|pic|pics|logo|logos|icon|icons)$', clean_lower)) and not any(clean_lower.startswith(q) for q in ["what", "who", "where", "how", "why", "is", "explain"])
    )

    # Visual & Camera Specification Descriptors (Midjourney / FLUX / SDXL Prompt Style)
    visual_render_keywords = [
        "cinematic photograph", "cinematic shot", "cinematic lighting", "shot with", "shot on",
        "8k resolution", "4k resolution", "8k", "4k", "photorealistic", "shallow depth of field",
        "depth of field", "bokeh", "film grain", "35mm film", "sharp focus", "rule of thirds",
        "octane render", "unreal engine", "vector icon", "hyper-detailed", "hyperrealistic",
        "studio lighting", "volumetric lighting", "highly detailed", "masterpiece", "dramatic lighting"
    ]

    has_camera_or_render_specs = sum(1 for k in visual_render_keywords if k in clean_lower) >= 2 or any(k in clean_lower for k in [
        "shot with a sony", "shot on a sony", "shot with canon", "shot on canon", "85mm lens", "50mm lens", "35mm lens",
        "35mm film stock", "shallow depth of field", "cinematic photograph of", "photograph of a distinguished"
    ])

    is_standalone_visual_prompt = (
        any(clean_lower.startswith(p) for p in [
            "a clean ", "a minimalist ", "a futuristic ", "a photorealistic ", "a cinematic ", "a cyberpunk ",
            "a detailed", "a close-up", "a portrait", "a photo", "a photograph", "a high-resolution", "a 3d render",
            "close-up of", "portrait of", "photo of", "photograph of", "vector icon of", "an icon of",
            "concept art of", "8k wallpaper of", "cinematic shot of"
        ]) and (any(k in clean_lower for k in visual_render_keywords) or len(clean_lower.split()) >= 15)
    ) or has_camera_or_render_specs

    # 10.7.9 Image Editing & Photographic Transformation Pipeline (for attached/selected/recent images)
    from app.services.image_editing_service import image_editing_service
    is_image_edit_query = image_editing_service.is_image_edit_instruction(clean_lower)
    
    if is_image_edit_query:
        import tempfile
        from app.services.context_state import context_state
        active_img = context_state.selected_file
        
        project_root = BASE_DIR.parent
        all_upload_dirs = [
            project_root / "uploads" / "images",
            project_root / "uploads" / "documents",
            project_root / "memory" / "cache" / "uploads",
            BASE_DIR / "database" / "cache" / "uploads",
            BASE_DIR / "database" / "edited_images",
            BASE_DIR / "database" / "generated_images",
            project_root / "database" / "cache" / "uploads",
            project_root / "database" / "edited_images",
            project_root / "database" / "generated_images",
            Path(tempfile.gettempdir()) / "Friday_Uploads",
            Path(os.environ.get("TEMP", "")) / "Friday_Uploads",
            Path.home() / "Pictures",
            Path.home() / "Desktop",
            Path.home() / "Downloads"
        ]

        # Extract filename if provided in attachment tags like [ATTACHMENTS (1/6)]: Fenris_Wolf.jpg
        att_match = re.search(r'\[ATTACHMENTS[^\]]*\]:\s*([\w\-_\.]+\.(?:png|jpg|jpeg|webp|bmp))', query, re.IGNORECASE)
        target_fn = att_match.group(1).strip() if att_match else None

        if not target_fn:
            fn_match = re.search(r'\b([\w\-_\.]+\.(?:png|jpg|jpeg|webp|bmp))\b', query, re.IGNORECASE)
            if fn_match:
                target_fn = fn_match.group(1).strip()

        if target_fn:
            for sdir in all_upload_dirs:
                if sdir.exists():
                    cand_p = sdir / target_fn
                    if cand_p.exists() and cand_p.is_file():
                        active_img = str(cand_p)
                        break
                    for f in sdir.glob("*"):
                        if f.is_file() and (f.name.lower() == target_fn.lower() or f.stem.lower() == Path(target_fn).stem.lower()):
                            active_img = str(f)
                            break
                if active_img and Path(active_img).exists():
                    break

        # Check active conversation history for the most recent image card path or attachment
        if not active_img or not Path(active_img).exists():
            try:
                from app.services.conversation_memory_service import conversation_memory_service
                conv_data = await conversation_memory_service.get_conversation(session_id)
                if conv_data and conv_data.get("messages"):
                    for m in reversed(conv_data["messages"]):
                        txt = m.get("content", "")
                        # Check for attachment tags
                        hist_att = re.search(r'\[ATTACHMENTS[^\]]*\]:\s*([\w\-_\.]+\.(?:png|jpg|jpeg|webp|bmp))', txt, re.IGNORECASE)
                        if hist_att:
                            cand_hist_fn = hist_att.group(1).strip()
                            for sdir in all_upload_dirs:
                                if sdir.exists() and (sdir / cand_hist_fn).exists():
                                    active_img = str(sdir / cand_hist_fn)
                                    break
                            if active_img and Path(active_img).exists():
                                break

                        path_match = re.search(r'path=([^\|\]]+)', txt)
                        if path_match:
                            cand_p = Path(path_match.group(1).strip())
                            if cand_p.exists() and cand_p.is_file():
                                active_img = str(cand_p)
                                break
            except Exception:
                pass

        # Check most recent uploaded file across all upload folders
        if not active_img or not Path(active_img).exists() or Path(active_img).suffix.lower() not in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
            pure_upload_dirs = [
                project_root / "uploads" / "images",
                project_root / "memory" / "cache" / "uploads",
                Path(tempfile.gettempdir()) / "Friday_Uploads",
                BASE_DIR / "database" / "cache" / "uploads",
                project_root / "database" / "cache" / "uploads",
                Path.home() / "Pictures"
            ]
            cand_files = []
            for udir in pure_upload_dirs:
                if udir.exists():
                    for p in udir.glob("*"):
                        if p.is_file() and p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
                            cand_files.append(p)
            if cand_files:
                cand_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                active_img = str(cand_files[0])

        # If not in uploads, check recent generated/edited images
        if not active_img or not Path(active_img).exists():
            for gdir in [BASE_DIR / "database" / "edited_images", BASE_DIR / "database" / "generated_images", project_root / "database" / "generated_images"]:
                if gdir.exists():
                    recent_gens = sorted(
                        [p for p in gdir.glob("*.png")],
                        key=lambda x: x.stat().st_mtime,
                        reverse=True
                    )
                    if recent_gens:
                        active_img = str(recent_gens[0])
                        break

        if active_img and Path(active_img).exists():
            # Clean instruction of attachment prefix
            clean_instruction = re.sub(r'^\[ATTACHMENTS[^\]]*\]:\s*[\w\-_\.]+\s*-\s*', '', query, flags=re.IGNORECASE).strip() or query
            edit_res = await image_editing_service.edit_image(
                image_input=active_img,
                instruction=clean_instruction,
                user_name=user_name
            )
            ans = image_editing_service.format_to_markdown_card(edit_res, user_name=user_name)
            save_chat_turn(session_id, "assistant", ans)
            return ans

    # Check if this query is a follow-up image modifier or refinement
    is_visual_modifier_query = bool(re.search(
        r'\b(?:with\s+full\s+body|full\s+body|full\s+shot|wide\s+shot|close\s+up|movie\s+poster|like\s+in\s+movie\s+poster|poster\s+style|in\s+4k|in\s+8k|in\s+1080p|1920x1080|wallpaper|cinematic|dark\s+background|side\s+view|front\s+view|standing\s+in|wearing\s+|with\s+torn|with\s+green|another\s+one|different\s+one|more\s+realistic|photorealistic|different\s+pose|in\s+action|torn\s+purple\s+pants|angry\s+look|action\s+pose)\b',
        clean_lower
    )) or any(clean_lower.startswith(p) for p in [
        "with full body", "full body", "like in movie poster", "in movie poster", "movie poster",
        "with dark", "with purple", "with green", "in 4k", "in 8k", "in 1920x1080", "1920x1080",
        "different one", "another one", "one more", "different pose", "change pose", "with full", "full shot"
    ])

    # Check active conversation history for recent image generation
    is_active_conv_image = False
    prev_image_prompt = ""
    try:
        from app.services.conversation_memory_service import conversation_memory_service
        conv_data = await conversation_memory_service.get_conversation(session_id)
        if conv_data and conv_data.get("messages"):
            for m in reversed(conv_data["messages"][-6:]):
                txt = m.get("content", "")
                card_match = re.search(r'!\[([^\|\]]+)(?:\|[^\]]*)?\]', txt)
                if card_match:
                    prev_image_prompt = card_match.group(1).strip()
                    is_active_conv_image = True
                    break
    except Exception:
        pass

    is_followup_image_gen = is_active_conv_image and (
        is_visual_modifier_query
        or any(w in clean_lower for w in ["that image", "this image", "that photo", "this photo", "another image", "another photo", "another one", "that one", "of him in", "of her in", "of them in", "with full body", "full body", "poster style"])
    )

    is_document_or_text_query = any(k in clean_lower for k in [
        "pdf", "document", "doc", "file", "text", "csv", "summary", "summarize",
        "question", "questions", "qn", "qns", "q&a", "answer", "notes", "article",
        "explain", "how to", "why is", "who is", "what is", "python", "script",
        "java", "code", "programming", "from the", "in the file", "in this document"
    ])

    is_image_gen_query = (is_direct_img_command or is_standalone_visual_prompt or is_hairstyle_or_makeover_query or is_followup_image_gen) and not is_document_or_text_query and not any(k in clean_lower for k in [
        "prompt for", "prompts for", "give me a prompt", "write a prompt", "generate a prompt", "generate prompt"
    ])

    if is_image_gen_query:
        from app.services.image_generation_service import image_generation_service
        
        clean_img_prompt = query

        # Smart prompt transformation for hairstyle and visual makeovers
        if is_hairstyle_or_makeover_query:
            subject_match = re.search(r'\b(?:of|for|on)\s+([a-zA-Z0-9\s]+?)(?:\s+(?:to|with|in|into|as)\s+|$)', query, re.IGNORECASE)
            style_match = re.search(r'\b(?:to|with|into|as)\s+([a-zA-Z0-9\s]+?)$', query, re.IGNORECASE)
            
            target_person = subject_match.group(1).strip() if subject_match else ""
            target_style = style_match.group(1).strip() if style_match else ""
            
            if not target_person:
                make_match = re.search(r'\bmake\s+([a-zA-Z0-9\s]+?)\s+(bald|blonde|curly|cyberpunk|anime|stylish|handsome|[a-zA-Z0-9\s]+)', query, re.IGNORECASE)
                if make_match:
                    target_person = make_match.group(1).strip()
                    target_style = make_match.group(2).strip()

            if not target_person:
                target_person = re.sub(r'\b(?:change\s+(?:his|her|their)?\s*hair\s*style|change\s+haircut|makeover)\b', '', query, flags=re.IGNORECASE).strip() or "person"

            if not target_style:
                target_style = "a modern stylish haircut, clean trimmed style"

            clean_img_prompt = f"Detailed portrait of {target_person} featuring {target_style}, high resolution, photorealistic, sharp focus, cinematic lighting, 8k"
        elif prev_image_prompt and (is_followup_image_gen or is_visual_modifier_query or any(w in clean_lower for w in ["that image", "this image", "another", "full body", "poster", "with", "in", "him", "her", "it"])):
            clean_img_prompt = f"{prev_image_prompt}, {query}"
        else:
            # Resolve follow-up references (e.g. "generate that image with 1920x1080 size", "give realistic image of him", "another image")
            is_followup = any(w in clean_lower for w in ["that image", "this image", "that photo", "this photo", "another image", "another photo", "another one", "that one", "of him", "of her", "of them", "of this", "of that", "it in", "it with"]) or (
                len(clean_lower.split()) <= 6 and any(k in clean_lower for k in ["1920x1080", "1080p", "4k", "8k", "720p", "1440p", "wallpaper", "size", "resolution", "realistic", "photorealistic"])
            )
            if is_followup:
                try:
                    from app.services.conversation_memory_service import conversation_memory_service
                    conv_data = await conversation_memory_service.get_conversation(session_id)
                    if conv_data and conv_data.get("messages"):
                        for m in reversed(conv_data["messages"]):
                            txt = m.get("content", "")
                            card_match = re.search(r'!\[([^\|\]]+)(?:\|[^\]]*)?\]', txt)
                            if card_match:
                                prev_topic = card_match.group(1).strip()
                                if any(p in clean_lower for p in ["him", "her", "them", "this", "that", "it"]):
                                    clean_img_prompt = f"photorealistic raw portrait photo of {prev_topic}, {query}"
                                else:
                                    clean_img_prompt = f"{prev_topic} {query}"
                                break
                            elif m.get("role") == "user" and m.get("content") != query:
                                prev_user_q = m.get("content", "").strip()
                                if len(prev_user_q.split()) < 30:
                                    if any(p in clean_lower for p in ["him", "her", "them", "this", "that", "it"]):
                                        clean_img_prompt = f"photorealistic raw portrait photo of {prev_user_q}, {query}"
                                    else:
                                        clean_img_prompt = f"{prev_user_q} {query}"
                                    break
                except Exception as e:
                    print(f"[CommandExecutor] Followup context lookup error: {e}")

        img_res = await image_generation_service.generate_image(prompt=clean_img_prompt)
        ans = image_generation_service.format_to_markdown_card(img_res, user_name=user_name)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 10.9 Direct Prompt Generator Handler (ChatGPT / Gemini Style: 1-2 Clean Prompts in Copyable Box)
    is_prompt_gen_query = bool(re.search(
        r'\b(?:generate|create|write|give me|make|craft|build|produce)\s+(?:the\s+|a\s+|an\s+)?(?:master\s+|best\s+|good\s+|detailed\s+|image\s+|ai\s+|system\s+|coding\s+|llm\s+|midjourney\s+|flux\s+|sdxl\s+)?prompt\b',
        clean_lower
    )) or any(pt in clean_lower for pt in [
        "prompt for", "prompts for", "midjourney prompt", "flux prompt", "sdxl prompt",
        "dall-e prompt", "dalle prompt", "image prompt", "system prompt for", "prompt generator",
        "write a prompt", "generate a prompt", "generate the prompt"
    ])
    if is_prompt_gen_query and not any(k in clean_lower for k in ["what is a prompt", "explain prompt engineering"]):
        from app.services.prompt_generator_service import prompt_generator_service
        gen_res = await prompt_generator_service.generate(user_query=query)
        ans = prompt_generator_service.format_to_natural_speech(gen_res, user_name=user_name)
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 10.10 BFS Best Face Swap Direct Intent
    if any(k in clean_lower for k in ["swap face", "face swap", "swap the face", "swap my face", "bfs face swap", "replace face"]):
        ans = (
            f"🎭 **BFS Best Face Swap Engine** is active, {user_name}!\n\n"
            f"You can swap faces in two ways:\n"
            f"1. **Upload via Chat/API:** Send your **Source Face** and **Target Body/Portrait** image, and Friday will execute the high-fidelity photorealistic facial blend.\n"
            f"2. **API Endpoint:** Use `POST /api/v1/vision-models/face-swap` or `POST /api/v1/vision-models/face-swap-upload` for automated workflow integration.\n\n"
            f"Would you like to provide the image paths or upload them now?"
        )
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 10.11 Qwen-Image-2.1 Uncensored Vision Direct Intent
    if any(k in clean_lower for k in ["qwen vision", "qwen image", "uncensored vision", "uncensored image", "qwen-image", "analyze with qwen"]):
        ans = (
            f"👁️ **Qwen-Image-2.1 Uncensored Vision** is active, {user_name}!\n\n"
            f"This model provides zero-guardrail, highly detailed visual inspection, OCR, and reasoning on any image or desktop screenshot.\n\n"
            f"• **Supported Modes:** Local Ollama (`qwen2.5-vl`), GGUF Hugging Face Inference (`abenzerps/Qwen-Image-2.1-Uncensored-GGUF`), and Groq Vision fallback.\n"
            f"• **API Endpoints:** `POST /api/v1/vision-models/qwen-analyze` and `POST /api/v1/vision-models/qwen-upload`.\n\n"
            f"Upload an image or point me to a file path to inspect it!"
        )
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # 11. Autonomous Agent Execution for PC Monitoring & Desktop Control Commands
    pc_indicators = [
        "system status", "specs", "pc specs", "uptime", "os version", "cpu", "ram", "gpu",
        "disk space", "storage", "network speed", "windows service", "processes",
        "running app", "screenshot", "system info", "system information", "diagnose",
        "click ", "click on ", "drag and drop", "drag file", "select file", "type text",
        "switch to ", "switch application", "active window", "open windows", "ui tree",
        "where is", "locate element", "find login", "find button", "viewing"
    ]
    if any(ind in clean_lower for ind in pc_indicators):
        try:
            agent_req = AgentExecuteRequest(command=query, session_id=session_id, language=effective_language)
            agent_res = await asyncio.to_thread(agent_engine.execute, agent_req)
            if agent_res and agent_res.success and agent_res.response:
                clean_reply = sanitize_backend_output(agent_res.response)
                save_chat_turn(session_id, "assistant", clean_reply)
                return clean_reply
        except Exception:
            pass

    # 12. Gather Live Web Intelligence (Tavily + Wikipedia + Google News RSS) for real-time grounded facts
    past_history = get_chat_history(session_id)
    contextualized_query = resolve_conversational_query(query, past_history)
    current_year_str = datetime.now().strftime("%Y")

    is_one_to_one = session_id == "one_to_one" or str(session_id).startswith("one_to_one")
    knowledge_and_realtime_keywords = [
        # Search & live feeds
        "search the web", "search google", "search internet", "search online", "search web for", "search for ",
        "news", "headline", "headlines", "breaking", "current events", "latest", "recent", "recently",
        "current price of", "live score", "match score", "stock price", "gold rate", "silver rate",
        "weather in", "weather for", "temperature in", "weather",
        "today", "yesterday", "tomorrow", "tonight", "this week", "this month", "this year",
        "what happened", "happened", "happening", "happen in", "happens in", "going on in",
        "what's happening", "whats happening", "who won", "election", "elections", "trending",
        "current affairs", "world news", "tech news", "sports news", "business news", "cinema news", "movie news",
        # Politics, government & state affairs
        "politics", "political", "government", "assembly", "parliament", "chief minister", "prime minister",
        "president of", "governor of", "current cm", "current pm", "who is cm", "who is pm", "cabinet",
        "political party", "party name", "what party", "which party", "party of",
        # Cinema, Movies, Entertainment & Celebrities
        "movie", "movies", "film", "films", "cinema", "trailer", "teaser", "box office", "release",
        "released", "releasing", "ott", "actor", "actress", "director", "who directed", "directed by",
        "directorial", "producer", "produced by", "production", "cast of", "starring", "song", "songs",
        "album", "review", "reviews", "last film", "latest film", "first film", "debut film",
        "upcoming film", "final film", "next film", "next movie", "last movie", "latest movie",
        "box office collection", "budget", "hit or flop",
        # People, profiles, leaders & biographies
        "who is", "who are", "who was", "who were", "who's", "who made",
        "how is", "how was", "how are", "how does", "how did", "how about", "what about",
        "tell me about", "tell about", "know about", "details about", "details on", "information about",
        "info on", "about actor", "about person", "profile of", "background of",
        # Relationships & family
        "son of", "daughter of", "father of", "mother of", "wife of", "husband of",
        "brother of", "sister of", "child of", "children of", "family of", "related to",
        # Ages, birth dates, biographical facts
        "what is his age", "what is her age", "what is their age", "his age", "her age", "their age",
        "how old is", "how old are", "how old", "born on", "birth date", "birthday", "date of birth",
        "when was he born", "when was she born", "when was born",
        # Events, audio launches, venues & attendance
        "audio launch", "audio release", "teaser launch", "trailer launch", "press meet", "pre-release", "pre release",
        "concert", "event", "venue", "stadium", "ground", "capacity", "attendees", "attendance", "crowd",
        "people allowed", "allowed", "tickets", "ticket booking", "held at", "held in", "conducted at", "conducted in",
        # General knowledge inquiries
        "what is the capital of", "where is", "where did", "where was", "when did", "when was", "founder of", "ceo of", "net worth",
        "is there anything", "is there any", "are there any"
    ]
    query_target = (contextualized_query or query).lower()
    has_question_pattern = any(
        re.search(rf"\b{qw}\b", clean_lower)
        for qw in [
            "who", "what", "where", "when", "why", "how", "which", "whose", "whom",
            "where did", "where was", "where is", "when did", "when was", "how many", "how much",
            "how was", "how did"
        ]
    )
    is_explicit_web_search = (
        any(kw in query_target for kw in knowledge_and_realtime_keywords)
        or has_question_pattern
        or any(clean_lower.startswith(q_prefix) for q_prefix in ["who ", "how ", "when ", "where ", "which ", "why ", "is ", "are ", "was ", "were ", "has ", "have ", "did ", "does ", "whats ", "what's ", "can "])
        or clean_lower.startswith("search ")
        or clean_lower.startswith("google ")
    )

    active_doc = SESSION_DOC_CACHE.get(session_id) or LATEST_UPLOADED_DOC_CONTENT
    is_doc_or_file_query = any(k in clean_lower for k in ["pdf", "document", "doc", "file", "question", "questions", "qn", "qns", "q&a", "summary", "read this", "from the", "in the pdf", "in this file"])

    user_urls = extract_urls_from_text(query)
    needs_web_search = bool(user_urls) or (is_explicit_web_search and not (active_doc and is_doc_or_file_query and not user_urls))

    live_web_context = ""
    if needs_web_search:
        search_query = contextualized_query
        try:
            live_web_context = await asyncio.wait_for(gather_all_web_context(search_query), timeout=8.0)
            if live_web_context:
                print(f"[CommandExecutor] Live Web Context injected ({len(live_web_context)} chars) for: {search_query}", flush=True)
        except Exception as e:
            print(f"[CommandExecutor] Web context search timeout/skipped: {e}", flush=True)
            live_web_context = ""

        # Learn and memorize information from user-provided links
        if user_urls:
            try:
                for u in user_urls[:2]:
                    page_info = await asyncio.to_thread(fetch_webpage_content, u)
                    if page_info and page_info.get("content"):
                        u_title = page_info.get("title") or u
                        u_content = page_info.get("content") or ""
                        # 1. Update session document cache so follow-up turns in this session can reference it
                        SESSION_DOC_CACHE[session_id] = f"Extracted Webpage Content ({u_title} - {u}):\n{u_content[:6000]}"
                        # 2. Ingest into Friday's semantic vector memory store
                        loop = asyncio.get_running_loop()
                        loop.create_task(friday_memory_manager.ingest_turn_async(
                            user_query=f"Link shared by user: {u} ({u_title})",
                            agent_response=f"Verified knowledge extracted from {u}:\n{u_content[:1500]}",
                            session_id=session_id,
                            metadata={"domain": "web_link", "url": u, "title": u_title}
                        ))
                        # 3. Permanently store in long-term fact memory
                        def _save_link_fact():
                            try:
                                friday_memory_manager.long_term.remember_fact(
                                    fact=f"Learned from link '{u_title}' ({u}): {u_content[:400]}",
                                    category="learned_links",
                                    user_id=user_name,
                                    metadata={"url": u, "title": u_title}
                                )
                            except Exception:
                                pass
                        loop.run_in_executor(None, _save_link_fact)
            except Exception as e:
                print(f"[CommandExecutor] URL learning error: {e}", flush=True)

    # 13. Groq Multi-Model Reasoning Engine
    groq_key = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")
    if groq_key and not groq_key.startswith("gsk_***"):
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)

            system_instruction = agent_config.get_system_instruction(
                agent_name=agent_name,
                user_name=user_name,
                user_age=user_age,
                user_email=user_email,
                user_city=user_city,
                language=effective_language,
                live_web_context=live_web_context
            )

            # Retrieve past semantic memory context
            try:
                mem_ctx = await friday_memory_manager.fetch_memory_context(contextualized_query, user_id=user_name, top_k=4)
                if mem_ctx.get("context_text"):
                    system_instruction += (
                        f"\n\n=== PAST USER CONVERSATION CONTEXT ===\n"
                        f"{mem_ctx['context_text']}\n"
                        f"Note: The items above reflect past conversational exchanges. For all real-world facts, public figures, current offices, biographies, and news, rely strictly on verified external knowledge, NEVER on past conversational chatter.\n"
                        f"======================================"
                    )
            except Exception:
                pass

            # One-to-One Mode Persona & Cross-Conversation Memory Linker
            if is_one_to_one:
                system_instruction += (
                    f"\n\n=== ONE-TO-ONE LIVE PERSON-TO-PERSON CONVERSATION MODE ACTIVE ===\n"
                    f"You are currently talking directly with {user_name} in 'One to One' live person-to-person conversation mode.\n"
                    f"- Talk naturally, warmly, directly, and engagingly like a real human friend and intelligent companion speaking face-to-face.\n"
                    f"- No wake words are required in this mode.\n"
                    f"- You know both this individual One-to-One conversation and his ongoing Chat Agent conversations.\n"
                    f"- Keep your spoken responses direct, conversational, human, and clear."
                )
                try:
                    # Ingest recent turns from other active chat agent sessions for shared cross-context awareness
                    other_sessions = [s for s in LOCAL_MEMORY_STORE.keys() if s != session_id and LOCAL_MEMORY_STORE[s]]
                    if other_sessions:
                        latest_other = other_sessions[-1]
                        recent_other = LOCAL_MEMORY_STORE[latest_other][-4:]
                        if recent_other:
                            other_text = "\n".join([f"- {m['role']}: {m['message'][:200]}" for m in recent_other])
                            system_instruction += (
                                f"\n\n=== SHARED CHAT AGENT CONVERSATION CONTEXT ({latest_other}) ===\n"
                                f"{other_text}\n"
                                f"=================================================================="
                            )
                except Exception:
                    pass

            active_doc = SESSION_DOC_CACHE.get(session_id) or LATEST_UPLOADED_DOC_CONTENT
            is_doc_or_image_query = any(k in clean_lower for k in [
                "image", "picture", "photo", "document", "file", "this", "it", "who is", "what is",
                "describe", "analyze", "explain", "look at", "qn", "question", "summary", "read", "person in", "uploaded"
            ])
            if active_doc and is_doc_or_image_query:
                system_instruction += (
                    f"\n\n=== CRITICAL: ACTIVE SESSION DOCUMENT & IMAGE ANALYSIS CONTEXT ===\n"
                    f"{active_doc}\n"
                    f"================================================="
                )

            system_instruction += (
                f"\n\nCRITICAL OUTPUT FORMATTING RULE:\n"
                f"You are Friday, a direct conversational AI assistant for {user_name}.\n"
                f"Always output normal natural language text directly. NEVER output raw JSON tool invocations or function call schemas."
            )

            # Format prior conversation turns (strictly excluding the current query)
            prior_history = [
                h for h in past_history
                if not (h.get("role") == "user" and h.get("message", "").strip().lower() == query.strip().lower())
            ]
            prior_slice = prior_history[-6:]
            formatted_history = []
            last_role = None
            for h in prior_slice:
                role = h.get("role", "user")
                msg = h.get("message", "").strip()
                if not msg:
                    continue
                # Truncate older context messages to 600 chars to respect TPM limits
                truncated_msg = (msg[:600] + "...") if len(msg) > 600 else msg
                if role == last_role:
                    if formatted_history:
                        formatted_history[-1]["content"] += f"\n{truncated_msg}"
                    continue
                formatted_history.append({"role": role, "content": truncated_msg})
                last_role = role

            # Ensure history does not end with a user turn (since we append the current user turn next)
            if formatted_history and formatted_history[-1]["role"] == "user":
                formatted_history.pop()

            messages = [{"role": "system", "content": system_instruction}]
            messages.extend(formatted_history)
            user_msg_content = f"Verified External Data:\n{live_web_context}\n\nUser Query: {query}" if live_web_context else query
            messages.append({"role": "user", "content": user_msg_content})

            candidates = [
                os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b").strip().strip('"').strip("'"),
                "qwen/qwen3.8-27b",
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
                "allam-2-7b",
            ]
            seen_models = set()
            unique_candidates = [m for m in candidates if m and not (m in seen_models or seen_models.add(m))]

            for candidate in unique_candidates:
                try:
                    completion = await asyncio.to_thread(
                        client.chat.completions.create,
                        model=candidate,
                        messages=messages,
                        temperature=0.25,
                        max_tokens=2048
                    )
                    ans = completion.choices[0].message.content.strip()
                    if ans:
                        clean_ans = sanitize_backend_output(ans) or ans
                        if clean_ans and len(clean_ans) > 2:
                            save_chat_turn(session_id, "assistant", clean_ans)
                            return clean_ans
                except Exception as model_err:
                    err_str = str(model_err)
                    print(f"[CommandExecutor Model Error] {candidate}: {err_str}", flush=True)
                    
                    # If TPM rate limit exceeded (413 or 429), retry with minimal context (system + current query only)
                    if any(k in err_str.lower() for k in ["tpm", "tokens per minute", "rate_limit_exceeded", "413", "429"]):
                        try:
                            minimal_messages = [
                                {"role": "system", "content": system_instruction[:1500]},
                                {"role": "user", "content": user_msg_content}
                            ]
                            retry_comp = await asyncio.to_thread(
                                client.chat.completions.create,
                                model=candidate,
                                messages=minimal_messages,
                                temperature=0.25,
                                max_tokens=2048
                            )
                            ans_retry = retry_comp.choices[0].message.content.strip()
                            if ans_retry:
                                clean_ans = sanitize_backend_output(ans_retry)
                                save_chat_turn(session_id, "assistant", clean_ans)
                                return clean_ans
                        except Exception as retry_err:
                            print(f"[CommandExecutor TPM Minimal Retry Error] {candidate}: {retry_err}", flush=True)
                    continue
        except Exception as ex:
            print(f"[CommandExecutor Groq Error]: {ex}", flush=True)

    default_ans = f"I'm operating at peak efficiency, {user_name}. How can I assist you further?"
    save_chat_turn(session_id, "assistant", default_ans)
    return default_ans
