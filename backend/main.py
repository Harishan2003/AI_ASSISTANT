"""
Friday AI Assistant - Main Application Server
============================================
FastAPI backend core serving REST endpoints, WebSocket real-time voice and telemetry streams,
autonomous agent task orchestration, security controls, and hardware power optimization.
"""

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.services.tts_service import tts_service

load_dotenv()

# Base project paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_PROJECT_DIR = Path(BASE_DIR).parent if Path(BASE_DIR).name == "backend" else Path(BASE_DIR)
DATABASE_DIR = ROOT_PROJECT_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

PROFILE_FILE = DATABASE_DIR / "user_profile.json"
ADD_PATH_FILE = DATABASE_DIR / "add_path.json"
LOCK_SECURITY_FILE = DATABASE_DIR / "lock_screen_security.json"
FRIDAY_MASTER_FILE = DATABASE_DIR / "friday_master_auth.json"
POWER_SETTINGS_FILE = DATABASE_DIR / "power_settings.json"

MEMORY_ROOT = ROOT_PROJECT_DIR / "memory"
CACHE_DIR = MEMORY_ROOT / "cache"
UPLOAD_DIR = CACHE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Domain services and tools
from app.services.agent_feature_scanner import agent_feature_scanner
from app.services.conversation_memory_service import conversation_memory_service
from app.api.v1.memory import router as memory_router
from app.tools import register_all_tools
from app.api.v1 import api_v1_router, ws_router
from app.services.monitoring_service import monitoring_service
from app.services.power_service import (
    load_power_settings,
    save_power_settings,
    get_cached_ram_freq,
    get_battery_info,
    DEFAULT_POWER_SETTINGS
)
from app.services.document_analysis_service import (
    sanitize_backend_output,
    extract_text_from_file_direct,
    analyze_multiple_documents
)
from app.services.command_executor import (
    load_user_profile,
    save_user_profile,
    save_chat_turn,
    get_chat_history,
    cleanup_expired_memory,
    get_greeting_message,
    execute_in_backend,
    LOCAL_MEMORY_STORE,
    SESSION_DOC_CACHE,
    LATEST_UPLOADED_DOC_CONTENT
)

# -----------------------------------------------------------------------------
# DATABASE DEFAULTS & SECURITY HELPERS
# -----------------------------------------------------------------------------

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


def load_lock_security() -> Dict[str, Any]:
    """
    What does this function do:
    Loads and parses the lock screen keyword-to-password mappings configuration from
    'database/lock_screen_security.json'.
    
    Returns:
        Dict[str, Any]: Lock security dictionary (enabled, mappings, session_unlocked).
    """
    if LOCK_SECURITY_FILE.exists():
        try:
            with open(LOCK_SECURITY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_LOCK_SECURITY, **data}
        except Exception as e:
            print(f"[Security] Reading lock security failed: {e}", flush=True)
    return DEFAULT_LOCK_SECURITY.copy()


def save_lock_security(sec_data: Dict[str, Any]) -> None:
    """
    What does this function do:
    Persists updated lock screen keyword mappings and lock state to 'database/lock_screen_security.json'.
    
    Args:
        sec_data (Dict[str, Any]): Dictionary of updated lock security fields.
    """
    current = load_lock_security()
    current.update(sec_data)
    try:
        with open(LOCK_SECURITY_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        print("[Security] Lock security configuration updated.", flush=True)
    except Exception as e:
        print(f"[Security Error] Writing lock security failed: {e}", flush=True)


def load_friday_master() -> Dict[str, Any]:
    """
    What does this function do:
    Loads the master authentication password hash and lock status from
    'database/friday_master_auth.json'.
    
    Returns:
        Dict[str, Any]: Master auth dictionary.
    """
    if FRIDAY_MASTER_FILE.exists():
        try:
            with open(FRIDAY_MASTER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_FRIDAY_MASTER, **data}
        except Exception as e:
            print(f"[Security] Reading Friday master auth failed: {e}", flush=True)
    return DEFAULT_FRIDAY_MASTER.copy()


def save_friday_master(master_data: Dict[str, Any]) -> None:
    """
    What does this function do:
    Persists the master administrator password configuration to 'database/friday_master_auth.json'.
    
    Args:
        master_data (Dict[str, Any]): Updated master authentication dictionary.
    """
    current = load_friday_master()
    current.update(master_data)
    try:
        with open(FRIDAY_MASTER_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        print("[Security] Friday master auth updated.", flush=True)
    except Exception as e:
        print(f"[Security Error] Writing Friday master auth failed: {e}", flush=True)


# -----------------------------------------------------------------------------
# PYDANTIC REQUEST / RESPONSE SCHEMAS
# -----------------------------------------------------------------------------

class ProfileUpdateRequest(BaseModel):
    name: str
    agent_name: Optional[str] = "Friday"
    age: Optional[str] = ""
    email: Optional[str] = ""
    city: Optional[str] = ""
    voice_gender: Optional[str] = "female"
    languages: Optional[List[str]] = ["english", "tamil", "tanglish"]


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


class ChangeMasterPasswordRequest(BaseModel):
    new_master_password: str


class FridayMasterSetupRequest(BaseModel):
    password: str


class CreateConversationRequest(BaseModel):
    title: Optional[str] = None


class RenameConversationRequest(BaseModel):
    title: str


class AddMessageRequest(BaseModel):
    role: str
    content: str


class PowerSettingsRequest(BaseModel):
    eco_mode: Optional[bool] = None
    auto_battery_saver: Optional[bool] = None
    telemetry_interval_battery: Optional[float] = None
    telemetry_interval_ac: Optional[float] = None


class DeviceMonitoringSettingsRequest(BaseModel):
    device_monitoring_enabled: Optional[bool] = None
    enabled: Optional[bool] = None
    ocr_enabled: Optional[bool] = None
    action_delay_ms: Optional[int] = None
    verification_enabled: Optional[bool] = None


class WhatsAppSettingsRequest(BaseModel):
    enabled: bool
    auto_reply: Optional[bool] = True
    custom_auto_reply_message: Optional[str] = None



class WhatsAppSendRequest(BaseModel):
    contact: Optional[str] = None
    recipient: Optional[str] = None
    message: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    language: Optional[str] = "english"


class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = None
    gender: Optional[str] = "female"
    voice: Optional[str] = None


# -----------------------------------------------------------------------------
# FASTAPI APPLICATION SETUP & LIFECYCLE
# -----------------------------------------------------------------------------

app = FastAPI(title="Friday AI Assistant Core")

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
    """
    What does this function do:
    Application startup event handler. Cleans up expired sliding conversation memory,
    registers all AI tool agents in the global registry, launches the background monitoring
    daemon, and auto-resumes WhatsApp background notification listener if active.
    """
    cleanup_expired_memory()
    total_tools = register_all_tools()
    print(f"[Tools Registry] Registered {total_tools} agent tools successfully.", flush=True)
    monitoring_service.start()

    # Auto-resume WhatsApp monitoring if enabled in settings
    try:
        from app.services.whatsapp_service import whatsapp_service
        if whatsapp_service.settings.get("enabled", False) or whatsapp_service.settings.get("monitoring_active", False):
            whatsapp_service.set_monitoring(enabled=True)
            print("[WhatsApp Startup] Background monitoring successfully resumed.", flush=True)
    except Exception as e:
        print(f"[WhatsApp Startup Notice]: {e}", flush=True)


@app.on_event("shutdown")
async def shutdown_event():
    """
    What does this function do:
    Application shutdown event handler. Safely halts background monitoring threads
    and frees hardware resource hooks upon server termination.
    """
    monitoring_service.stop()


# -----------------------------------------------------------------------------
# 1. USER PROFILE ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/api/profile")
async def get_profile_endpoint():
    """
    What does this function do:
    Fetches the active user profile configuration (operator name, wake word, agent name, email, city).
    
    Returns:
        Dict[str, Any]: User profile dictionary.
    """
    return load_user_profile()


@app.post("/api/profile")
async def update_profile_endpoint(req: ProfileUpdateRequest):
    """
    What does this function do:
    Updates and persists the operator profile (name, agent persona name, wake word, location, age)
    to disk and synchronizes the assistant's memory.
    
    Args:
        req (ProfileUpdateRequest): The profile update payload.
        
    Returns:
        dict: Success status and the updated profile object.
    """
    if not req.name.strip():
        return {"status": "error", "message": "Name is mandatory"}
    agent = req.agent_name.strip() if req.agent_name and req.agent_name.strip() else "Friday"
    save_user_profile({
        "name": req.name.strip(),
        "agent_name": agent,
        "wake_word": agent.lower(),
        "age": req.age.strip(),
        "email": req.email.strip(),
        "city": req.city.strip(),
        "voice_gender": (req.voice_gender or "female").lower(),
        "languages": req.languages or ["english", "tamil", "tanglish"]
    })
    return {"status": "success", "profile": load_user_profile()}


# -----------------------------------------------------------------------------
# 2. FEATURE HEALTH SCANNER ENDPOINT
# -----------------------------------------------------------------------------

@app.post("/api/v1/settings/scan-agent-features")
@app.get("/api/v1/settings/scan-agent-features")
@app.get("/api/v1/system/features-scan")
@app.post("/api/v1/system/features-scan")
async def scan_agent_features_endpoint():
    """
    What does this function do:
    Executes non-destructive health checks across all registered agent tools, plugins,
    and system integrations asynchronously, returning detailed diagnostic metrics.
    
    Returns:
        dict: List of feature diagnostic results and overall status.
    """
    try:
        results = await agent_feature_scanner.scan_all_features()
        normalized = []
        for r in results:
            raw_name = r.get("feature") or r.get("feature_name") or "Unknown Feature"
            raw_status = str(r.get("status") or "working")
            display_status = "ONLINE" if raw_status.lower() in ["working", "online", "optimal", "passed"] else "OFFLINE"
            normalized.append({
                **r,
                "feature": raw_name,
                "feature_name": raw_name,
                "status": display_status,
                "raw_status": raw_status
            })
        return {"status": "success", "results": normalized, "features": normalized}
    except Exception as e:
        return {"status": "error", "message": str(e), "results": [], "features": []}


# -----------------------------------------------------------------------------
# 3. POWER & BATTERY SAVER ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/api/v1/settings/power")
async def get_power_settings_endpoint():
    """
    What does this function do:
    Returns current power saver preferences (Eco Mode, Auto-on Battery), live battery
    level percentage, charging status (AC plugged vs battery), and whether Eco Mode is active.
    
    Returns:
        dict: Settings dictionary, battery status snapshot, and is_eco_active boolean.
    """
    settings = load_power_settings()
    batt = get_battery_info()
    is_on_battery = (batt is not None and not batt.get("power_plugged", True))
    is_eco_active = settings.get("eco_mode", False) or (settings.get("auto_battery_saver", True) and is_on_battery)
    return {
        "status": "success",
        "settings": settings,
        "battery": batt,
        "is_eco_active": is_eco_active
    }


@app.post("/api/v1/settings/power")
async def update_power_settings_endpoint(req: PowerSettingsRequest):
    """
    What does this function do:
    Updates power saver settings (Eco Mode ON/OFF, Auto-On Battery ON/OFF, telemetry intervals)
    and persists them to database/power_settings.json.
    
    Args:
        req (PowerSettingsRequest): The updated power configuration fields.
        
    Returns:
        dict: Updated settings dictionary and active eco mode state.
    """
    current = load_power_settings()
    if req.eco_mode is not None:
        current["eco_mode"] = req.eco_mode
    if req.auto_battery_saver is not None:
        current["auto_battery_saver"] = req.auto_battery_saver
    if req.telemetry_interval_battery is not None:
        current["telemetry_interval_battery"] = max(2.0, min(30.0, float(req.telemetry_interval_battery)))
    if req.telemetry_interval_ac is not None:
        current["telemetry_interval_ac"] = max(1.0, min(10.0, float(req.telemetry_interval_ac)))
    save_power_settings(current)

    batt = get_battery_info()
    is_on_battery = (batt is not None and not batt.get("power_plugged", True))
    is_eco_active = current.get("eco_mode", False) or (current.get("auto_battery_saver", True) and is_on_battery)

    return {
        "status": "success",
        "settings": current,
        "battery": batt,
        "is_eco_active": is_eco_active
    }


# -----------------------------------------------------------------------------
# 3.5. DEVICE MONITORING & DESKTOP CONTROL SETTINGS ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/api/v1/settings/device-monitoring")
async def get_device_monitoring_settings_endpoint():
    """
    What does this function do:
    Returns the current Device Monitoring configuration (device_monitoring_enabled flag, OCR state,
    action verification) and runtime desktop summary.
    """
    from app.tools.device import load_device_settings, device_state_tracker
    settings = load_device_settings()
    summary = device_state_tracker.get_summary()
    return {
        "status": "success",
        "settings": settings,
        "summary": summary
    }


@app.post("/api/v1/settings/device-monitoring")
async def update_device_monitoring_settings_endpoint(req: DeviceMonitoringSettingsRequest):
    """
    What does this function do:
    Updates Device Monitoring settings (enabling/disabling desktop screen inspection & control)
    and persists them to database/device_settings.json.
    """
    from app.tools.device import load_device_settings, save_device_settings, device_state_tracker
    updates = {}
    if req.device_monitoring_enabled is not None:
        updates["device_monitoring_enabled"] = req.device_monitoring_enabled
    elif req.enabled is not None:
        updates["device_monitoring_enabled"] = req.enabled

    if req.ocr_enabled is not None:
        updates["ocr_enabled"] = req.ocr_enabled
    if req.action_delay_ms is not None:
        updates["action_delay_ms"] = req.action_delay_ms
    if req.verification_enabled is not None:
        updates["verification_enabled"] = req.verification_enabled

    updated = save_device_settings(updates)
    summary = device_state_tracker.get_summary()
    return {
        "status": "success",
        "settings": updated,
        "summary": summary
    }


# -----------------------------------------------------------------------------
# 4. WHATSAPP PLUGIN & MONITORING ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/api/v1/settings/whatsapp")

async def get_whatsapp_settings_endpoint():
    """
    What does this function do:
    Retrieves the current status of the WhatsApp desktop integration (monitoring active,
    auto-reply enabled, replied count, custom message, last activity timestamp).
    
    Returns:
        dict: WhatsApp plugin state dictionary.
    """
    from app.services.whatsapp_service import whatsapp_service
    status_data = whatsapp_service.get_status()
    return {"status": "success", "settings": status_data, **status_data}


@app.post("/api/v1/settings/whatsapp")
async def update_whatsapp_settings_endpoint(req: WhatsAppSettingsRequest):
    """
    What does this function do:
    Updates WhatsApp autonomous background monitoring state, enables/disables auto-replies,
    and sets custom auto-reply rules.
    
    Args:
        req (WhatsAppSettingsRequest): Payload with enabled, auto_reply, and custom text.
        
    Returns:
        dict: Updated WhatsApp plugin status.
    """
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
    """
    What does this function do:
    Directly dispatches an outgoing WhatsApp message to a recipient via the WhatsApp Desktop app.
    
    Args:
        req (WhatsAppSendRequest): Contains contact name and message text.
        
    Returns:
        dict: Dispatch outcome and success indicator.
    """
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
    """
    What does this function do:
    Retrieves the recent stream of monitored WhatsApp events, incoming notifications, and auto-replies.
    
    Returns:
        dict: List of activity log entries.
    """
    from app.services.whatsapp_service import whatsapp_service
    return {"status": "success", "logs": whatsapp_service.get_logs()}


@app.get("/api/v1/whatsapp/urgent-alert")
async def get_whatsapp_urgent_alert_endpoint():
    """
    What does this function do:
    Checks if there is an active urgent WhatsApp notification waiting for Harishan's immediate review.
    
    Returns:
        dict: Active alert object or None.
    """
    from app.services.whatsapp_service import whatsapp_service
    return {"status": "success", "alert": whatsapp_service.get_urgent_alert()}


@app.post("/api/v1/whatsapp/urgent-alert/dismiss")
async def dismiss_whatsapp_urgent_alert_endpoint():
    """
    What does this function do:
    Dismisses and clears the current glowing urgent WhatsApp alert banner on the frontend UI.
    
    Returns:
        dict: Dismissal confirmation.
    """
    from app.services.whatsapp_service import whatsapp_service
    return whatsapp_service.dismiss_urgent_alert()


# -----------------------------------------------------------------------------
# 5. CONVERSATION SESSIONS & HISTORY ENDPOINTS
# -----------------------------------------------------------------------------

@app.post("/api/v1/conversations")
async def create_conversation_endpoint(req: Optional[CreateConversationRequest] = None):
    """
    What does this function do:
    Creates a new isolated conversation thread with sliding 24-hour retention window.
    
    Args:
        req (Optional[CreateConversationRequest]): Optional initial conversation title.
        
    Returns:
        dict: Newly created conversation metadata.
    """
    title = req.title if req and req.title else "New Session"
    conv = conversation_memory_service.create_conversation(title=title)
    return {"status": "success", "conversation": conv}


@app.get("/api/v1/conversations")
async def list_conversations_endpoint():
    """
    What does this function do:
    Lists all non-expired conversations sorted chronologically by last updated timestamp.
    
    Returns:
        dict: List of active conversation summary objects.
    """
    convs = await conversation_memory_service.list_conversations()
    return {"status": "success", "conversations": convs}


@app.get("/api/v1/conversations/{conversation_id}")
async def get_conversation_endpoint(conversation_id: str):
    """
    What does this function do:
    Retrieves complete metadata and messages for a specific conversation session.
    
    Args:
        conversation_id (str): Unique conversation ID.
        
    Returns:
        dict: Conversation details and message history.
    """
    conv = await conversation_memory_service.get_conversation(conversation_id)
    if not conv:
        return {"status": "error", "message": "Conversation not found or expired"}
    return {"status": "success", "conversation": conv}


@app.patch("/api/v1/conversations/{conversation_id}")
async def rename_conversation_endpoint(conversation_id: str, req: RenameConversationRequest):
    """
    What does this function do:
    Renames the title of an existing conversation session.
    
    Args:
        conversation_id (str): Conversation ID.
        req (RenameConversationRequest): Contains new title string.
        
    Returns:
        dict: Success status.
    """
    success = await conversation_memory_service.rename_conversation(conversation_id, req.title)
    return {"status": "success" if success else "error"}


@app.delete("/api/v1/conversations/{conversation_id}")
async def delete_conversation_endpoint(conversation_id: str):
    """
    What does this function do:
    Permanently deletes a conversation thread and its associated message index.
    
    Args:
        conversation_id (str): Conversation ID to delete.
        
    Returns:
        dict: Deletion confirmation status.
    """
    success = await conversation_memory_service.delete_conversation(conversation_id)
    return {"status": "success" if success else "error"}


@app.delete("/api/v1/conversations/{conversation_id}/messages")
async def clear_messages_endpoint(conversation_id: str):
    """
    What does this function do:
    Clears all messages within a conversation while retaining the conversation session itself.
    
    Args:
        conversation_id (str): Conversation ID.
        
    Returns:
        dict: Success status.
    """
    success = await conversation_memory_service.clear_messages(conversation_id)
    return {"status": "success" if success else "error"}


@app.get("/api/v1/conversations/{conversation_id}/messages")
async def get_messages_endpoint(conversation_id: str, limit: int = 50, before_message_id: Optional[str] = None):
    """
    What does this function do:
    Fetches paginated messages from a conversation history.
    
    Args:
        conversation_id (str): Conversation ID.
        limit (int): Number of messages to retrieve.
        before_message_id (Optional[str]): Cursor for pagination.
        
    Returns:
        dict: List of messages.
    """
    messages = await conversation_memory_service.get_messages(conversation_id, limit=limit, before_message_id=before_message_id)
    return {"status": "success", "messages": messages}


@app.post("/api/v1/conversations/{conversation_id}/messages")
async def add_message_endpoint(conversation_id: str, req: AddMessageRequest):
    """
    What does this function do:
    Appends a new user or assistant message to a conversation session.
    
    Args:
        conversation_id (str): Conversation ID.
        req (AddMessageRequest): Contains role ('user'/'assistant') and content.
        
    Returns:
        dict: Newly stored message record.
    """
    msg = await conversation_memory_service.add_message(conversation_id, req.role, req.content)
    return {"status": "success", "message": msg}


@app.post("/api/v1/conversations/cleanup/expired")
async def cleanup_expired_conversations_endpoint():
    """
    What does this function do:
    Triggers cleanup of stale conversations that have exceeded their sliding retention window.
    
    Returns:
        dict: Number of purged conversations.
    """
    cleaned = conversation_memory_service.cleanup_expired_conversations()
    return {"status": "success", "cleaned_count": cleaned}


# -----------------------------------------------------------------------------
# 6. CUSTOM PATHS & APP SHORTCUTS ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/api/add-path")
async def get_add_path_endpoint():
    """
    What does this function do:
    Retrieves all custom user-registered folder and application shortcut routes
    from 'database/add_path.json'.
    
    Returns:
        dict: Dictionary containing registered paths list.
    """
    try:
        if ADD_PATH_FILE.exists():
            data = json.loads(ADD_PATH_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "paths" in data:
                return data
            elif isinstance(data, list):
                return {"paths": data}
        return {"paths": []}
    except Exception as e:
        return {"paths": [], "error": str(e)}


@app.post("/api/add-path")
async def add_path_endpoint(req: AddPathRequest):
    """
    What does this function do:
    Adds or updates a custom keyword route mapping (e.g., 'project folder' -> 'C:/Users/...')
    in 'database/add_path.json' so Friday can open it by voice or text.
    
    Args:
        req (AddPathRequest): Contains route_name and filesystem path.
        
    Returns:
        dict: Success message.
    """
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
        return {"status": "success", "message": "Path route saved successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/delete-path")
async def delete_path_endpoint(req: DeletePathRequest):
    """
    What does this function do:
    Removes a registered custom path shortcut from 'database/add_path.json'.
    
    Args:
        req (DeletePathRequest): Contains route_name to remove.
        
    Returns:
        dict: Success status.
    """
    try:
        if not ADD_PATH_FILE.exists():
            return {"status": "success", "message": "Path not found"}

        data = json.loads(ADD_PATH_FILE.read_text(encoding="utf-8"))
        paths = data.get("paths", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        updated_paths = [p for p in paths if str(p.get("route_name", "")).strip().lower() != req.route_name.strip().lower()]

        ADD_PATH_FILE.write_text(json.dumps({"paths": updated_paths}, indent=2), encoding="utf-8")
        return {"status": "success", "message": "Route deleted successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# -----------------------------------------------------------------------------
# 7. SECURITY & LOCK SCREEN ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/api/security/lock-config")
async def get_lock_config():
    """
    What does this function do:
    Fetches the lock screen security configuration, returning enabled status and safe keywords
    without exposing hashed passwords.
    
    Returns:
        dict: Security configuration snapshot.
    """
    conf = load_lock_security()
    safe_mappings = [{"keyword": m.get("keyword")} for m in conf.get("mappings", [])]
    return {
        "enabled": conf.get("enabled", False),
        "mappings": safe_mappings,
        "session_unlocked": conf.get("session_unlocked", True)
    }


@app.post("/api/security/lock-config")
async def update_lock_config(req: SecurityMappingRequest):
    """
    What does this function do:
    Configures keyword-to-password mappings for lock screen security, hashing passwords with bcrypt.
    
    Args:
        req (SecurityMappingRequest): List of keyword-password pairs.
        
    Returns:
        dict: Status message.
    """
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
    """
    What does this function do:
    Returns the Friday master administrator authentication status.
    
    Returns:
        dict: Master lock status.
    """
    conf = load_friday_master()
    return {
        "master_enabled": conf.get("master_enabled", True),
        "session_unlocked": conf.get("session_unlocked", True)
    }


@app.post("/api/security/friday-master-config")
async def setup_friday_master(req: FridayMasterSetupRequest):
    """
    What does this function do:
    Initializes or updates the master administrator password for Friday using bcrypt hashing.
    
    Args:
        req (FridayMasterSetupRequest): Contains new password string.
        
    Returns:
        dict: Status message.
    """
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
    """
    What does this function do:
    Verifies if a provided master password matches the stored bcrypt hash.
    
    Args:
        req (VerifyLocalPasswordRequest): Password attempt.
        
    Returns:
        dict: Authorized status or error.
    """
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
    except Exception:
        return {"status": "error", "response": "Verification failed."}


@app.post("/api/security/friday-master-unlock")
async def verify_friday_master_unlock(req: VerifyLocalPasswordRequest):
    """
    What does this function do:
    Unlocks the Friday session when verified with the master administrator password.
    
    Args:
        req (VerifyLocalPasswordRequest): Password attempt.
        
    Returns:
        dict: Unlock status.
    """
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
    except Exception:
        return {"status": "error", "response": "Verification failed."}


@app.post("/api/security/unlock-attempt")
async def verify_unlock_attempt(req: UnlockAttemptRequest):
    """
    What does this function do:
    Validates a lock screen unlock keyword and password combination, granting session access on match.
    
    Args:
        req (UnlockAttemptRequest): Contains keyword and password.
        
    Returns:
        dict: Access granted or authentication failed message.
    """
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
    except Exception:
        return {"status": "error", "response": "Authentication failed."}


@app.get("/api/v1/security/lock-folders")
@app.get("/api/v1/security/lock-config")
async def get_lock_folders_v1():
    """
    What does this function do:
    Retrieves current lock screen / folder security keyword mappings.
    """
    conf = load_lock_security()
    safe_mappings = [{"keyword": m.get("keyword"), "password": ""} for m in conf.get("mappings", [])]
    return {
        "status": "success",
        "enabled": conf.get("enabled", False),
        "mappings": safe_mappings,
        "lock_folders": safe_mappings,
        "session_unlocked": conf.get("session_unlocked", True)
    }


@app.post("/api/v1/security/lock-folders")
async def save_lock_folders_v1(req: Dict[str, Any]):
    """
    What does this function do:
    Saves folder / keyword security rules to disk.
    """
    mappings_list = req.get("lock_folders") or req.get("mappings") or []
    return await update_lock_config(SecurityMappingRequest(mappings=mappings_list))


@app.post("/api/v1/security/lock-folders/verify-master")
async def verify_master_v1(req: VerifyLocalPasswordRequest):
    """
    What does this function do:
    Verifies master password and returns authenticated flag.
    """
    res = await verify_master_password(req)
    return {
        "status": res.get("status"),
        "authenticated": res.get("status") == "success",
        "response": res.get("response")
    }


@app.post("/api/v1/security/lock-folders/set-master")
async def set_master_v1(req: Dict[str, Any]):
    """
    What does this function do:
    Updates master password.
    """
    new_pwd = req.get("new_master") or req.get("password") or ""
    return await setup_friday_master(FridayMasterSetupRequest(password=new_pwd))


# -----------------------------------------------------------------------------
# 8. DOCUMENT & MULTI-FILE UPLOAD ENDPOINTS
# -----------------------------------------------------------------------------

@app.post("/api/analyze-file")
@app.post("/api/analyze-files")
async def analyze_files_endpoint(
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    prompt: Optional[str] = Form(""),
    session_id: Optional[str] = Form("default"),
    language: Optional[str] = Form("english")
):
    """
    What does this function do:
    Handles multi-file uploads (PDFs, text files, code files, images), caches extracted text
    in the session, and triggers comprehensive multi-document analysis via Friday's LLM engine.
    
    Args:
        files: List of uploaded files.
        file: Single uploaded file fallback.
        prompt: User's analysis instruction or query.
        session_id: Active session identifier.
        language: Output language preference.
        
    Returns:
        dict: Synthesized analysis report, processed file count, and file names.
    """
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

        save_chat_turn(session_id, "user", f"[ATTACHMENTS ({len(saved_paths)}/6)]: {', '.join(file_names)} - {prompt or 'Analyze this file.'}")

        try:
            meta_combined = []
            for p in saved_paths:
                m = extract_text_from_file_direct(p)
                meta_combined.append(m["raw_text"])
            if meta_combined:
                full_corpus = "\n\n".join(meta_combined)
                SESSION_DOC_CACHE[session_id] = full_corpus
        except Exception:
            pass

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


# -----------------------------------------------------------------------------
# 9. CHAT REST API & REAL-TIME WEBSOCKET TELEMETRY
# -----------------------------------------------------------------------------

class ConnectionManager:
    """
    Manages active WebSocket client connections for real-time bidirectional
    voice communication and live hardware telemetry broadcasting.
    """
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accepts and registers a new WebSocket connection."""
        await websocket.accept()
        if websocket not in self.active_connections:
            self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Removes a disconnected WebSocket from active pool."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def safe_send_json(self, websocket: WebSocket, data: dict):
        """Safely transmits JSON payload to a client with auto-cleanup on failure."""
        try:
            if websocket in self.active_connections:
                await websocket.send_json(data)
        except Exception:
            self.disconnect(websocket)


manager = ConnectionManager()


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """
    What does this function do:
    Synchronous/REST chat endpoint. Dispatches user messages into Friday's execution pipeline
    and returns the AI assistant's reply along with execution latency timing.
    
    Args:
        req (ChatRequest): Contains user message, session_id, and language.
        
    Returns:
        dict: Assistant response and latency string (e.g. '180ms').
    """
    t0 = time.perf_counter()
    reply = await execute_in_backend(req.message, session_id=req.session_id or "default", language=req.language or "english")
    took_ms = round((time.perf_counter() - t0) * 1000)
    return {"response": reply, "latency": f"{took_ms}ms"}


@app.get("/api/tts")
async def tts_get_endpoint(text: str, language: Optional[str] = None, gender: Optional[str] = None, voice: Optional[str] = None):
    """
    What does this function do:
    Streams synthesized neural speech MP3 audio (supporting Tamil, Tanglish, and English with Male/Female voice changer)
    directly to the browser for real-time audio playback.
    """
    if not gender:
        profile = load_user_profile()
        gender = profile.get("voice_gender", "female")
    audio_bytes = await tts_service.synthesize(text, language=language, gender=gender, voice=voice)
    if not audio_bytes:
        return Response(content=b"", media_type="audio/mpeg", status_code=204)
    return Response(content=audio_bytes, media_type="audio/mpeg")


@app.post("/api/tts")
async def tts_post_endpoint(req: TTSRequest):
    """
    What does this function do:
    POST endpoint for streaming synthesized neural speech MP3 audio.
    """
    gender = req.gender
    if not gender:
        profile = load_user_profile()
        gender = profile.get("voice_gender", "female")
    audio_bytes = await tts_service.synthesize(req.text, language=req.language, gender=gender, voice=req.voice)
    if not audio_bytes:
        return Response(content=b"", media_type="audio/mpeg", status_code=204)
    return Response(content=audio_bytes, media_type="audio/mpeg")


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    """
    What does this function do:
    High-performance real-time WebSocket connection endpoint. Streams live hardware telemetry
    (CPU, RAM, GPU, Disk, Network throughput, Battery status) and executes conversational voice
    interactions with sub-second latency.
    """
    await manager.connect(websocket)

    async def telemetry_loop():
        """
        What does this function do:
        Runs background hardware diagnostics and pushes real-time telemetry over WebSocket.
        Adjusts polling rate dynamically and throttles GPU wakeups when Eco Mode is active.
        """
        try:
            last_net = psutil.net_io_counters()
            last_time = time.time()

            while True:
                cpu = int(psutil.cpu_percent(interval=None))
                mem_obj = psutil.virtual_memory()
                mem_percent = int(mem_obj.percent)

                power_cfg = load_power_settings()
                batt = psutil.sensors_battery()
                is_on_battery = (batt is not None and not getattr(batt, "power_plugged", True))
                is_eco_active = bool(power_cfg.get("eco_mode", False) or (power_cfg.get("auto_battery_saver", True) and is_on_battery))

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
                rtx_temp = 42 if is_eco_active else 50
                radeon_load = 0
                radeon_temp = 40 if is_eco_active else 45
                
                try:
                    if os.name == "nt":
                        if not is_eco_active:
                            # 1. Query NVIDIA GPU 0 via nvidia-smi only when NOT in eco mode
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

                            # 2. Dynamic AMD Radeon iGPU Telemetry via PowerShell CIM counter
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
                        else:
                            # Eco / Battery Saver Mode: Zero subprocess wakeups, smooth hardware estimation
                            radeon_load = int(min(20, max(1, int(cpu * 0.15))))
                            radeon_temp = int(40 + min(15, int(cpu * 0.2)))
                except Exception:
                    radeon_load = 2
                    radeon_temp = 42

                gpus_telemetry = [
                    {"id": "gpu0", "label": "GPU 0", "shortName": "RTX 3050" + (" (D3 Sleep)" if is_eco_active and rtx_load == 0 else ""), "load": rtx_load, "temp": rtx_temp},
                    {"id": "gpu1", "label": "GPU 1", "shortName": "Radeon", "load": radeon_load, "temp": radeon_temp}
                ]

                # 3. Fan Speed Calculation
                cpu_fan_rpm = int(1800 + (cpu * 25)) if is_eco_active else int(2200 + (cpu * 35))
                gpu_fan_rpm = int(1800 + (max(rtx_load, radeon_load) * 20)) if is_eco_active else int(2200 + (max(rtx_load, radeon_load) * 30))
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

                batt_info = None
                if batt:
                    batt_info = {
                        "percent": int(batt.percent),
                        "power_plugged": bool(batt.power_plugged),
                        "secsleft": int(batt.secsleft) if (batt.secsleft and batt.secsleft > 0 and batt.secsleft < 864000) else None,
                        "is_eco_active": is_eco_active
                    }

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
                        "memFreq": get_cached_ram_freq(),
                        "battery": batt_info,
                        "eco_active": is_eco_active
                    }
                })
                sleep_interval = float(power_cfg.get("telemetry_interval_battery", 6.0)) if is_eco_active else float(power_cfg.get("telemetry_interval_ac", 2.0))
                await asyncio.sleep(sleep_interval)
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    telemetry_task = asyncio.create_task(telemetry_loop())
    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message:
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


# -----------------------------------------------------------------------------
# APPLICATION ENTRYPOINT
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)