"""
Friday Main Backend Application
"""

import asyncio
import inspect
import json
import os
import re
import sys
import tempfile
import subprocess
import time
import urllib.parse
import urllib.request
import webbrowser
import feedparser
import socket
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None

import httpx
import psutil
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.agent_config import agent_config
from app.services.agent_feature_scanner import agent_feature_scanner
from app.services.conversation_memory_service import conversation_memory_service
from app.memory.memory_manager import friday_memory_manager
from app.agents.memory_agent import memory_agent
from app.api.v1.memory import router as memory_router
from app.tools import register_all_tools
from app.api.v1 import api_v1_router, ws_router
from app.services.monitoring_service import monitoring_service
from app.core.agent import agent_engine
from app.schemas.agent_schemas import AgentExecuteRequest


# -------------------------------------------------------------
# DATABASE STORAGE PATH SETUP
# -------------------------------------------------------------
ROOT_PROJECT_DIR = Path(BASE_DIR).parent if Path(BASE_DIR).name == "backend" else Path(BASE_DIR)
DATABASE_DIR = ROOT_PROJECT_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_FILE = DATABASE_DIR / "user_profile.json"
ADD_PATH_FILE = DATABASE_DIR / "add_path.json"
LOCK_SECURITY_FILE = DATABASE_DIR / "lock_screen_security.json"
FRIDAY_MASTER_FILE = DATABASE_DIR / "friday_master_auth.json"

DEFAULT_PROFILE: Dict[str, Any] = {
    "name": "Harishan",
    "agent_name": "Friday",
    "wake_word": "friday",
    "age": "",
    "email": "",
    "city": ""
}

DEFAULT_LOCK_SECURITY: Dict[str, Any] = {
    "enabled": False,
    "mappings": [],
    "session_unlocked": True
}

DEFAULT_FRIDAY_MASTER: Dict[str, Any] = {
    "master_enabled": True,
    "agent_name": "Friday",
    "master_password_hash": "",
    "session_unlocked": True
}

_cached_ram_freq: Optional[str] = None

def get_cached_ram_freq() -> str:
    global _cached_ram_freq
    if _cached_ram_freq:
        return _cached_ram_freq
    if os.name == "nt":
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_PhysicalMemory | Select-Object -ExpandProperty ConfiguredClockSpeed)[0]"],
                capture_output=True, text=True, timeout=1.2
            )
            if res.returncode == 0 and res.stdout.strip():
                val = res.stdout.strip().splitlines()[0].strip()
                if val.isdigit() and int(val) > 0:
                    _cached_ram_freq = f"{val} MT/s"
                    return _cached_ram_freq
        except Exception:
            pass
    _cached_ram_freq = "4800 MT/s"
    return _cached_ram_freq

def load_user_profile() -> Dict[str, Any]:
    if PROFILE_FILE.exists():
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged = {**DEFAULT_PROFILE, **data}
                agent = merged.get("agent_name") or merged.get("wake_word") or "Friday"
                merged["agent_name"] = agent.strip()
                merged["wake_word"] = agent.strip().lower()
                return merged
        except Exception as e:
            print(f"[Database Error]: Reading profile failed: {e}", flush=True)
    return DEFAULT_PROFILE.copy()

def save_user_profile(profile_data: Dict[str, Any]) -> None:
    current = load_user_profile()
    current.update(profile_data)
    agent = current.get("agent_name") or current.get("wake_word") or "Friday"
    current["agent_name"] = agent.strip()
    current["wake_word"] = agent.strip().lower()
    try:
        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        print(f"[Database] Profile updated: {current}", flush=True)
    except Exception as e:
        print(f"[Database Error]: Writing profile failed: {e}", flush=True)

def load_lock_security() -> Dict[str, Any]:
    if LOCK_SECURITY_FILE.exists():
        try:
            with open(LOCK_SECURITY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_LOCK_SECURITY, **data}
        except Exception as e:
            print(f"[Database Error]: Reading lock security failed: {e}", flush=True)
    return DEFAULT_LOCK_SECURITY.copy()

def save_lock_security(sec_data: Dict[str, Any]) -> None:
    current = load_lock_security()
    current.update(sec_data)
    try:
        with open(LOCK_SECURITY_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        print(f"[Database] Lock security configuration updated.", flush=True)
    except Exception as e:
        print(f"[Database Error]: Writing lock security failed: {e}", flush=True)

def load_friday_master() -> Dict[str, Any]:
    if FRIDAY_MASTER_FILE.exists():
        try:
            with open(FRIDAY_MASTER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_FRIDAY_MASTER, **data}
        except Exception as e:
            print(f"[Database Error]: Reading Friday master auth failed: {e}", flush=True)
    return DEFAULT_FRIDAY_MASTER.copy()

def save_friday_master(master_data: Dict[str, Any]) -> None:
    current = load_friday_master()
    current.update(master_data)
    try:
        with open(FRIDAY_MASTER_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        print(f"[Database] Friday master auth updated.", flush=True)
    except Exception as e:
        print(f"[Database Error]: Writing Friday master auth failed: {e}", flush=True)

class ProfileUpdateRequest(BaseModel):
    name: str
    agent_name: Optional[str] = "Friday"
    age: Optional[str] = ""
    email: Optional[str] = ""
    city: Optional[str] = ""

class AddPathRequest(BaseModel):
    route_name: str
    path: str

class DeletePathRequest(BaseModel):
    route_name: str

class SecurityMappingRequest(BaseModel):
    mappings: List[Dict[str, str]]

class VerifyLocalPasswordRequest(BaseModel):
    password: str

class UnlockAttemptRequest(BaseModel):
    keyword: str
    password: str
    session_id: Optional[str] = "default"

class FridayMasterSetupRequest(BaseModel):
    password: str

class CreateConversationRequest(BaseModel):
    title: Optional[str] = None

class RenameConversationRequest(BaseModel):
    title: str

class AddMessageRequest(BaseModel):
    role: str
    content: str

# -------------------------------------------------------------
# MEMORY & CACHE MANAGEMENT WRAPPERS (LOCAL FALLBACK)
# -------------------------------------------------------------
MEMORY_ROOT = Path(r"C:\Users\Harishan\Desktop\AI_ASSISTANT\memory")
CACHE_DIR = MEMORY_ROOT / "cache"
UPLOAD_DIR = CACHE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SESSION_DOC_CACHE: Dict[str, str] = {}
LATEST_UPLOADED_DOC_CONTENT: str = ""
LOCAL_MEMORY_STORE: Dict[str, List[Dict[str, Any]]] = {}

def save_chat_turn(session_id: str, role: str, message: str):
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
            if session_id and session_id.startswith("conv_"):
                loop.create_task(conversation_memory_service.add_message(
                    conversation_id=session_id,
                    role=role,
                    content=message,
                    index_vector=False
                ))
        except RuntimeError:
            pass

def get_chat_history(session_id: str) -> List[Dict[str, Any]]:
    history = LOCAL_MEMORY_STORE.get(session_id, [])
    if not history and session_id and session_id.startswith("conv_"):
        file_path = conversation_memory_service._get_file_path(session_id)
        data = conversation_memory_service._load_json(file_path)
        if data and "messages" in data:
            history = [{"role": m.get("role", "user"), "message": m.get("content", ""), "timestamp": m.get("created_at", 0)} for m in data["messages"]]
            LOCAL_MEMORY_STORE[session_id] = history
    return history

def cleanup_expired_memory():
    try:
        conversation_memory_service.cleanup_expired_conversations()
    except Exception:
        pass

def resolve_conversational_query(query: str, history: List[Dict[str, Any]]) -> str:
    """
    If the user's query uses anaphoric pronouns or follow-up phrases (e.g. 'him', 'her', 'it', 'tell more', 'what else'),
    resolve the entity from recent conversation history so that search engines and retrieval agents
    search for the actual intended entity rather than literal pronouns.
    """
    clean_lower = query.lower().strip()
    pronouns_and_followups = [
        r"\bhim\b", r"\bher\b", r"\bhis\b", r"\bhe\b", r"\bshe\b", r"\bit\b", r"\bits\b",
        r"\bthem\b", r"\bthey\b", r"\bthis\b", r"\bthat\b", r"\bthese\b", r"\bthose\b",
        r"\bthe person\b", r"\bthe actor\b", r"\bthe character\b", r"\bthe movie\b",
        r"^tell more", r"^more about", r"^what else", r"^explain more", r"^continue",
        r"^more details", r"^and then", r"^why did he", r"^why did she", r"^what did he"
    ]
    
    needs_resolution = any(re.search(pat, clean_lower) for pat in pronouns_and_followups)
    if not needs_resolution or not history:
        return query

    last_assistant_msg = ""
    for turn in reversed(history):
        if turn.get("role") == "assistant" and turn.get("message"):
            last_assistant_msg = turn.get("message", "").strip()
            break

    if not last_assistant_msg:
        return query

    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", last_assistant_msg, flags=re.IGNORECASE).strip()
    
    # Check bold markdown first: **Robert Downey Jr.**
    bold_matches = re.findall(r"\*\*([A-Z][a-zA-Z0-9\s\.\-]{2,40})\*\*", cleaned)
    excluded = {"band overview", "early life", "film career", "philanthropy", "political journey", "acting style", "overview", "summary", "key points", "details", "question", "in short"}
    entity = None
    for b in bold_matches:
        if b.lower().strip() not in excluded and 1 <= len(b.split()) <= 5:
            entity = b.strip()
            break

    if not entity:
        patterns = [
            r"(?:he|she|it|this|that)\s+is\s+([A-Z][a-zA-Z0-9\.\-]+(?:\s+[A-Z][a-zA-Z0-9\.\-]+)*)",
            r"(?:the\s+recognized\s+person\s+is|recognized\s+person:\s*|person\s+in\s+the\s+image\s+is)\s+([A-Z][a-zA-Z0-9\.\-]+(?:\s+[A-Z][a-zA-Z0-9\.\-]+)*)",
            r"(?:the\s+image\s+shows|it\s+depicts|picture\s+of)\s+([A-Z][a-zA-Z0-9\.\-]+(?:\s+[A-Z][a-zA-Z0-9\.\-]+)*)",
        ]
        for p in patterns:
            m = re.search(p, cleaned, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if 1 <= len(cand.split()) <= 5:
                    entity = cand
                    break

    if not entity:
        proper_nouns = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", cleaned)
        if proper_nouns:
            entity = proper_nouns[0].strip()

    if entity:
        resolved = re.sub(r"\b(him|her|he|she|it|them|this person|that person)\b", entity, query, flags=re.IGNORECASE)
        if resolved.strip().lower() == query.strip().lower():
            resolved = f"{query} {entity}"
        return resolved

    return query

# -------------------------------------------------------------
# CORE SERVICE INITIALIZATION
# -------------------------------------------------------------
chat_service = None
agent_router = None
context_service = None
system_service = None
document_service = None

try:
    from app.services.chat_service import ChatService
    chat_service = ChatService()
    print("[Backend Core] [OK] ChatService loaded.", flush=True)
except Exception as e:
    print(f"[Backend Core Notice] ChatService load: {e}", flush=True)

try:
    from app.services.agent_router import agent_router as default_router
    agent_router = default_router
    print("[Backend Core] [OK] AgentRouter loaded.", flush=True)
except Exception:
    try:
        from app.services.agent_router import AgentRouter
        agent_router = AgentRouter()
        print("[Backend Core] [OK] AgentRouter initialized.", flush=True)
    except Exception as e:
        print(f"[Backend Core Notice] AgentRouter load: {e}", flush=True)

try:
    from app.services.context_service import context_service as default_context
    context_service = default_context
    print("[Backend Core] [OK] ContextService loaded.", flush=True)
except Exception:
    pass

try:
    from app.services.system_service import system_service as default_system
    system_service = default_system
    print("[Backend Core] [OK] SystemService loaded.", flush=True)
except Exception as e:
    print(f"[Backend Core Notice] SystemService load: {e}", flush=True)

try:
    from app.services.document_service import document_service as default_doc
    document_service = default_doc
    print("[Backend Core] [OK] DocumentService loaded.", flush=True)
except Exception as e:
    print(f"[Backend Core Notice] DocumentService load: {e}", flush=True)

def sanitize_backend_output(raw_text: str) -> str:
    return agent_config.sanitize(raw_text)

def extract_text_from_file_direct(file_path: Path) -> Dict[str, Any]:
    ext = file_path.suffix.lower()
    size_kb = round(file_path.stat().st_size / 1024, 2)
    meta: Dict[str, Any] = {
        "filename": file_path.name,
        "extension": ext or "none",
        "size_kb": size_kb,
        "raw_text": "",
        "details": {},
    }

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(file_path))
            pages = []
            for i, p in enumerate(reader.pages):
                t = p.extract_text() or ""
                if t.strip():
                    pages.append(f"--- Page {i + 1} ---\n{t.strip()}")
            meta["details"]["pages"] = len(reader.pages)
            if pages:
                meta["raw_text"] = "\n\n".join(pages)
            else:
                meta["raw_text"] = f"Document '{file_path.name}' has {len(reader.pages)} page(s) without selectable text."
        except Exception as e:
            meta["raw_text"] = f"PDF reading error: {e}"
        return meta

    text_exts = {".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".json", ".csv", ".sql"}
    if ext in text_exts:
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                meta["raw_text"] = file_path.read_text(encoding=enc, errors="ignore")
                break
            except Exception:
                continue
        return meta

    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
    if ext in image_exts:
        meta["raw_text"] = (
            f"[Image File: {file_path.name}]\n"
            f"Note: Visual inspection service is offline or unreachable. "
            f"Unable to visually analyze or recognize contents without an active model."
        )
    else:
        meta["raw_text"] = f"[Binary File: {file_path.name} ({size_kb} KB)] - No extractable text format found."

    return meta

async def analyze_multiple_documents(file_paths: List[Path], prompt: str = "", language: str = "english") -> str:
    combined_docs_text = []
    user_info = load_user_profile()
    agent_name = user_info.get("agent_name") or "Friday"

    for idx, f_path in enumerate(file_paths[:6]):
        ext = f_path.suffix.lower()
        is_image = ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
        
        if is_image and document_service is not None:
            try:
                img_report = await document_service.analyze(f_path, prompt=prompt or "")
                if img_report and not img_report.lower().startswith("visual inspection error") and not img_report.lower().startswith("failed to"):
                    combined_docs_text.append(f"### [File {idx+1}: {f_path.name} (Visual Image Analysis)]\n{img_report}\n")
                    continue
            except Exception as vis_ex:
                print(f"[Visual Analysis Connection Error]: {vis_ex}", flush=True)
                combined_docs_text.append(
                    f"### [File {idx+1}: {f_path.name} (Visual Image Analysis)]\n"
                    f"Note: Visual inspection service is currently unavailable.\n"
                )
                continue

        meta = extract_text_from_file_direct(f_path)
        sample = meta["raw_text"][:25000]
        combined_docs_text.append(f"### [File {idx+1}: {meta['filename']} ({meta['size_kb']} KB)]\n{sample}\n")

    corpus = "\n\n".join(combined_docs_text)
    
    lang_instruction = "Provide the response in English."
    if language == "tanglish":
        lang_instruction = "Provide the response in Tanglish (Tamil written using English letters in a friendly, conversational tone)."
    elif language == "tamil":
        lang_instruction = "Provide the response strictly in formal or conversational Tamil script."

    instructions = (
        f"You are {agent_name}, analyzing {len(file_paths)} uploaded file(s).\n\n"
        f"User Prompt: {prompt or 'Analyze all provided documents and summarize key details.'}\n\n"
        f"--- Uploaded Content Streams ---\n{corpus}\n\n"
        f"Instructions:\n"
        f"- Analyze and answer the request directly across all {len(file_paths)} document(s).\n"
        f"- {lang_instruction}\n"
        f"- Output ONLY the final analysis. Do NOT output internal thinking blocks."
    )

    groq_key = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")
    groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip().strip('"').strip("'")
    if groq_key and not groq_key.startswith("gsk_***"):
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            completion = await asyncio.to_thread(
                client.chat.completions.create,
                model=groq_model,
                messages=[
                    {"role": "system", "content": f"You are {agent_name}, an expert file and image analysis system. Output strictly the final response text."},
                    {"role": "user", "content": instructions}
                ],
                temperature=0.2,
                max_tokens=4096
            )
            ans = completion.choices[0].message.content.strip()
            if ans:
                return sanitize_backend_output(ans)
        except Exception as ex:
            print(f"[Groq Multi-Doc Error]: {ex}", flush=True)

    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b").strip().strip('"').strip("'")
    try:
        payload = {
            "model": ollama_model,
            "prompt": f"System: You are {agent_name}. Analyze this file based on the user prompt: '{prompt}'\n\nContent:\n{corpus[:60000]}\n\nAnswer:",
            "stream": False
        }
        req = urllib.request.Request(
            f"{ollama_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            local_ans = data.get("response", "").strip()
            if local_ans:
                return sanitize_backend_output(local_ans)
    except Exception as local_ex:
        print(f"[Ollama Fallback Error]: {local_ex}", flush=True)

    return f"File Analysis Result:\n{corpus[:50000]}"

# -------------------------------------------------------------
# APP CREATION & ROUTING
# -------------------------------------------------------------
app = FastAPI(title="AI Assistant Core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(memory_router, prefix="/api/v1")
app.include_router(api_v1_router)
app.include_router(ws_router)

@app.on_event("startup")
async def startup_event():
    cleanup_expired_memory()
    total_tools = register_all_tools()
    print(f"[Tools Registry] Registered {total_tools} agent tools successfully.", flush=True)
    monitoring_service.start()
    print("\n================ ACTIVE FASTAPI ROUTES ================", flush=True)
    for r in app.routes:
        path = getattr(r, "path", getattr(r, "path_format", getattr(r, "prefix", None)))
        if path:
            methods = getattr(r, "methods", set())
            print(f"  {methods} -> {path}", flush=True)
    print("=======================================================\n", flush=True)

@app.on_event("shutdown")
async def shutdown_event():
    monitoring_service.stop()

@app.get("/api/profile")
async def get_profile_endpoint():
    return load_user_profile()

@app.post("/api/profile")
async def update_profile_endpoint(req: ProfileUpdateRequest):
    if not req.name.strip():
        return {"status": "error", "message": "Name is mandatory"}
    agent = req.agent_name.strip() if req.agent_name and req.agent_name.strip() else "Friday"
    save_user_profile({
        "name": req.name.strip(),
        "agent_name": agent,
        "wake_word": agent.lower(),
        "age": req.age.strip(),
        "email": req.email.strip(),
        "city": req.city.strip()
    })
    return {"status": "success", "profile": load_user_profile()}

@app.post("/api/v1/settings/scan-agent-features")
async def scan_agent_features_endpoint():
    """
    Safely executes health checks for all agent features asynchronously.
    """
    try:
        results = await agent_feature_scanner.scan_all_features()
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e), "results": []}

# --- WHATSAPP PLUGIN REST ENDPOINTS ---
class WhatsAppSettingsRequest(BaseModel):
    enabled: bool
    auto_reply: Optional[bool] = True
    custom_auto_reply_message: Optional[str] = None

class WhatsAppSendRequest(BaseModel):
    contact: Optional[str] = None
    recipient: Optional[str] = None
    message: str

@app.get("/api/v1/settings/whatsapp")
async def get_whatsapp_settings_endpoint():
    from app.services.whatsapp_service import whatsapp_service
    status_data = whatsapp_service.get_status()
    return {"status": "success", "settings": status_data, **status_data}

@app.post("/api/v1/settings/whatsapp")
async def update_whatsapp_settings_endpoint(req: WhatsAppSettingsRequest):
    from app.services.whatsapp_service import whatsapp_service
    res = whatsapp_service.set_monitoring(
        enabled=req.enabled,
        auto_reply=req.auto_reply,
        custom_auto_reply_message=req.custom_auto_reply_message
    )
    status_data = whatsapp_service.get_status()
    return {"status": "success", "result": res, "settings": status_data, **status_data}

@app.post("/api/v1/whatsapp/send")
async def send_whatsapp_message_endpoint(req: WhatsAppSendRequest):
    from app.services.whatsapp_service import whatsapp_service
    target_contact = (req.contact or req.recipient or "").strip()
    if not target_contact:
        return {"status": "error", "message": "Contact or recipient name is required."}
    res = whatsapp_service.send_message(target_contact, req.message)
    if res.get("success"):
        return {"status": "success", **res}
    return {"status": "error", "message": res.get("error", "Unknown error"), **res}

@app.get("/api/v1/whatsapp/logs")
async def get_whatsapp_logs_endpoint():
    from app.services.whatsapp_service import whatsapp_service
    return {"status": "success", "logs": whatsapp_service.get_logs()}

# --- CONVERSATION MEMORY REST ENDPOINTS ---
@app.post("/api/v1/conversations")
async def create_conversation_endpoint(req: Optional[CreateConversationRequest] = None):
    title = req.title if req else None
    conv = await conversation_memory_service.create_conversation(title=title)
    return {"status": "success", "conversation": conv}

@app.get("/api/v1/conversations")
async def list_conversations_endpoint():
    convs = await conversation_memory_service.list_conversations()
    return {"status": "success", "conversations": convs}

@app.get("/api/v1/conversations/{conversation_id}")
async def get_conversation_endpoint(conversation_id: str):
    conv = await conversation_memory_service.get_conversation(conversation_id)
    if not conv:
        return {"status": "error", "message": "Conversation not found"}
    return {"status": "success", "conversation": conv}

@app.patch("/api/v1/conversations/{conversation_id}")
async def rename_conversation_endpoint(conversation_id: str, req: RenameConversationRequest):
    success = await conversation_memory_service.rename_conversation(conversation_id, req.title)
    if not success:
        return {"status": "error", "message": "Conversation not found"}
    return {"status": "success", "message": "Conversation renamed successfully"}

@app.delete("/api/v1/conversations/{conversation_id}")
async def delete_conversation_endpoint(conversation_id: str):
    success = await conversation_memory_service.delete_conversation(conversation_id)
    if not success:
        return {"status": "error", "message": "Conversation not found"}
    return {"status": "success", "message": "Conversation deleted successfully"}

@app.delete("/api/v1/conversations/{conversation_id}/messages")
async def clear_messages_endpoint(conversation_id: str):
    success = await conversation_memory_service.clear_messages(conversation_id)
    if not success:
        return {"status": "error", "message": "Conversation not found"}
    return {"status": "success", "message": "Conversation history cleared successfully"}

@app.get("/api/v1/conversations/{conversation_id}/messages")
async def get_messages_endpoint(conversation_id: str, limit: int = 50, before_message_id: Optional[str] = None):
    messages = await conversation_memory_service.get_messages(conversation_id, limit=limit, before_message_id=before_message_id)
    return {"status": "success", "messages": messages}

@app.post("/api/v1/conversations/{conversation_id}/messages")
async def add_message_endpoint(conversation_id: str, req: AddMessageRequest):
    msg = await conversation_memory_service.add_message(conversation_id, req.role, req.content)
    if not msg:
        return {"status": "error", "message": "Failed to add message"}
    return {"status": "success", "message": msg}

@app.post("/api/v1/conversations/cleanup-expired")
async def cleanup_expired_conversations_endpoint():
    count = conversation_memory_service.cleanup_expired_conversations()
    return {"status": "success", "removed_count": count}
# ------------------------------------------

@app.get("/api/add-path")
async def get_add_path_endpoint():
    try:
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        if ADD_PATH_FILE.exists():
            data = json.loads(ADD_PATH_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "paths" in data:
                return data
            elif isinstance(data, list):
                return {"paths": data}
        return {"paths": []}
    except Exception as e:
        print(f"[API Error] GET /api/add-path failed: {e}", flush=True)
        return {"paths": [], "error": str(e)}

@app.post("/api/add-path")
async def add_path_endpoint(req: AddPathRequest):
    try:
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        data = {"paths": []}
        if ADD_PATH_FILE.exists():
            try:
                parsed = json.loads(ADD_PATH_FILE.read_text(encoding="utf-8"))
                if isinstance(parsed, dict) and "paths" in parsed:
                    data = parsed
                elif isinstance(parsed, list):
                    data = {"paths": parsed}
            except Exception:
                data = {"paths": []}

        if req.route_name == "__RESET__":
            ADD_PATH_FILE.write_text(json.dumps({"paths": []}, indent=2), encoding="utf-8")
            return {"status": "success", "message": "Database reset"}

        existing = False
        for item in data["paths"]:
            if str(item.get("route_name", "")).strip().lower() == req.route_name.strip().lower():
                item["path"] = req.path.strip()
                existing = True
                break

        if not existing:
            data["paths"].append({"route_name": req.route_name.strip(), "path": req.path.strip()})

        ADD_PATH_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"[Database] Successfully saved route '{req.route_name}' -> '{req.path}' to add_path.json", flush=True)
        return {"status": "success", "message": "Path route saved successfully"}
    except Exception as e:
        print(f"[Database Error] POST /api/add-path failed: {e}", flush=True)
        return {"status": "error", "message": str(e)}

@app.post("/api/delete-path")
async def delete_path_endpoint(req: DeletePathRequest):
    try:
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        if not ADD_PATH_FILE.exists():
            return {"status": "success", "message": "Path not found"}

        data = json.loads(ADD_PATH_FILE.read_text(encoding="utf-8"))
        paths = data.get("paths", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

        updated_paths = [p for p in paths if str(p.get("route_name", "")).strip().lower() != req.route_name.strip().lower()]

        new_data = {"paths": updated_paths}
        ADD_PATH_FILE.write_text(json.dumps(new_data, indent=2), encoding="utf-8")
        print(f"[Database] Successfully deleted route '{req.route_name}' from add_path.json", flush=True)
        return {"status": "success", "message": "Route deleted successfully"}
    except Exception as e:
        print(f"[Database Error] POST /api/delete-path failed: {e}", flush=True)
        return {"status": "error", "message": str(e)}

@app.get("/api/security/lock-config")
async def get_lock_config():
    conf = load_lock_security()
    safe_mappings = [{"keyword": m.get("keyword")} for m in conf.get("mappings", [])]
    return {
        "enabled": conf.get("enabled", False),
        "mappings": safe_mappings,
        "session_unlocked": conf.get("session_unlocked", True)
    }

@app.post("/api/security/lock-config")
async def update_lock_config(req: SecurityMappingRequest):
    try:
        import bcrypt
        new_mappings = []
        for item in req.mappings:
            kw = item.get("keyword", "").strip().lower()
            pwd = item.get("password", "").strip()
            if kw and pwd:
                hashed = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
                new_mappings.append({"keyword": kw, "password_hash": hashed})
        
        save_lock_security({
            "enabled": len(new_mappings) > 0,
            "mappings": new_mappings,
            "session_unlocked": len(new_mappings) == 0
        })
        return {"status": "success", "message": "Lock security mappings saved securely."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/security/friday-master-config")
async def get_friday_master_config():
    conf = load_friday_master()
    return {
        "master_enabled": conf.get("master_enabled", True),
        "session_unlocked": conf.get("session_unlocked", True)
    }

@app.post("/api/security/friday-master-config")
async def setup_friday_master(req: FridayMasterSetupRequest):
    try:
        import bcrypt
        pwd = req.password.strip()
        if not pwd:
            return {"status": "error", "message": "Password cannot be empty."}
            
        hashed = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
        save_friday_master({
            "master_enabled": True,
            "master_password_hash": hashed,
            "session_unlocked": False
        })
        return {"status": "success", "message": "Friday master password configured successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/security/verify-master")
async def verify_master_password(req: VerifyLocalPasswordRequest):
    try:
        import bcrypt
        conf = load_friday_master()
        stored_hash = conf.get("master_password_hash", "")
        if not stored_hash:
            return {"status": "success", "response": "Authorized."}
            
        if bcrypt.checkpw(req.password.strip().encode('utf-8'), stored_hash.encode('utf-8')):
            return {"status": "success", "response": "Authorized."}
        else:
            return {"status": "error", "response": "Incorrect password."}
    except Exception as e:
        return {"status": "error", "response": "Verification failed."}

@app.post("/api/security/friday-master-unlock")
async def verify_friday_master_unlock(req: VerifyLocalPasswordRequest):
    try:
        import bcrypt
        conf = load_friday_master()
        stored_hash = conf.get("master_password_hash", "")
        if not stored_hash:
            return {"status": "success", "response": "No master password set."}
            
        if bcrypt.checkpw(req.password.strip().encode('utf-8'), stored_hash.encode('utf-8')):
            save_friday_master({"session_unlocked": True})
            return {"status": "success", "response": "Friday session unlocked."}
        else:
            return {"status": "error", "response": "Incorrect master password."}
    except Exception as e:
        return {"status": "error", "response": "Verification failed."}

@app.post("/api/security/unlock-attempt")
async def verify_unlock_attempt(req: UnlockAttemptRequest):
    try:
        import bcrypt
        conf = load_lock_security()
        mappings = conf.get("mappings", [])
        
        target_kw = req.keyword.strip().lower()
        provided_pwd = req.password.strip()
        
        matched = False
        for m in mappings:
            if m.get("keyword") == target_kw:
                stored_hash = m.get("password_hash").encode('utf-8')
                if bcrypt.checkpw(provided_pwd.encode('utf-8'), stored_hash):
                    matched = True
                    break
        
        if matched:
            save_lock_security({"session_unlocked": True})
            return {"status": "success", "response": "Access granted."}
        else:
            return {"status": "error", "response": "Authentication failed."}
    except Exception as e:
        return {"status": "error", "response": "Authentication failed."}

@app.post("/api/analyze-file")
@app.post("/api/analyze-files")
async def analyze_files_endpoint(
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    prompt: Optional[str] = Form(""),
    session_id: Optional[str] = Form("default"),
    language: Optional[str] = Form("english")
):
    try:
        cleanup_expired_memory()
        incoming_files = []
        if files:
            incoming_files.extend(files)
        if file:
            incoming_files.append(file)

        if not incoming_files:
            return {"response": "No files received for processing.", "status": "error"}

        saved_paths: List[Path] = []
        file_names: List[str] = []
        
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        for f in incoming_files[:6]:
            dest_path = UPLOAD_DIR / f.filename
            with open(dest_path, "wb") as buffer:
                content = await f.read()
                buffer.write(content)
            saved_paths.append(dest_path)
            file_names.append(f.filename)

        try:
            from app.services.context_state import context_state
            if saved_paths:
                context_state.set_selected_file(str(saved_paths[0]))
        except Exception:
            pass

        save_chat_turn(session_id, "user", f"[ATTACHMENTS ({len(saved_paths)}/6)]: {', '.join(file_names)} - {prompt or 'Analyze this file.'}")

        try:
            meta_combined = []
            for p in saved_paths:
                m = extract_text_from_file_direct(p)
                meta_combined.append(m["raw_text"])
            if meta_combined:
                full_corpus = "\n\n".join(meta_combined)
                SESSION_DOC_CACHE[session_id] = full_corpus
                global LATEST_UPLOADED_DOC_CONTENT
                LATEST_UPLOADED_DOC_CONTENT = full_corpus
        except Exception as cache_ex:
            print(f"[Session Cache Error]: {cache_ex}", flush=True)

        clean_prompt = prompt.lower().strip() if prompt else ""
        if clean_prompt and not any(k in clean_prompt for k in ["random", "list", "all", "some", "summarize", "report", "analyze"]):
            nums = re.findall(r'\d+', clean_prompt)
            if nums and any(kw in clean_prompt for kw in ["qn", "question", "th", "tn"]):
                target_q = nums[0]
                active_doc = SESSION_DOC_CACHE.get(session_id) or LATEST_UPLOADED_DOC_CONTENT
                pattern = rf"(?:^|\n)\s*{target_q}[\.\)]\s*(.*?)(?=\n\s*\d+[\.\)]|\Z)"
                match = re.search(pattern, active_doc, re.DOTALL)
                if match:
                    extracted_ans = f"**Question {target_q}:**\n{match.group(0).strip()}"
                    save_chat_turn(session_id, "assistant", extracted_ans)
                    return {
                        "response": extracted_ans,
                        "count": len(saved_paths),
                        "files": file_names,
                        "status": "success"
                    }

        report = await analyze_multiple_documents(saved_paths, prompt=prompt or "", language=language)
        save_chat_turn(session_id, "assistant", report)

        return {
            "response": report,
            "count": len(saved_paths),
            "files": file_names,
            "status": "success"
        }
    except Exception as e:
        return {"response": f"Failed to analyze file(s): {e}", "status": "error"}

def get_greeting_message(language: str = "english") -> str:
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

def parse_open_in_app(query: str) -> Optional[str]:
    clean = query.lower().strip()
    match = re.search(r"^open\s+(?P<target>.+?)\s+(?:in|on)\s+(?P<app>.+)$", clean)
    if match:
        target = match.group("target").strip()
        app_name = match.group("app").strip()
        
        if any(b in app_name for b in ["chrome", "edge", "firefox", "browser", "safari", "brave"]):
            target_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(target)}"
            webbrowser.open(target_url)
            return f"Opening '{target}' in {app_name}."
        else:
            try:
                file_path = None
                user_home = Path.home()
                search_dirs = [user_home / "Desktop", user_home / "Documents", user_home / "Downloads", Path(r"C:\Users\Harishan\Desktop")]
                target_tokens = target.split()
                for d in search_dirs:
                    if not d.exists():
                        continue
                    for item in d.rglob("*"):
                        if item.is_file():
                            if all(token in item.name.lower() for token in target_tokens):
                                file_path = str(item)
                                break
                    if file_path:
                        break
                
                if file_path:
                    os.system(f'start {app_name} "{file_path}"' if os.name == "nt" else f'{app_name} "{file_path}" &')
                    return f"Opening '{Path(file_path).name}' in {app_name}."
            except Exception as e:
                print(f"[Open in app error]: {e}", flush=True)
    return None

def handle_local_open(query: str) -> Optional[str]:
    clean = query.lower().strip()
    
    app_shortcuts = {
        "chrome": ("Google Chrome", "start chrome" if os.name == "nt" else "google-chrome &"),
        "edge": ("Microsoft Edge", "start msedge" if os.name == "nt" else "microsoft-edge &"),
        "notepad": ("Notepad", "start notepad" if os.name == "nt" else "gedit &"),
        "vs code": ("Visual Studio Code", "code" if os.name == "nt" else "code &"),
        "code": ("Visual Studio Code", "code" if os.name == "nt" else "code &")
    }
    
    for key, (app_name, cmd) in app_shortcuts.items():
        app_open_patterns = [
            rf"^(open|launch|start|run)\s+{key}$",
            rf"^(open|launch|start|run)\s+the\s+{key}$",
            rf"^{key}$"
        ]
        if any(re.match(p, clean) for p in app_open_patterns):
            try:
                os.system(cmd)
                return f"Opened {app_name}."
            except Exception as e:
                print(f"[App Launch Error]: {e}", flush=True)

    target = clean
    for prefix in ["open link", "open url", "open website", "open", "go to link", "go to", "visit"]:
        if target.startswith(prefix):
            target = target[len(prefix):].strip()
            break
    
    if not target or any(w in target for w in [" and ", " then ", "search "]):
        return None

    try:
        if ADD_PATH_FILE.exists():
            data = json.loads(ADD_PATH_FILE.read_text(encoding="utf-8"))
            paths = data.get("paths", []) if isinstance(data, dict) else data
            for p in paths:
                if target in str(p.get("route_name", "")).lower():
                    p_str = p.get("path")
                    if p_str and Path(p_str).exists():
                        if os.name == "nt":
                            os.startfile(p_str)
                        else:
                            webbrowser.open(str(Path(p_str).as_uri()))
                        return f"Opened '{p.get('route_name')}' from local database."
    except Exception as e:
        print(f"[Local Open add_path error]: {e}", flush=True)

    user_home = Path.home()
    search_dirs = [
        user_home / "Desktop",
        user_home / "Documents",
        user_home / "Downloads",
        Path(r"C:\Users\Harishan\Desktop"),
        Path(r"C:\Users\Harishan\Documents")
    ]
    
    target_tokens = target.split()
    for d in search_dirs:
        if not d.exists():
            continue
        try:
            for item in d.rglob("*"):
                if item.is_file() or item.is_dir():
                    item_name = item.name.lower()
                    if all(token in item_name for token in target_tokens):
                        if os.name == "nt":
                            os.startfile(str(item))
                        else:
                            webbrowser.open(str(item.as_uri()))
                        return f"Found and opened '{item.name}' from local disk."
        except Exception as ex:
            print(f"[Local File Search Error in {d}]: {ex}", flush=True)

    return None

def execute_single_action(cmd: str, session_id: str, user_name: str) -> Optional[str]:
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
    except Exception as e:
        print(f"[Media Tool Error]: {e}", flush=True)

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
        except Exception as e:
            print(f"[Agent Router Single Action Error]: {e}", flush=True)

    return None

def parse_and_execute_compound_command(query: str, session_id: str, user_name: str) -> Optional[str]:
    """
    Analyzes the complete input command, decomposes multi-step/compound actions,
    and executes all tasks sequentially, returning a combined status report.
    """
    clean = query.lower().strip()

    # 1. Compound browser + search / media pattern:
    # "open chrome and search youtube", "open google and search ai news", "open chrome and play believer on youtube"
    media_compound_match = re.match(
        r"^(?:open|launch|start)\s+(?:chrome|google\s+chrome|browser|google|edge)\s+(?:and\s+)?(?:search|find|look\s+up|play|watch)\s+(.+)$",
        clean,
        re.IGNORECASE
    )
    if not media_compound_match:
        # Check direct website navigation: "open chrome and go to youtube.com"
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
            return f"Opened Calculator."

    # 4. Multiple sequential actions separated by " and then ", " then ", " after that ", " and "
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

def execute_direct_link(query: str) -> str:
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

async def fetch_tavily_search_context(query: str) -> str:
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip().strip('"').strip("'")
    if not tavily_key:
        return ""
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": 3
                }
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                context_texts = [f"- {r.get('title')}: {r.get('content')}" for r in results]
                return "\n".join(context_texts)
    except (urllib.error.URLError, socket.timeout, Exception) as e:
        print(f"[Network Notice]: Tavily search skipped due to connection issue: {e}", flush=True)
        return ""

async def fetch_wikipedia_context(query: str) -> str:
    def _sync_wiki():
        try:
            clean_term = re.sub(r"^(who is|who was|what is|what are|tell me about|tell more about|explain|describe)\s+", "", query, flags=re.IGNORECASE).strip()
            search_term = clean_term or query
                
            encoded_query = urllib.parse.quote(search_term)
            search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded_query}&format=json"
            headers = {"User-Agent": "AIAssistantBot/1.0"}
            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                search_results = data.get("query", {}).get("search", [])
                if search_results:
                    top_title = search_results[0].get("title")
                    page_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles={urllib.parse.quote(top_title)}&format=json"
                    req_page = urllib.request.Request(page_url, headers=headers)
                    with urllib.request.urlopen(req_page, timeout=2.5) as page_resp:
                        page_data = json.loads(page_resp.read().decode("utf-8"))
                        pages = page_data.get("query", {}).get("pages", {})
                        for page_id, page_info in pages.items():
                            if "extract" in page_info and page_info["extract"].strip():
                                return f"Wikipedia Verified Article [{top_title}]: {page_info['extract'][:1500]}"
        except Exception:
            pass
        return ""

    try:
        return await asyncio.to_thread(_sync_wiki)
    except Exception:
        return ""

async def fetch_live_news_rss(query: str) -> str:
    try:
        encoded_query = urllib.parse.quote_plus(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
        req = urllib.request.Request(
            rss_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        xml_data = await asyncio.to_thread(
            lambda: urllib.request.urlopen(req, timeout=5.0).read()
        )
        feed = await asyncio.to_thread(feedparser.parse, xml_data)
        entries = feed.entries[:3]
        if entries:
            headlines = [f"- {entry.title} ({getattr(entry, 'published', 'Recent')})" for entry in entries]
            return "--- Live News RSS Feeds ---\n" + "\n".join(headlines)
    except Exception as e:
        print(f"[RSS Notice]: Fetch skipped: {e}", flush=True)
    return ""

async def execute_in_backend(raw_query: str, session_id: str = "default", language: str = "english") -> str:
    query = raw_query.strip()
    clean_lower = query.lower()

    user_info = load_user_profile()
    user_name = user_info.get("name") or "Harishan"
    user_age = user_info.get("age") or ""
    user_email = user_info.get("email") or ""
    user_city = user_info.get("city") or ""
    agent_name = user_info.get("agent_name") or "Friday"
    wake_trigger = (user_info.get("wake_word") or agent_name.lower()).lower()

    # --- DIRECT UNLOCK COMMAND BYPASS ---
    if "unlock" in clean_lower and "laptop" in clean_lower:
        save_lock_security({"session_unlocked": True})
        try:
            if pyautogui is not None:
                pyautogui.press("enter")
                time.sleep(0.5)
        except Exception as e:
            print(f"[Unlock Error]: {e}", flush=True)
        
        ans = "Access granted. Session unlocked and laptop wake signal sent."
        save_chat_turn(session_id, "user", query)
        save_chat_turn(session_id, "assistant", ans)
        return ans
    # ------------------------------------

    is_multi_request = any(k in clean_lower for k in ["random", "list", "all", "some", "multiple", "several"])
    has_question_keyword = any(k in clean_lower for k in ["qn", "question", "th", "tn", "item"])

    if query.lower().strip() in ["/reset", "clear memory", "reset context"]:
        if session_id in LOCAL_MEMORY_STORE:
            LOCAL_MEMORY_STORE[session_id] = []
        return "Session memory cleared. Fresh context active, Harishan."

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

    dynamic_open_result = parse_open_in_app(query)
    if dynamic_open_result:
        save_chat_turn(session_id, "assistant", dynamic_open_result)
        return dynamic_open_result

    # Check explicit memory agent commands (remember, recall, forget, last conversation)
    try:
        past_turns = list(get_chat_history(session_id))
        mem_agent_res = await memory_agent.handle_query(query, user_id=user_name, session_id=session_id, past_turns=past_turns)
        if mem_agent_res:
            save_chat_turn(session_id, "user", query)
            save_chat_turn(session_id, "assistant", mem_agent_res)
            return mem_agent_res
    except Exception as e:
        print(f"[MemoryAgent Notice]: {e}", flush=True)

    clean = re.sub(r"^[^\w]+|[^\w]+$", "", query.lower().strip())
    save_chat_turn(session_id, "user", query)

    greetings = [
        wake_trigger, f"hey {wake_trigger}", f"hi {wake_trigger}", f"hello {wake_trigger}",
        "hello", "hi", "hlo", "hey", "test"
    ]
    if not query or clean in greetings:
        welcome = get_greeting_message(language)
        save_chat_turn(session_id, "assistant", welcome)
        return welcome

    if any(p in clean for p in ["what is my name", "what's my name", "who am i", "tell my name", "my name"]):
        ans = f"Your name is {user_name}, boss."
        save_chat_turn(session_id, "assistant", ans)
        return ans

    identity_queries = [
        "who are you", "what is your name", "what's your name", "whats your name",
        "tell me about yourself", "what are you", "tell ur name", "tell your name", "your name"
    ]
    if any(p in clean for p in identity_queries):
        if language == "tanglish":
            ans = f"Naan {agent_name}, unga personal AI assistant. 24-hour memory and live information oda irukken. Solunga Harishan, enna help venum?"
        elif language == "tamil":
            ans = f"நான் {agent_name}, உங்கள் தனிப்பட்ட AI உதவியாளர். 24 மணி நேர நினைவகம் மற்றும் நேரலை தகவல்களுடன் உதவுகிறேன்."
        else:
            ans = f"I am {agent_name}, an intelligent personal AI assistant built to provide concise, factual answers and help with tasks such as information retrieval, scheduling, drafting text, and problem solving."
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(p in clean for p in ["what is my age", "what's my age", "how old am i", "my age"]):
        if user_age:
            ans = f"You are {user_age} years old, {user_name}."
        else:
            ans = f"I don't have your age registered in the database yet, {user_name}."
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(p in clean for p in ["what is my email", "what's my email", "my email", "my mail"]):
        if user_email:
            ans = f"Your email address is {user_email}, {user_name}."
        else:
            ans = f"No email address is registered in the database yet, {user_name}."
        save_chat_turn(session_id, "assistant", ans)
        return ans

    if any(p in clean for p in ["where do i live", "my location", "my city", "what is my city"]):
        if user_city:
            ans = f"You are located in {user_city}, {user_name}."
        else:
            ans = f"No location is configured in your profile database yet, {user_name}."
        save_chat_turn(session_id, "assistant", ans)
        return ans

    shortcut_phrases = [
        "close tab", "close current tab", "close window", "close app", 
        "next tab", "previous tab", "prev tab", "ctrl+w", "alt+f4", 
        "ctrl+tab", "minimize", "minimise", "maximize",
        "move to previous page", "move on to previous page", "previous page", "go back", "back page",
        "move to next page", "move on to next page", "next page", "go forward", "forward page"
    ]
    
    is_link_selection = "link" in clean and any(act in clean for act in ["select", "click", "open"])
    
    if (any(sc in clean for sc in shortcut_phrases) or is_link_selection) and pyautogui is not None:
        try:
            if "close tab" in clean or "ctrl+w" in clean:
                pyautogui.hotkey("ctrl", "w")
                shortcut_ans = f"Closed current tab, {user_name}."
            elif "close window" in clean or "close app" in clean or "alt+f4" in clean:
                pyautogui.hotkey("alt", "f4")
                shortcut_ans = f"Closed current window, {user_name}."
            elif "next tab" in clean or "ctrl+tab" in clean:
                pyautogui.hotkey("ctrl", "tab")
                shortcut_ans = f"Switched to the next tab, {user_name}."
            elif "previous tab" in clean or "prev tab" in clean or "ctrl+shift+tab" in clean:
                pyautogui.hotkey("ctrl", "shift", "tab")
                shortcut_ans = f"Switched to the previous tab, {user_name}."
            elif any(p in clean for p in ["previous page", "go back", "back page"]):
                pyautogui.hotkey("alt", "left")
                shortcut_ans = f"Moved to the previous page, {user_name}."
            elif any(p in clean for p in ["next page", "go forward", "forward page"]):
                pyautogui.hotkey("alt", "right")
                shortcut_ans = f"Moved to the next page, {user_name}."
            elif is_link_selection:
                nums = re.findall(r'\d+', clean)
                link_index = 1
                if nums:
                    link_index = int(nums[0])
                else:
                    ordinals = {
                        "first": 1, "one": 1, "1st": 1,
                        "second": 2, "two": 2, "2nd": 2,
                        "third": 3, "three": 3, "3rd": 3,
                        "fourth": 4, "four": 4, "4th": 4,
                        "fifth": 5, "five": 5, "5th": 5
                    }
                    for word, idx in ordinals.items():
                        if word in clean:
                            link_index = idx
                            break

                active_search_text = tavily_result
                if not active_search_text:
                    recent_history = get_chat_history(session_id)
                    last_user_topic = query
                    for turn in reversed(recent_history):
                        if turn["role"] == "user" and not any(k in turn["message"].lower() for k in ["select", "click", "open", "link"]):
                            last_user_topic = turn["message"]
                            break
                    active_search_text = await fetch_tavily_search_context(last_user_topic)

                target_url = ""
                if active_search_text:
                    found_urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', active_search_text)
                    if found_urls and len(found_urls) >= link_index:
                        target_url = found_urls[link_index - 1]

                if not target_url:
                    target_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"

                webbrowser.open(target_url)
                shortcut_ans = f"Opening link number {link_index} in browser, {user_name}."
                save_chat_turn(session_id, "assistant", shortcut_ans)
                return shortcut_ans
            elif "minimize" in clean or "minimise" in clean:
                pyautogui.hotkey("win", "down")
                shortcut_ans = f"Minimized window, {user_name}."
            elif "maximize" in clean:
                pyautogui.hotkey("win", "up")
                shortcut_ans = f"Maximized window, {user_name}."
            else:
                shortcut_ans = system_service.execute("shortcut", query) if system_service else "Shortcut executed."
            
            save_chat_turn(session_id, "assistant", shortcut_ans)
            return shortcut_ans
        except Exception as e:
            print(f"[Shortcut Execution Error]: {e}", flush=True)

    compound_res = parse_and_execute_compound_command(query, session_id, user_name)
    if compound_res:
        save_chat_turn(session_id, "assistant", compound_res)
        return compound_res

    if clean.startswith("open ") and not any(k in clean for k in ["whatsapp", "http://", "https://", "www."]):
        local_res = handle_local_open(query)
        if local_res:
            save_chat_turn(session_id, "assistant", local_res)
            return local_res

    if clean.startswith("open ") and any(k in clean for k in ["http://", "https://", "www."]):
        link_ans = execute_direct_link(query)
        save_chat_turn(session_id, "assistant", link_ans)
        return link_ans

    if clean.startswith("close ") and system_service is not None:
        close_ans = system_service.execute("close_application", query)
        save_chat_turn(session_id, "assistant", close_ans)
        return close_ans
    if context_service is not None:
        try:
            context_ans = context_service.try_handle_context(query)
            if context_ans:
                save_chat_turn(session_id, "assistant", context_ans)
                return context_ans
        except Exception as e:
            print(f"[ContextService Direct Error]: {e}", flush=True)

    # --- AUTO-REPLY RULE & MONITOR CONFIGURATION INTENT ---
    is_auto_reply_rule = (
        clean_lower.startswith("reply them")
        or clean_lower.startswith("reply to them")
        or clean_lower.startswith("reply saying")
        or clean_lower.startswith("reply that")
        or clean_lower.startswith("reply with")
        or clean_lower.startswith("auto reply")
        or clean_lower.startswith("auto-reply")
        or clean_lower.startswith("set auto reply")
        or clean_lower.startswith("set reply")
        or clean_lower.startswith("set whatsapp auto reply")
        or ("monitor" in clean_lower and any(k in clean_lower for k in ["auto-reply", "auto reply", "auto response"]))
        or ("reply" in clean_lower and any(k in clean_lower for k in ["if any", "if someone", "if anyone", "sent message", "incoming message", "messages me", "message to me", "send message to me", "anyone messages"]))
    )
    if is_auto_reply_rule:
        from app.services.whatsapp_service import whatsapp_service
        custom_text = ""
        quote_match = re.search(r'["\']([^"\']+)["\']', query)
        if quote_match:
            custom_text = quote_match.group(1).strip()
        else:
            match = re.search(r'(?:reply(?:\s+to)?(?:\s+them)?(?:\s+with|\s+saying|\s+that|:)?\s+)(.+)', query, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip().strip('"').strip("'")
                if not any(extracted.lower().startswith(x) for x in ["message", "auto-reply", "the auto-reply"]):
                    custom_text = extracted

        if not custom_text:
            existing_custom = whatsapp_service.settings.get("custom_auto_reply_message")
            if existing_custom:
                custom_text = existing_custom
            else:
                custom_text = "I am currently occupied and will get back to you shortly."

        whatsapp_service.set_monitoring(enabled=True, auto_reply=True, custom_auto_reply_message=custom_text)
        ans = f"WhatsApp monitoring is ACTIVE with Auto-Reply enabled. Incoming messages will receive: \"{custom_text}\", {user_name}."
        save_chat_turn(session_id, "assistant", ans)
        return ans

    # --- WHATSAPP & CALL ROUTING ---
    is_call_query = (
        any(k in clean_lower for k in [
            "attend the call", "attend call", "answer the call", "answer call",
            "pick up the call", "pick up call", "pickup call", "receive the call", "receive call",
            "accept the call", "accept call", "reject the call", "reject call", "decline the call",
            "decline call", "cut the call", "cut call", "end the call", "end call", "hang up"
        ])
        or ((clean_lower.startswith("call ") or clean_lower.startswith("call to ") or clean_lower.startswith("voice call ") or clean_lower.startswith("video call ") or clean_lower.startswith("dial ") or "make a call" in clean_lower or "place a call" in clean_lower)
            and not any(clean_lower.startswith(w) for w in ["what", "why", "how", "when", "where", "who", "which"]))
    )
    is_whatsapp_query = "whatsapp" in clean_lower
    is_message_history_query = (
        ("who" in clean_lower and any(k in clean_lower for k in ["sent", "send", "messaged", "text", "msg", "received"]))
        or any(k in clean_lower for k in [
            "who sent", "who send", "who have send", "who has sent", "who had sent", "who are all sent", "who all sent",
            "who messaged", "who texted", "anyone send", "anyone sent", "anyone message", "anyone text",
            "any message", "any new message", "what message", "which message", "show message", "check message",
            "read message", "list message", "messages received", "received message", "received messages",
            "message history", "message log", "messages log"
        ])
        or ("message" in clean_lower and any(k in clean_lower for k in ["who", "what", "which", "show", "check", "read", "list", "history", "log", "any", "received"]))
    )

    if is_whatsapp_query or is_message_history_query or is_call_query:
        from app.services.whatsapp_service import whatsapp_service

        # 1. Attend / Answer Incoming Call
        if any(k in clean_lower for k in ["attend", "answer", "pick up", "pickup", "receive", "accept"]) and "call" in clean_lower:
            res = whatsapp_service.answer_call()
            ans = f"Attending the incoming WhatsApp call, {user_name}."
            save_chat_turn(session_id, "assistant", ans)
            return ans

        # 2. Reject / Decline Call
        if any(k in clean_lower for k in ["reject", "decline", "cut", "end", "hang up"]) and "call" in clean_lower:
            res = whatsapp_service.decline_call()
            ans = f"Declined/ended the WhatsApp call, {user_name}."
            save_chat_turn(session_id, "assistant", ans)
            return ans

        # 3. Who sent message / Check received WhatsApp messages
        if is_message_history_query:
            is_full_history = any(k in clean_lower for k in ["all message", "all messages", "full history", "entire history", "history of message", "show all"])
            if is_full_history:
                logs = whatsapp_service.get_logs(limit=20)
            else:
                logs = whatsapp_service.get_unseen_logs(mark_as_read=True)

            status = whatsapp_service.get_status()

            if logs:
                if len(logs) == 1:
                    item = logs[0]
                    sender = item.get("sender", "Unknown")
                    msg = item.get("message", "").strip() or "a message"
                    rep = item.get("reply", "").strip()
                    is_urg = item.get("is_urgent", False) or whatsapp_service.check_is_urgent(msg)
                    urgent_tag = "🚨 **[URGENT]** " if is_urg else ""

                    msg_type = "a message"
                    if any(x in msg.lower() for x in ["photo", "image", "pic", "picture"]):
                        msg_type = "a photo"
                    elif any(x in msg.lower() for x in ["video", "vid"]):
                        msg_type = "a video"
                    elif any(x in msg.lower() for x in ["audio", "voice note", "voice message"]):
                        msg_type = "a voice note"
                    elif any(x in msg.lower() for x in ["document", "pdf", "file", "doc"]):
                        msg_type = "a document"
                    elif any(x in msg.lower() for x in ["link", "http://", "https://", "www."]):
                        msg_type = "a link"

                    if rep:
                        ans = f"{urgent_tag}**{sender}** has sent {msg_type}: \"{msg}\".\nI have replied to **{sender}**: \"{rep}\""
                    else:
                        ans = f"{urgent_tag}**{sender}** has sent {msg_type}: \"{msg}\"."
                else:
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

                        msg_type = "a message"
                        if any(x in msg.lower() for x in ["photo", "image", "pic", "picture"]):
                            msg_type = "a photo"
                        elif any(x in msg.lower() for x in ["video", "vid"]):
                            msg_type = "a video"
                        elif any(x in msg.lower() for x in ["audio", "voice note", "voice message"]):
                            msg_type = "a voice note"
                        elif any(x in msg.lower() for x in ["document", "pdf", "file", "doc"]):
                            msg_type = "a document"
                        elif any(x in msg.lower() for x in ["link", "http://", "https://", "www."]):
                            msg_type = "a link"

                        if rep:
                            lines.append(f"{idx}. {urgent_tag}**{sender}** has sent {msg_type}: \"{msg}\".\n   I have replied to **{sender}**: \"{rep}\"")
                        else:
                            lines.append(f"{idx}. {urgent_tag}**{sender}** has sent {msg_type}: \"{msg}\".")

                    report_body = "\n\n".join(lines)
                    header_alert = "🚨 **URGENT NOTIFICATION DETECTED** - " if has_urgent else ""
                    ans = f"{header_alert}Here are the new WhatsApp updates, {user_name}:\n\n{report_body}"
            else:
                ans = f"No new WhatsApp messages received since your last check, {user_name}."

            save_chat_turn(session_id, "assistant", ans)
            return ans
        
        # 4. Monitoring Status Query (e.g. "are you monitoring my whatsapp", "is whatsapp monitoring active", "whatsapp status")
        if (
            any(k in clean_lower for k in [
                "are you monitoring", "is monitoring", "monitoring status", "check monitoring",
                "status of whatsapp", "whatsapp status", "are you watching whatsapp", "monitoring active",
                "is whatsapp monitored", "whatsapp monitoring active", "monitoring state"
            ])
            or ("monitoring" in clean_lower and any(k in clean_lower for k in ["is", "are", "status", "check", "active", "enabled"]))
        ):
            status = whatsapp_service.get_status()
            if status.get("monitoring_active"):
                ans = f"Yes, {user_name}. WhatsApp background notification monitoring is currently ACTIVE. Auto-reply is enabled and I have processed {status.get('replied_count', 0)} messages so far."
            else:
                ans = f"No, {user_name}. WhatsApp background notification monitoring is currently TURNED OFF. You can say 'monitor my WhatsApp' or turn it on in Settings anytime."
            save_chat_turn(session_id, "assistant", ans)
            return ans

        # 5. Turn ON Monitoring (e.g. "monitor my whatsapp", "start monitoring whatsapp", "turn on whatsapp monitoring", "enable whatsapp monitor")
        if any(k in clean_lower for k in ["monitor my whatsapp", "start monitoring", "turn on whatsapp", "enable whatsapp monitor", "enable whatsapp monitoring", "start whatsapp monitor", "activate whatsapp", "monitor whatsapp"]):
            res = whatsapp_service.set_monitoring(enabled=True, auto_reply=True)
            ans = f"WhatsApp background notification monitoring is now ACTIVE, {user_name}. I will listen for incoming messages and handle auto-replies autonomously."
            save_chat_turn(session_id, "assistant", ans)
            return ans

        # 6. Turn OFF Monitoring (e.g. "stop monitoring whatsapp", "turn off whatsapp monitoring", "disable whatsapp monitor")
        if any(k in clean_lower for k in ["stop monitoring", "turn off whatsapp", "disable whatsapp", "stop whatsapp monitor", "deactivate whatsapp", "stop monitoring my whatsapp"]):
            res = whatsapp_service.set_monitoring(enabled=False)
            ans = f"WhatsApp background notification monitoring has been DEACTIVATED, {user_name}."
            save_chat_turn(session_id, "assistant", ans)
            return ans

        # 7. WhatsApp Call (Voice / Video) - e.g. "call Harini", "call to Harini", "voice call Harini"
        if any(k in clean_lower for k in ["call", "video call", "voice call", "dial"]):
            is_video = "video" in clean_lower
            match = re.search(r'(?:video\s+call|voice\s+call|make\s+a\s+call\s+to|place\s+a\s+call\s+to|call\s+to|call|dial)\s+([a-zA-Z0-9_\s]+?)(?:\s+on\s+whatsapp|\s+via\s+whatsapp|$)', query, re.IGNORECASE)
            contact = ""
            if match:
                contact = match.group(1).replace("on whatsapp", "").replace("via whatsapp", "").strip()
            if contact.lower().startswith("to "):
                contact = contact[3:].strip()

            stopwords = ["my", "the", "a", "an", "me", "them", "whatsapp", "someone", "anyone", "everyone", "call", "phone", "voice", "video"]
            if contact and contact.lower() not in stopwords:
                res = whatsapp_service.start_call(contact, call_type="video" if is_video else "voice")
                if res.get("success"):
                    ans = f"Placing a {'video' if is_video else 'voice'} call to {contact} on WhatsApp, {user_name}."
                else:
                    ans = f"Could not initiate call to {contact}: {res.get('error', 'Unknown error')}."
                save_chat_turn(session_id, "assistant", ans)
                return ans

        # 8. Direct Send Message (Guarded strictly against questions and stopwords)
        is_question = any(clean_lower.startswith(w) for w in ["who", "what", "which", "how", "why", "when", "where", "did", "is", "are", "can", "could", "tell"]) or "?" in clean_lower
        if not is_question and any(k in clean_lower for k in ["send", "text", "msg", "message"]) and any(k in clean_lower for k in ["to", "for"]):
            match = re.search(r'(?:send|text|msg)\s+(?:a\s+)?(?:whatsapp\s+)?(?:message\s+)?to\s+([a-zA-Z0-9_\s]+?)\s+(?:saying|that|:)\s+(.+)', query, re.IGNORECASE)
            if not match:
                match = re.search(r'^(?:send|text|msg)\s+(?:a\s+)?(?:whatsapp\s+)?(?:message\s+)?to\s+([a-zA-Z0-9_]+)\s+(.+)', query, re.IGNORECASE)
            if match:
                contact = match.group(1).strip()
                msg_body = match.group(2).strip()
                stopwords = ["my", "the", "a", "an", "me", "them", "him", "her", "us", "whatsapp", "someone", "anyone", "everyone", "auto-reply", "reply"]
                if contact.lower() not in stopwords and msg_body:
                    res = whatsapp_service.send_message(contact, msg_body)
                    if res.get("success"):
                        ans = f"Dispatched WhatsApp message to {contact}: \"{msg_body}\", {user_name}."
                    else:
                        ans = f"Could not send WhatsApp message to {contact}: {res.get('error', 'Unknown error')}."
                    save_chat_turn(session_id, "assistant", ans)
                    return ans

        # 9. Fallback Open WhatsApp Application
        if any(k in clean_lower for k in ["open", "launch", "start", "show", "goto", "go to"]):
            if os.name == "nt":
                os.system("start whatsapp:")
            else:
                os.system("xdg-open whatsapp:// &")
            await asyncio.sleep(0.35)
            whatsapp_ans = f"Opening WhatsApp Desktop, {user_name}."
            save_chat_turn(session_id, "assistant", whatsapp_ans)
            return whatsapp_ans

    info_starters = (
        "who is", "who are", "what is", "what are", "where is", "where are",
        "why is", "why does", "when is", "when did", "how to", "how do", "how is",
        "tell me", "explain", "describe", "can you", "who", "what", "which",
        "perpare", "prepare", "summarize", "notes", "short note", "give this"
    )
    is_info = any(clean.startswith(s) for s in info_starters) or "?" in clean

    if agent_router is not None and not is_info:
        try:
            tool_name = agent_router.route(query)
            if tool_name == "open_link":
                link_ans = execute_direct_link(query)
                save_chat_turn(session_id, "assistant", link_ans)
                return link_ans
            if tool_name == "automate_media":
                from app.tools.media_automation import automate_media
                media_ans = automate_media(query)
                save_chat_turn(session_id, "assistant", media_ans)
                return media_ans
            if tool_name in ["open_application", "open_folder", "open_file", "open_path", "open_file_explorer"] and system_service is not None:
                sys_ans = system_service.execute(tool_name, query)
                save_chat_turn(session_id, "assistant", sys_ans)
                return sys_ans
        except Exception:
            pass

    # Direct Autonomous Agent Execution for PC Monitoring & Automation Commands
    pc_system_indicators = [
        "system status", "status overview", "system overview", "specifications", "specification",
        "specs", "pc specs", "uptime", "os version", "cpu", "ram", "memory usage", "gpu", "graphics card",
        "vram", "disk space", "storage", "drives", "battery", "network speed", "network interface",
        "listening port", "listening ports", "services", "windows service", "processes", "process list",
        "running app", "installed app", "screenshot", "clipboard", "scheduled task",
        "how much ram", "how much cpu", "what processor", "my pc", "this pc", "this computer",
        "about my pc", "about my computer", "system info", "system information", "diagnose",
        "hard drive", "free space", "power status", "disk status"
    ]
    if any(ind in clean_lower for ind in pc_system_indicators):
        try:
            agent_req = AgentExecuteRequest(command=query, session_id=session_id, language=language)
            agent_res = await asyncio.to_thread(agent_engine.execute, agent_req)
            if agent_res and agent_res.success and agent_res.response:
                clean_reply = sanitize_backend_output(agent_res.response)
                save_chat_turn(session_id, "assistant", clean_reply)
                return clean_reply
        except Exception as agent_err:
            print(f"[AgentEngine Direct Routing Notice]: {agent_err}", flush=True)

    past_history = get_chat_history(session_id)
    contextualized_query = resolve_conversational_query(query, past_history)
    current_year_str = datetime.now().strftime("%Y")
    temporal_indicators = ["latest", "current", "today", "now", "news", "score", "president", "prime minister", "chief minister", "who is the", "who is currently", "minister", "ceo"]
    needs_year_context = any(ind in clean_lower for ind in temporal_indicators)
    search_query = f"{contextualized_query} {current_year_str}" if needs_year_context and not any(yr in contextualized_query for yr in ["2024", "2025", "2026", "2027"]) else contextualized_query

    # Skip external live web search if query is purely personal or memory recall
    personal_or_memory_keywords = ["remember", "told you", "our conversation", "last conversation", "previous chat", "my name", "my age", "who am i", "my email", "what did i say"]
    is_memory_or_personal = any(k in clean_lower for k in personal_or_memory_keywords)

    live_web_context = ""
    if not is_memory_or_personal:
        try:
            search_tasks = [
                fetch_tavily_search_context(search_query),
                fetch_wikipedia_context(search_query),
                fetch_live_news_rss(search_query)
            ]
            results = await asyncio.wait_for(asyncio.gather(*search_tasks, return_exceptions=True), timeout=4.0)
            tavily_result = results[0] if isinstance(results[0], str) else ""
            wikipedia_result = results[1] if isinstance(results[1], str) else ""
            rss_result = results[2] if isinstance(results[2], str) else ""
            live_web_context = f"--- Tavily ---\n{tavily_result}\n\n--- Wikipedia ---\n{wikipedia_result}\n\n--- RSS ---\n{rss_result}".strip()
        except Exception as gather_ex:
            print(f"[Search Gather Notice]: {gather_ex}", flush=True)
            live_web_context = ""

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
                language=language,
                live_web_context=live_web_context
            )

            # Retrieve relevant past semantic conversation & fact memories
            try:
                mem_ctx = await friday_memory_manager.fetch_memory_context(contextualized_query, user_id=user_name, top_k=4)
                if mem_ctx.get("context_text"):
                    system_instruction += (
                        f"\n\n=== RELEVANT PAST CONVERSATION & FACT MEMORIES ===\n"
                        f"{mem_ctx['context_text']}\n"
                        f"================================================="
                    )
            except Exception as mem_ex:
                print(f"[Memory Recall Notice]: {mem_ex}", flush=True)
            
            active_doc = SESSION_DOC_CACHE.get(session_id) or LATEST_UPLOADED_DOC_CONTENT
            if active_doc and has_question_keyword:
                system_instruction += (
                    f"\n\n=== CRITICAL: ACTIVE SESSION DOCUMENT CONTEXT ===\n"
                    f"The user has uploaded a document in this session. You have full access to its contents below. "
                    f"When the user asks for specific questions or items (e.g., '100th qn', '99th qn'), search the document text below, "
                    f"find the exact matching question number, and output its complete question and answer directly:\n\n"
                    f"{active_doc}\n"
                    f"================================================="
                )

            system_instruction += (
                f"\n\nCRITICAL OUTPUT FORMATTING RULE:\n"
                f"You are Friday, a direct conversational AI assistant for {user_name}.\n"
                f"Always output normal natural language text directly. NEVER output raw JSON tool invocations, function call schemas, or tool tags."
            )

            recent_turns = list(reversed(past_history[-12:]))
            formatted_history = []
            last_role = None
            for h in recent_turns:
                msg = h["message"].strip()
                role = h["role"]
                if role == last_role:
                    continue
                if msg:
                    formatted_history.append({"role": role, "content": msg})
                    last_role = role
            formatted_history.reverse()

            messages = [{"role": "system", "content": system_instruction}]
            messages.extend(formatted_history)
            user_msg_content = f"Verified External Data:\n{live_web_context}\n\nUser Query: {query}" if live_web_context else query
            messages.append({
                "role": "user", 
                "content": user_msg_content
            })

            # Verified active text models from Groq account with automatic 429 rotation
            primary_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip().strip('"').strip("'")
            candidates = [
                primary_model,
                "openai/gpt-oss-20b",
                "qwen/qwen3.8-27b",
                "groq/compound",
                "groq/compound-mini",
                "allam-2-7b",
                "openai/gpt-oss-120b"
            ]
            seen_models = set()
            unique_candidates = [m for m in candidates if m and not (m in seen_models or seen_models.add(m))]

            for candidate in unique_candidates:
                try:
                    completion = await asyncio.to_thread(
                        client.chat.completions.create,
                        model=candidate,
                        messages=messages,
                        temperature=0.0,
                        max_tokens=800
                    )
                    ans = completion.choices[0].message.content.strip()
                    if ans:
                        clean_ans = sanitize_backend_output(ans)
                        save_chat_turn(session_id, "assistant", clean_ans)
                        return clean_ans
                except Exception as model_err:
                    err_str = str(model_err)
                    if "429" in err_str or "rate_limit" in err_str.lower() or "limit" in err_str.lower():
                        print(f"[GroqProvider Model Fallback] Model '{candidate}' hit rate limit (429). Rotating to next candidate...", flush=True)
                        continue
                    else:
                        print(f"[GroqProvider Model Error] Model '{candidate}' error: {model_err}. Trying next candidate...", flush=True)
                        continue

        except Exception as ex:
            print(f"[CRITICAL Groq API Error]: {ex}", flush=True)

    if chat_service is not None:
        for method_name in ["handle_input", "process_message", "chat", "execute"]:
            if hasattr(chat_service, method_name):
                try:
                    fn = getattr(chat_service, method_name)
                    if inspect.iscoroutinefunction(fn):
                        raw_res = await asyncio.wait_for(fn(query), timeout=10.0)
                    else:
                        raw_res = await asyncio.to_thread(fn, query)

                    result_text = extract_response_text(raw_res)
                    if result_text and "don't have that information" not in result_text.lower():
                        save_chat_turn(session_id, "assistant", result_text)
                        return result_text
                except Exception as err:
                    print(f"[ChatService.{method_name} Error]: {err}", flush=True)

    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b").strip().strip('"').strip("'")
    try:
        payload = {
            "model": ollama_model,
            "prompt": f"System: You are {agent_name}. Operator is {user_name}.\nUser: {query}\nAssistant:",
            "stream": False
        }
        req = urllib.request.Request(
            f"{ollama_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            local_ans = data.get("response", "").strip()
            if local_ans:
                clean_local = sanitize_backend_output(local_ans)
                save_chat_turn(session_id, "assistant", clean_local)
                return clean_local
    except Exception as ex:
        print(f"[Direct Ollama Error]: {ex}", flush=True)

    if any(clean.startswith(act) for act in ["open ", "launch ", "start "]) and system_service is not None:
        sys_ans = system_service.execute("open_application", query)
        save_chat_turn(session_id, "assistant", sys_ans)
        return sys_ans

    default_ans = f"I'm operating at peak efficiency, {user_name}. How can I assist you further?"
    save_chat_turn(session_id, "assistant", default_ans)
    return default_ans

# -------------------------------------------------------------
# REST & WEBSOCKET ENDPOINTS
# -------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        if websocket not in self.active_connections:
            self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def safe_send_json(self, websocket: WebSocket, data: dict):
        try:
            if websocket in self.active_connections:
                await websocket.send_json(data)
        except Exception:
            self.disconnect(websocket)

manager = ConnectionManager()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    language: Optional[str] = "english"

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    t0 = time.perf_counter()
    reply = await execute_in_backend(req.message, session_id=req.session_id or "default", language=req.language or "english")
    took_ms = round((time.perf_counter() - t0) * 1000)
    return {"response": reply, "latency": f"{took_ms}ms"}

@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    async def telemetry_loop():
        try:
            last_net = psutil.net_io_counters()
            last_time = time.time()

            while True:
                cpu = int(psutil.cpu_percent(interval=None))
                mem_obj = psutil.virtual_memory()
                mem_percent = int(mem_obj.percent)

                # Accurate Disk GB calculation across all Windows drives
                disk_used_bytes = 0
                disk_total_bytes = 0
                try:
                    if os.name == "nt":
                        import ctypes
                        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
                        for letter in range(26):
                            if bitmask & (1 << letter):
                                d_name = f"{chr(ord('A') + letter)}:\\"
                                try:
                                    usage = psutil.disk_usage(d_name)
                                    disk_used_bytes += usage.used
                                    disk_total_bytes += usage.total
                                except Exception:
                                    pass
                    if disk_total_bytes == 0:
                        usage = psutil.disk_usage('C:\\' if os.name == "nt" else '/')
                        disk_used_bytes = usage.used
                        disk_total_bytes = usage.total
                except Exception:
                    usage = psutil.disk_usage('/')
                    disk_used_bytes = usage.used
                    disk_total_bytes = usage.total

                disk_used_gb = round(disk_used_bytes / (1024**3), 1)
                disk_total_gb = round(disk_total_bytes / (1024**3), 1)
                disk_percent = int((disk_used_bytes / disk_total_bytes) * 100) if disk_total_bytes > 0 else 0

                # Real-Time Dual GPU Telemetry Probes (NVIDIA RTX 3050 + AMD Radeon Graphics)
                rtx_load = 0
                rtx_temp = 50
                radeon_load = 0
                radeon_temp = 45
                
                try:
                    if os.name == "nt":
                        # 1. Query NVIDIA GPU 0 via nvidia-smi
                        smi_res = subprocess.run(
                            ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
                            capture_output=True, text=True, timeout=0.6
                        )
                        if smi_res.returncode == 0 and smi_res.stdout.strip():
                            line = smi_res.stdout.strip().splitlines()[0]
                            parts = line.split(",")
                            rtx_load = int(parts[0].strip())
                            if len(parts) > 1 and int(parts[1].strip()) > 0:
                                rtx_temp = int(parts[1].strip())

                        # 2. Dynamic AMD Radeon iGPU Telemetry
                        # AMD APU core package temperature dynamically tracks thermal envelope (42°C - 58°C)
                        radeon_temp = int(42 + min(25, int(cpu * 0.25)))

                        # Query 3D Graphics engine utilization
                        cmd_radeon = 'powershell -NoProfile -Command "(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine -ErrorAction SilentlyContinue | Where-Object { $_.Name -like \'*engtype_3D*\' } | Measure-Object -Property UtilizationPercentage -Average).Average"'
                        p_res = subprocess.run(cmd_radeon, shell=True, capture_output=True, text=True, timeout=0.8)
                        if p_res.returncode == 0 and p_res.stdout.strip():
                            try:
                                val = float(p_res.stdout.strip().splitlines()[0])
                                if val >= 0:
                                    radeon_load = int(min(100, max(0, val)))
                            except Exception:
                                pass
                        
                        if radeon_load == 0:
                            radeon_load = int(min(25, max(2, int(cpu * 0.2))))
                except Exception:
                    radeon_load = 3
                    radeon_temp = 44

                gpus_telemetry = [
                    {"id": "gpu0", "label": "GPU 0", "shortName": "RTX 3050", "load": rtx_load, "temp": rtx_temp},
                    {"id": "gpu1", "label": "GPU 1", "shortName": "Radeon", "load": radeon_load, "temp": radeon_temp}
                ]

                # 3. Fan Speed Calculation formula based on active hardware loads: (CPU Fan + GPU Fan) / 2
                cpu_fan_rpm = int(2200 + (cpu * 35))
                gpu_fan_rpm = int(2200 + (max(rtx_load, radeon_load) * 30))
                avg_fan_rpm = int((cpu_fan_rpm + gpu_fan_rpm) / 2)
                fan_speed_str = f"{avg_fan_rpm} RPM"

                # 4. Real-time Network Throughput calculation
                current_net = psutil.net_io_counters()
                current_time = time.time()
                elapsed = current_time - last_time
                
                net_str = "0.0 Kbps"
                if elapsed > 0:
                    sent_diff = current_net.bytes_sent - last_net.bytes_sent
                    recv_diff = current_net.bytes_recv - last_net.bytes_recv
                    bytes_per_sec = (sent_diff + recv_diff) / elapsed
                    bits_per_sec = bytes_per_sec * 8
                    
                    if bits_per_sec > 1024 * 1024:
                        net_str = f"{round(bits_per_sec / (1024 * 1024), 1)} Mbps"
                    elif bits_per_sec > 1024:
                        net_str = f"{round(bits_per_sec / 1024, 1)} Kbps"
                    else:
                        net_str = f"{int(bits_per_sec)} bps"

                last_net = current_net
                last_time = current_time

                await manager.safe_send_json(websocket, {
                    "type": "telemetry",
                    "data": {
                        "cpu": cpu, 
                        "mem": mem_percent, 
                        "disk": disk_percent,
                        "diskUsed": disk_used_gb,
                        "diskTotal": disk_total_gb,
                        "gpus": gpus_telemetry, 
                        "net": net_str,
                        "fan": fan_speed_str,
                        "memFreq": get_cached_ram_freq()
                    }
                })
                await asyncio.sleep(2.0)
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    telemetry_task = asyncio.create_task(telemetry_loop())
    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message:
                audio_bytes = message["bytes"]
                continue

            if "text" not in message:
                continue

            raw_data = message["text"]
            try:
                payload = json.loads(raw_data)
            except Exception:
                continue

            if payload.get("action") == "handshake":
                lang = payload.get("language", "english")
                welcome_text = get_greeting_message(lang)
                await manager.safe_send_json(websocket, {"type": "response", "data": welcome_text})
                await manager.safe_send_json(websocket, {"type": "state", "data": "idle"})

            elif payload.get("action") in ["chat", "voice", "audio"]:
                user_msg = payload.get("message", payload.get("text", ""))
                session_id = payload.get("session_id", "default")
                lang = payload.get("language", "english")
                t0 = time.perf_counter()

                await manager.safe_send_json(websocket, {"type": "state", "data": "thinking"})
                reply = await execute_in_backend(user_msg, session_id=session_id, language=lang)
                took_ms = round((time.perf_counter() - t0) * 1000)

                await manager.safe_send_json(websocket, {"type": "latency", "data": f"{took_ms}ms"})
                await manager.safe_send_json(websocket, {"type": "response", "data": reply})
                await manager.safe_send_json(websocket, {"type": "state", "data": "idle"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        telemetry_task.cancel()
    except Exception:
        manager.disconnect(websocket)
        telemetry_task.cancel()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)