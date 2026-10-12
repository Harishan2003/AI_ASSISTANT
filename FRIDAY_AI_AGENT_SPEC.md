# Friday AI Assistant — Complete Technical Specification

> **Version:** 2.0.0  
> **Owner:** Harishan  
> **Platform:** Windows 10 / 11  
> **Date:** September 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Directory Structure](#4-directory-structure)
5. [Core Agent Engine](#5-core-agent-engine)
6. [Agent Modules](#6-agent-modules)
7. [Service Layer](#7-service-layer)
8. [Memory System](#8-memory-system)
9. [Speech & Voice Pipeline](#9-speech--voice-pipeline)
10. [Vision & Screen Intelligence](#10-vision--screen-intelligence)
11. [Tool Registry & Capabilities](#11-tool-registry--capabilities)
12. [LLM Provider System](#12-llm-provider-system)
13. [REST API Reference](#13-rest-api-reference)
14. [WhatsApp Automation](#14-whatsapp-automation)
15. [Desktop Overlay HUD](#15-desktop-overlay-hud)
16. [Security & Permission System](#16-security--permission-system)
17. [Database Schema](#17-database-schema)
18. [Configuration Reference](#18-configuration-reference)
19. [Data Flow Diagrams](#19-data-flow-diagrams)
20. [Known Limitations & Roadmap](#20-known-limitations--roadmap)

---

## 1. Overview

**Friday** is a fully autonomous, locally-running Windows AI desktop assistant named after the AI in Iron Man. It provides a unified command-and-control interface for the user's PC through voice, text, and a futuristic transparent HUD overlay.

### Core Identity

| Property       | Value                              |
|----------------|------------------------------------|
| Agent Name     | Friday                             |
| Wake Word      | `friday`                           |
| Primary User   | Harishan                           |
| Persona        | Sharp, helpful, adaptive, proactive |
| Architecture   | ReAct loop (Reason + Act)          |
| Runtime        | Windows 10/11, Python 3.10+        |

### Design Philosophy

- **Local-first**: All core processing runs locally. No cloud dependency for system commands.
- **Context-aware**: Friday detects the foreground application and adapts its behavior accordingly.
- **Multi-modal**: Accepts text chat, voice commands, file uploads, and screen captures.
- **Autonomous**: Can chain multiple tool calls to satisfy complex multi-step requests without manual intervention.
- **Safe**: Requires explicit user confirmation before executing destructive or sensitive operations.

---

## 2. System Architecture

```
USER INTERFACES
  React Frontend (Vite + React)
  Desktop Overlay (pywebview / Edge WebView2)
  Voice / Wake Word (SenseVoice + Piper TTS)
         |
         | HTTP / WebSocket
         v
FASTAPI BACKEND (Port 8000)
  main.py / app/main.py
  ChatAPI | VoiceAPI | VisionAPI | SystemAPI | RAG
         |
         v
SERVICE LAYER
  AgentRouter | CommandExecutor | ContextService | VoiceService
  WhatsAppService | SystemService | AlarmService | VisionService
  MemoryService | DocumentService | SecurityService | TTS/STT
         |
         v
CORE AGENT ENGINE
  AgentEngine (ReAct Loop) | ToolRouter | PermManager
  LLM Provider Factory     | AuditLogger | EventBus
         |
         v
TOOL REGISTRY (50+ tools)
  System | FileSystem | Browser | WhatsApp | Terminal
  Memory | Screenshot | Clipboard | Calendar | Weather | Email
         |
         v
MEMORY SYSTEM
  SessionMemory | LongTermMemory | VectorStore | ProfileMemory
  ConversationMemory | SQLite DB | Embeddings

EXTERNAL PROVIDERS
  Groq API | Ollama (Local) | OpenRouter Cloud | OpenAI API
```

---

## 3. Technology Stack

### Backend

| Component         | Technology                       | Version      |
|-------------------|----------------------------------|--------------|
| Web Framework     | FastAPI                          | >= 0.111.0   |
| ASGI Server       | Uvicorn                          | >= 0.30.0    |
| Data Validation   | Pydantic v2                      | >= 2.0.0     |
| ORM               | SQLAlchemy                       | >= 2.0.0     |
| Async DB Driver   | asyncpg                          | >= 0.29.0    |
| Cache / Pub-Sub   | Redis                            | >= 5.0.0     |
| LLM SDK           | OpenAI Python SDK (compat.)      | >= 1.30.0    |
| Auth              | python-jose + passlib[bcrypt]    | ---          |
| Template Engine   | Jinja2                           | >= 3.1.4     |
| File I/O          | aiofiles                         | >= 23.2.1    |
| Screen Control    | pyautogui, uiautomation          | ---          |
| Windows APIs      | ctypes (Win32), winreg, psutil   | ---          |
| PDF Parsing       | pypdf                            | ---          |
| Browser Automation| Playwright                       | ---          |
| STT               | SenseVoice-Small, Whisper        | ---          |
| TTS               | Piper TTS (local ONNX)           | ---          |

### Frontend

| Component         | Technology               | Version   |
|-------------------|--------------------------|-----------|
| Framework         | React                    | >= 18.x   |
| Build Tool        | Vite                     | >= 5.x    |
| Language          | TypeScript               | ---       |
| Routing           | React Router             | ---       |
| State Management  | Context API + Hooks      | ---       |
| HTTP Client       | Fetch / Axios            | ---       |

### Desktop Overlay

| Component         | Technology               |
|-------------------|--------------------------|
| Window            | pywebview (Edge WebView2)|
| Rendering         | HTML5 Canvas + CSS       |
| Transparency      | DWM Glass (Win32 API)    |
| Fonts             | Orbitron, Inter, JetBrains Mono |

---

## 4. Directory Structure

```
AI_ASSISTANT/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── base_agent.py
│   │   │   ├── browser_agent.py        # Browser/context automation
│   │   │   ├── memory_agent.py         # Memory read/write agent
│   │   │   ├── voice_agent.py
│   │   │   ├── vision_agent.py
│   │   │   ├── chat_agent.py
│   │   │   ├── coding_agent.py
│   │   │   ├── system_agent.py
│   │   │   ├── tool_agent.py
│   │   │   ├── research_agent.py
│   │   │   ├── planner_agent.py
│   │   │   └── orchestrator.py
│   │   ├── api/v1/
│   │   │   ├── chat.py
│   │   │   ├── voice.py
│   │   │   ├── vision.py
│   │   │   ├── memory.py
│   │   │   ├── tools_api.py
│   │   │   ├── system_api.py
│   │   │   ├── agent_api.py
│   │   │   ├── tasks_api.py
│   │   │   ├── monitoring_ws.py
│   │   │   ├── audit_api.py
│   │   │   └── health.py
│   │   ├── core/
│   │   │   ├── agent.py                # AgentEngine (ReAct loop)
│   │   │   ├── agent_config.py
│   │   │   ├── config.py               # Settings (env vars)
│   │   │   ├── tool_router.py
│   │   │   ├── permission_manager.py
│   │   │   ├── audit_logger.py
│   │   │   ├── event_bus.py
│   │   │   └── llm/
│   │   │       ├── models.py
│   │   │       ├── base.py
│   │   │       ├── provider_factory.py
│   │   │       ├── groq_provider.py
│   │   │       ├── ollama_provider.py
│   │   │       ├── openai_provider.py
│   │   │       └── openrouter_provider.py
│   │   ├── memory/
│   │   │   ├── memory_manager.py       # Unified memory orchestrator
│   │   │   ├── conversation_memory.py
│   │   │   ├── long_term_memory.py
│   │   │   ├── profile_memory.py
│   │   │   ├── session_memory.py
│   │   │   ├── vector_store.py
│   │   │   └── embeddings.py
│   │   ├── services/
│   │   │   ├── agent_router.py         # Intent -> tool routing
│   │   │   ├── command_executor.py     # Primary command engine (~2300 lines)
│   │   │   ├── context_service.py      # Foreground app context (~885 lines)
│   │   │   ├── system_service.py
│   │   │   ├── voice_service.py
│   │   │   ├── whatsapp_service.py     # WhatsApp desktop automation
│   │   │   ├── chat_service.py
│   │   │   ├── alarm_service.py
│   │   │   ├── vision_service.py
│   │   │   ├── document_service.py
│   │   │   ├── security_service.py
│   │   │   ├── tts_service.py
│   │   │   ├── web_search_service.py
│   │   │   ├── web_search_context.py   # Tavily integration
│   │   │   ├── monitoring_service.py
│   │   │   └── context_state.py        # Shared mutable context
│   │   ├── speech/
│   │   │   ├── sensevoice_stt.py       # SenseVoice-Small STT
│   │   │   ├── whisper_stt.py          # Whisper STT fallback
│   │   │   ├── piper_tts.py            # Piper ONNX TTS
│   │   │   ├── wakeword.py             # Wake-word detector
│   │   │   └── vad.py                  # Voice activity detection
│   │   ├── tools/                      # Individual tool implementations
│   │   ├── models/                     # SQLAlchemy DB models
│   │   ├── schemas/                    # Pydantic schemas
│   │   └── database/                   # DB access layer
│   ├── main.py
│   ├── run.py
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.tsx
│       ├── components/
│       ├── pages/
│       ├── services/
│       ├── hooks/
│       ├── store/
│       └── types/
├── database/
│   ├── friday_agent.db             # SQLite persistent store
│   ├── user_profile.json           # User identity config
│   ├── add_path.json               # Custom app path registry
│   ├── device_settings.json
│   ├── overlay_config.json
│   ├── lock_screen_security.json
│   └── power_settings.json
├── models/
│   ├── whisper/
│   ├── piper/
│   ├── embeddings/
│   ├── local_llm/
│   └── vision/
├── knowledge/
│   ├── pdf/
│   ├── docx/
│   ├── csv/
│   ├── txt/
│   └── web/
├── desktop_overlay.py              # Standalone HUD launcher
├── scripts/
├── docker/
└── logs/
```

---

## 5. Core Agent Engine

### 5.1 AgentEngine (`app/core/agent.py`)

The `AgentEngine` implements the **ReAct (Reason + Act)** loop — the core decision-making pattern that allows Friday to autonomously chain tool calls to solve complex multi-step tasks.

```
User Query
    |
    v
Build System Prompt
  (OS info + current time + user memories from DB)
    |
    v
ReAct Iteration Loop (max 6 iterations)
  |
  1. LLM Call with tool schemas
  |    |-- No tool_calls -> Return final answer
  |    |
  |    +-- tool_calls[] present:
  |          for each tool_call:
  |            - Lookup tool in ToolRouter
  |            - Check permission level
  |            - Execute tool function
  |            - Append result to message history
  |
  2. Append assistant + tool results to messages[]
  3. Loop back to step 1
    |
    v
AgentResponse {
  content, success,
  executed_tools[], requires_confirmation
}
```

#### System Prompt Variables

The system prompt is dynamically built on every invocation:

| Variable          | Source                                  |
|-------------------|-----------------------------------------|
| `{os_info}`       | `platform.system()` + `platform.release()` |
| `{user_name}`     | `os.getenv("USERNAME")`                 |
| `{current_time}`  | `datetime.datetime.now()`              |
| `{user_memories}` | `agent_db.get_facts(limit=10)`          |

#### AgentResponse Schema

```python
class AgentResponse:
    content: str                     # Final text response
    success: bool                    # Execution success flag
    executed_tools: List[ToolResult] # All tool calls made
    requires_confirmation: bool      # Prompts user before proceeding
    error: Optional[str]             # Error message if failed
    error_code: Optional[str]        # Machine-readable error code
```

---

## 6. Agent Modules

Friday has a multi-agent architecture with specialized sub-agents:

| Agent                | File                   | Responsibility                                      |
|----------------------|------------------------|-----------------------------------------------------|
| **Memory Agent**     | `memory_agent.py`      | Store/recall user facts, preferences, conversation history |
| **Browser Agent**    | `browser_agent.py`     | UI automation, context-aware browser commands, tab management |
| **Voice Agent**      | `voice_agent.py`       | STT/TTS pipeline coordination                       |
| **Vision Agent**     | `vision_agent.py`      | Screen capture, window analysis, OCR                |
| **Chat Agent**       | `chat_agent.py`        | General LLM-based conversation                      |
| **System Agent**     | `system_agent.py`      | OS commands, process management, hardware stats     |
| **Tool Agent**       | `tool_agent.py`        | Direct tool invocation for registered tools         |
| **Coding Agent**     | `coding_agent.py`      | Code generation and terminal execution              |
| **Research Agent**   | `research_agent.py`    | Web search + document synthesis                     |
| **Planner Agent**    | `planner_agent.py`     | Multi-step task planning and decomposition          |
| **Orchestrator**     | `orchestrator.py`      | Routes tasks to the appropriate sub-agent           |

---

## 7. Service Layer

### 7.1 AgentRouter (`services/agent_router.py`)

The `AgentRouter` performs **rule-based intent classification** before falling through to the LLM. This provides sub-millisecond routing for known commands.

**Routing Priority Order:**

1. Screenshot / Camera Capture
2. Global Tab Controls (open/close tab)
3. File Sharing / Attachment
4. WhatsApp Automation (message, call, contact)
5. Gmail / Email
6. Browser Navigation (open URL, search web)
7. System Controls (volume, brightness, power)
8. Application Launch/Close
9. File System Operations
10. System Information (CPU, RAM, GPU, battery)
11. Alarm / Timer / Reminder
12. WhatsApp Background Monitor toggle
13. Lock Screen Security
14. Media Controls (play, pause, next, volume)
15. Calculator / Math
16. Weather Queries
17. Time / Date
18. General LLM fallthrough

**Normalization Pipeline:**
```
Input -> strip whitespace -> lowercase -> unicode normalize ->
remove punctuation -> collapse spaces -> route matching
```

---

### 7.2 CommandExecutor (`services/command_executor.py`)

The primary execution engine (~2,300 lines). Handles:

- **System shortcuts** (keyboard hotkeys via pyautogui)
- **Application launching** (Windows Registry + path aliases)
- **Compound command parsing** (e.g., "open Chrome and search for X")
- **Memory recall** integration (checks stored facts before LLM call)
- **Autonomous agent task routing** via `AgentEngine`
- **Multi-threaded LLM reasoning** pipeline with streaming
- **Disambiguation & Confirmation** pending state machine

#### Pending State Machine

```
User asks ambiguous command
    |
    v
PENDING_DISAMBIGUATION[session_id] = {
    options: [...],
    context: {...}
}
    |
    v
Ask user to clarify
    |
    v
User responds -> resolve -> execute
```

---

### 7.3 ContextService (`services/context_service.py`)

Detects the **foreground Windows application** in real-time using Win32 APIs and executes context-aware commands.

**Supported Application Contexts:**

| Application       | Capabilities                                                    |
|-------------------|-----------------------------------------------------------------|
| **WhatsApp**      | Open chat, send message, read unread, reply                     |
| **Gmail**         | Compose, open label, search, reply                              |
| **Chrome / Edge** | Open URL, search, new tab, scroll, focus address bar           |
| **File Explorer** | Navigate, select file, copy/paste path                         |
| **Notepad**       | Type text, open file, save                                      |
| **VS Code**       | Open file, terminal commands, open workspace                    |

**Win32 API Usage:**

```python
user32.GetForegroundWindow()            # Current focused window HWND
user32.GetWindowTextW()                 # Window title
user32.GetClassNameW()                  # Window class name
kernel32.QueryFullProcessImageNameW()   # Process EXE path
user32.SetForegroundWindow()            # Force-focus a window
```

---

### 7.4 VoiceService (`services/voice_service.py`)

Coordinates the full voice conversation loop:

| Constant                  | Value    | Purpose                           |
|---------------------------|----------|-----------------------------------|
| `WAKE_DURATION`           | 2.0 s    | Wake-word listen window           |
| `INTERRUPT_DURATION`      | 1.8 s    | Barge-in detection window         |
| `NORMAL_DURATION`         | 2.0 s    | Default command listen window     |
| `COMMAND_MAX_DURATION`    | 30.0 s   | Max voice command duration        |
| `COMMAND_SILENCE_DURATION`| 1.5 s    | End-of-speech silence threshold   |
| `COMMAND_START_TIMEOUT`   | 5.0 s    | Timeout before re-sleeping        |
| `MAX_MEMORY_MESSAGES`     | 40       | Conversation history cap          |

**System Prompt (Voice Mode):**
> *"You are Friday, an intelligent, versatile desktop AI assistant. By default, keep spoken answers concise and direct. However, if the user explicitly asks for a specific length, format, list, or detailed explanation, follow their requested length and format exactly."*

---

### 7.5 AlarmService (`services/alarm_service.py`)

Manages background timers and alarms with:
- Native Windows toast notifications
- Audible multi-frequency chime beeps (via `winsound`)
- WebSocket push alerts to the frontend
- Voice reminders via TTS
- UUID-based alarm IDs for tracking and cancellation

**AlarmItem Schema:**

```python
class AlarmItem:
    alarm_id: str           # Unique UUID hex
    label: str              # Human-readable label
    duration_seconds: float # Original duration
    target_time: datetime   # When to fire
    is_active: bool
    cancelled: bool
    timer_thread: Thread    # Background thread reference
```

---

### 7.6 SystemService (`services/system_service.py`)

OS-level service for:
- **Application launching**: Registry lookup + UWP protocol URLs + custom aliases
- **Screen capture**: `pyautogui.screenshot()`
- **Camera capture**: Windows Camera UWP integration
- **Tab controls**: Browser automation via pyautogui hotkeys
- **Drive/folder navigation**: Explorer.exe invocation
- **Search directories**: Desktop, Downloads, Documents, Pictures, Videos, Music, C:/, D:/

**UWP Protocol Map (sample):**

| Alias         | Protocol                  |
|---------------|---------------------------|
| `whatsapp`    | `whatsapp:`               |
| `spotify`     | `spotify:`                |
| `settings`    | `ms-settings:`            |
| `camera`      | `microsoft.windows.camera:` |
| `calculator`  | `calc`                    |

---

### 7.7 WhatsApp Service (`services/whatsapp_service.py`)

Full-featured WhatsApp Desktop automation (~1,500 lines):

**Features:**
- Open contact chats by name search via UI Automation
- Send text messages, emoji, files/attachments
- Initiate voice and video calls
- Background Windows toast notification monitoring
- AI auto-reply engine (via LLM) for incoming messages
- Per-monitor DPI awareness for exact coordinate matching

**Dependencies:**
- `uiautomation` — Windows UI Automation (preferred)
- `pyautogui` — Coordinate-based fallback
- `winsdk` — Windows Notification SDK for background listening
- `psutil` — WhatsApp process detection

---

## 8. Memory System

The memory system is a **4-tier architecture** orchestrated by `FridayMemoryManager`:

```
FridayMemoryManager
  |
  +-- SessionMemory      (in-process dict, session-scoped)
  +-- ConversationMemory (SQLite + background job queue)
  +-- LongTermMemory     (SQLite, permanent facts)
  +-- VectorStore        (embeddings + cosine similarity search)
  +-- ProfileMemory      (JSON file, user identity)
```

### Memory Tier Details

| Tier                   | Storage         | TTL       | Purpose                              |
|------------------------|-----------------|-----------|--------------------------------------|
| **SessionMemory**      | In-process dict | Session   | Active conversation turn history     |
| **ConversationMemory** | SQLite + Queue  | Permanent | All conversations, async ingestion   |
| **LongTermMemory**     | SQLite          | Permanent | User facts, preferences, habits      |
| **VectorStore**        | FAISS/in-memory | Permanent | Semantic similarity search           |
| **ProfileMemory**      | JSON file       | Permanent | User identity and agent profile      |

### Memory Retrieval Flow

```python
async def fetch_memory_context(query, user_id, top_k=5, min_score=0.35):
    # 1. Embed query
    # 2. Vector similarity search (min_score threshold)
    # 3. Merge with recent long-term facts
    # 4. Format as LLM-ready context string
    return { "sources": [...], "context_string": "..." }
```

---

## 9. Speech & Voice Pipeline

### 9.1 Speech-to-Text (STT)

**Primary: SenseVoice-Small** (`speech/sensevoice_stt.py`)
- Local ONNX-based model — no cloud dependency
- Optimized for short utterances
- Supports English, Tamil, Tanglish (code-switching)
- Voice Activity Detection (VAD) integration

**Fallback: Whisper** (`speech/whisper_stt.py`)
- OpenAI Whisper model (local)
- Higher accuracy for long-form audio
- Slower than SenseVoice — used as backup

### 9.2 Text-to-Speech (TTS)

**Piper TTS** (`speech/piper_tts.py`)
- Local ONNX neural TTS engine
- No internet required
- Natural-sounding voice output
- Configured for female/male voice by `voice_gender` setting

### 9.3 Wake Word Detection (`speech/wakeword.py`)

- Continuously listens for the wake word: **"friday"**
- Triggered via `listen_wake_word()` in VoiceService
- Low-power continuous listening loop
- Barge-in support: user can interrupt Friday mid-speech

### 9.4 Voice Loop (`app/voice_loop.py`)

```
Loop:
  1. listen_wake_word()  -> wait for "friday"
  2. play_acknowledgment_chime()
  3. listen_command()    -> capture command utterance
  4. execute_command()   -> route through CommandExecutor
  5. tts_speak(response) -> speak the result
  6. -> back to step 1
```

---

## 10. Vision & Screen Intelligence

### VisionService (`services/vision_service.py`)

Captures and interprets the live desktop state:

**Capabilities:**
- Query the foreground window title (< 1ms via Win32)
- Get all open application window titles (PowerShell, cached 2s)
- Natural language summary of current desktop state
- Mouse cursor position tracking
- Screen resolution and multi-monitor configuration

**Sample Output:**
```
Active Window: "VS Code - main.py"
Open Apps: ["VS Code", "Chrome", "WhatsApp", "File Explorer"]
Desktop Summary: "You are currently in VS Code editing main.py.
Chrome, WhatsApp, and File Explorer are also open in the background."
```

### Screen Capture

- `pyautogui.screenshot()` saves to `~/Pictures/Screenshots/`
- Timestamp-based filenames
- Returned as base64 or file path depending on API caller

---

## 11. Tool Registry & Capabilities

All tools are registered in `app/core/tool_router.py` and exposed as OpenAI-compatible function calling schemas.

### System & Hardware Monitoring

| Tool                  | Description                                              |
|-----------------------|----------------------------------------------------------|
| `get_cpu_status`      | CPU utilization, frequency, per-core load               |
| `get_memory_status`   | RAM used/free GB, utilization %, clock speed            |
| `get_storage_status`  | Disk drives: used/free GB, health                       |
| `get_gpu_status`      | NVIDIA + AMD GPU load, temp, VRAM (dual GPU support)    |
| `get_network_status`  | Wi-Fi speed, upload/download rates, open ports          |
| `get_battery_status`  | Battery %, charging state, power profile                |
| `get_system_info`     | OS build, architecture, hostname, hardware specs        |
| `list_services`       | Windows background services inventory                   |
| `manage_service`      | Start/stop/restart a Windows service                    |

### Environment & Utilities

| Tool              | Description                                              |
|-------------------|----------------------------------------------------------|
| `get_weather`     | Real-time weather via Open-Meteo API (any city)         |
| `get_current_time`| Date, time, timezone calculations (default: Asia/Kolkata)|
| `calculate`       | High-precision arithmetic, formulas, conversions        |
| `web_search`      | Live web search via Tavily API                          |

### Filesystem Operations

| Tool                    | Description                                          |
|-------------------------|------------------------------------------------------|
| `search_files`          | Search by filename/wildcard across directories       |
| `search_content`        | Deep text/regex search within files                  |
| `read_text_file`        | Read and return file content                         |
| `write_text_file`       | Create or overwrite text files                       |
| `create_folder`         | Create directories                                   |
| `move_file`             | Move/rename files                                    |
| `delete_file`           | Delete files (confirmation required)                 |
| `find_duplicate_files`  | SHA-256 duplicate detection for disk cleanup         |

### Process & Application Management

| Tool                    | Description                                          |
|-------------------------|------------------------------------------------------|
| `list_processes`        | Running processes: PID, CPU%, memory                 |
| `find_process_by_port`  | Identify which app owns a network port               |
| `terminate_process`     | Kill processes (OS-protected boundaries respected)   |
| `list_installed_apps`   | Apps from Windows Registry and Start Menu            |
| `launch_app`            | Launch any app by name or path                       |
| `close_app`             | Close running applications                           |

### Desktop & Terminal Automation

| Tool                    | Description                                          |
|-------------------------|------------------------------------------------------|
| `execute_command`       | Run PowerShell / CMD commands safely                 |
| `browser_navigate`      | Playwright-based web automation                      |
| `take_screenshot`       | Full desktop screenshot capture                      |
| `get_display_info`      | Resolution, monitor layout, DPI scale                |
| `get_clipboard`         | Read clipboard content                               |
| `set_clipboard`         | Write to clipboard                                   |
| `clear_clipboard`       | Clear clipboard                                      |
| `show_notification`     | Windows Action Center toast notification             |
| `create_scheduled_task` | Windows Task Scheduler integration                   |
| `list_scheduled_tasks`  | List existing scheduled tasks                        |
| `cancel_scheduled_task` | Remove a scheduled task                              |

### Device & UI Automation

| Tool                  | Description                                            |
|-----------------------|--------------------------------------------------------|
| `analyze_screen`      | Natural language description of current screen        |
| `get_active_window`   | Active window title, process, HWND                    |
| `get_open_windows`    | All visible desktop windows                           |
| `get_ui_tree`         | Full UI Automation accessibility tree                 |
| `find_ui_element`     | Find UI elements by name/role/class                   |
| `click_ui_element`    | Click a UI element                                    |
| `click_coordinates`   | Click at (x, y) screen coordinates                   |
| `type_text`           | Type text via keyboard simulation                     |
| `press_key`           | Press keyboard key(s)                                 |
| `press_hotkey`        | Send keyboard shortcut                                |
| `select_file_on_screen`| Select file in Explorer/Desktop                      |
| `drag_and_drop`       | Drag from one point to another                        |
| `drag_file_to_app`    | Drag file to an open application                      |
| `switch_application`  | Focus a running application window                   |
| `close_application`   | Close application window                             |

### Memory Tools

| Tool               | Description                                             |
|--------------------|---------------------------------------------------------|
| `save_user_fact`   | Persist a fact or preference about the user            |
| `recall_user_facts`| Retrieve stored user facts by category or keyword      |

### Custom App Registry (`database/add_path.json`)

Users can register custom application paths with friendly aliases:

```json
{
  "paths": [
    { "route_name": "harishan resume", "path": "C:\\Users\\Harishan\\Downloads\\Resume.pdf" },
    { "route_name": "gaming mouse",    "path": "C:\\Users\\Harishan\\Desktop\\GamingMouse.exe" }
  ]
}
```

Friday automatically resolves these aliases during routing.

---

## 12. LLM Provider System

Friday supports **4 interchangeable LLM providers** through a factory pattern.

### Provider Factory (`core/llm/provider_factory.py`)

```python
class ProviderFactory:
    @staticmethod
    def create(config: ModelConfig) -> BaseLLMProvider:
        match config.provider:
            case LLMProvider.GROQ       -> GroqProvider(config)
            case LLMProvider.OLLAMA     -> OllamaProvider(config)
            case LLMProvider.OPENROUTER -> OpenRouterProvider(config)
            case LLMProvider.OPENAI     -> OpenAIProvider(config)
            case LLMProvider.LMSTUDIO   -> LMStudioProvider(config)
```

### Provider Comparison

| Provider       | Default Model                  | API Key Required | Local |
|----------------|-------------------------------|------------------|-------|
| **Groq**       | `llama-3.3-70b-versatile`     | Yes              | No    |
| **Ollama**     | `qwen3:4b`                    | No               | Yes   |
| **OpenRouter** | `deepseek/deepseek-chat`      | Yes              | No    |
| **OpenAI**     | `gpt-4.1-mini`                | Yes              | No    |
| **LM Studio**  | (any local model)             | No               | Yes   |

### ModelConfig Schema

```python
class ModelConfig:
    provider: LLMProvider    # Enum: groq | ollama | openrouter | openai
    model_name: str          # Model identifier
    api_url: str             # API endpoint URL
    api_key: str             # API authentication key
    timeout: int             # Request timeout (seconds)
    temperature: float       # Response creativity (0.0 - 1.0)
    max_tokens: int          # Max output tokens
```

### Agent vs. Chat Temperature

| Mode       | Temperature | Reasoning                                      |
|------------|-------------|------------------------------------------------|
| Agent loop | `0.2`       | Deterministic tool selection, minimal hallucination |
| Chat       | `0.7`       | Natural, varied conversational responses       |

---

## 13. REST API Reference

**Base URL:** `http://localhost:8000/api/v1`

### Chat Endpoints

| Method  | Path              | Description                              |
|---------|-------------------|------------------------------------------|
| `POST`  | `/chat`           | Send a chat message, receive AI response |
| `GET`   | `/chat/history`   | Retrieve conversation history            |
| `DELETE`| `/chat/history`   | Clear conversation history               |

### Voice Endpoints

| Method | Path               | Description                    |
|--------|--------------------|--------------------------------|
| `POST` | `/voice/listen`    | Trigger STT listening session  |
| `POST` | `/voice/speak`     | Convert text to speech         |
| `POST` | `/voice/loop/start`| Start the autonomous voice loop|
| `POST` | `/voice/loop/stop` | Stop the voice loop            |

### Agent Endpoints

| Method | Path               | Description                        |
|--------|--------------------|------------------------------------|
| `POST` | `/agent/execute`   | Execute an autonomous agent task   |
| `POST` | `/agent/confirm`   | Confirm a pending agent action     |

### Memory Endpoints

| Method  | Path                    | Description                    |
|---------|-------------------------|--------------------------------|
| `GET`   | `/memory/facts`         | List stored user facts         |
| `POST`  | `/memory/facts`         | Save a new user fact           |
| `DELETE`| `/memory/facts/{id}`    | Delete a stored fact           |
| `GET`   | `/memory/conversations` | List conversation history      |

### System Endpoints

| Method | Path                | Description                         |
|--------|---------------------|-------------------------------------|
| `GET`  | `/system/status`    | System hardware status summary      |
| `GET`  | `/system/processes` | Running processes                   |
| `POST` | `/system/execute`   | Execute a terminal command          |
| `GET`  | `/system/screenshot`| Capture and return a screenshot     |

### Tools Endpoints

| Method | Path          | Description                          |
|--------|---------------|--------------------------------------|
| `GET`  | `/tools`      | List all registered tools            |
| `POST` | `/tools/call` | Directly invoke a registered tool    |

### Task / Alarm Endpoints

| Method  | Path                  | Description                       |
|---------|-----------------------|-----------------------------------|
| `GET`   | `/tasks`              | List active alarms and tasks      |
| `POST`  | `/tasks/alarm`        | Set a new alarm/timer             |
| `DELETE`| `/tasks/alarm/{id}`   | Cancel an alarm                   |

### Monitoring WebSocket

```
WS  ws://localhost:8000/api/v1/monitoring/ws
```

Pushes real-time hardware stats at configurable intervals:

```json
{
  "cpu":     { "percent": 12.4, "freq_mhz": 3200 },
  "ram":     { "used_gb": 8.2,  "total_gb": 16.0 },
  "gpu":     { "nvidia": { "load": 5.1, "temp_c": 42 } },
  "battery": { "percent": 87, "charging": true }
}
```

### File Upload

| Method | Path      | Description                                |
|--------|-----------|--------------------------------------------|
| `POST` | `/upload` | Upload PDF, DOCX, TXT, CSV for RAG/analysis|

---

## 14. WhatsApp Automation

### Architecture

WhatsApp automation uses a **dual-engine approach**:
1. **UI Automation** (`uiautomation`): Preferred — tree-based element targeting
2. **PyAutoGUI** fallback: Coordinate-based for unsupported element types

### Operations

| Operation            | Method                                        |
|----------------------|-----------------------------------------------|
| Open chat by name    | Search contact -> click chat item            |
| Send message         | Find message box -> type -> press Enter      |
| Send file            | Open attachment dialog -> navigate to file   |
| Voice call           | Open chat -> click call button               |
| Video call           | Open chat -> click video call button         |
| Read last message    | Query chat list / window content             |

### Background Monitor (Toast Watcher)

When enabled, Friday:
1. Subscribes to Windows notification center via `winsdk`
2. Intercepts WhatsApp toast notifications in real-time
3. Extracts sender name and message content
4. Generates AI response via LLM
5. Opens the sender's chat and sends auto-reply
6. Logs all activity for audit

### DPI Awareness

Friday initializes **Per-Monitor DPI Awareness (Level 2)** on startup:
```python
ctypes.windll.shcore.SetProcessDpiAwareness(2)
```

---

## 15. Desktop Overlay HUD

**File:** `desktop_overlay.py`

The Desktop Overlay is a GPU-accelerated, transparent, frameless, always-on-top widget powered by:
- **pywebview** (Microsoft Edge WebView2 backend)
- **HTML5 Canvas** for animated neural-core visualization
- **DWM Glass** (Aero Glass transparency)
- **Win32 Layered Window** for click-through transparency

### Visual Design

| Font Family       | Usage                    |
|-------------------|--------------------------|
| **Orbitron**      | Title, status indicators |
| **Inter**         | Body text, chat          |
| **JetBrains Mono**| Data readouts, values    |

### Window Properties

| Property         | Value                                    |
|------------------|------------------------------------------|
| Title            | "Friday AI Assistant - Neural Core Overlay" |
| Always on Top    | Yes                                      |
| Transparent      | Yes (DWM Glass + WS_EX_LAYERED)          |
| Frameless        | Yes                                      |
| Click-Through    | Configurable                             |

### Transparency Implementation

```python
# Step 1: Extend DWM frame into entire client area
margins = MARGINS(-1, -1, -1, -1)
ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, margins)

# Step 2: Add WS_EX_LAYERED window style
ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_LAYERED)
```

---

## 16. Security & Permission System

### Permission Levels

Tools are classified by risk level in `PermissionManager`:

| Level          | Code | Examples                                       | Behavior                    |
|----------------|------|------------------------------------------------|-----------------------------|
| **Safe**       | 0    | `get_weather`, `get_time`, `web_search`        | Always auto-execute         |
| **Low Risk**   | 1    | `read_text_file`, `take_screenshot`            | Auto-execute                |
| **Medium Risk**| 2    | `write_text_file`, `execute_command`           | Log + execute               |
| **High Risk**  | 3    | `delete_file`, `terminate_process`             | Require user confirmation   |
| **Critical**   | 4    | `send_file_externally`, OS core manipulation   | Hard block or explicit allow|

### Lock Screen Security (`database/lock_screen_security.json`)

- PIN authentication before accessing sensitive operations
- Session-based auth token after unlock
- Lock after inactivity timeout

### JWT Authentication (API)

| Setting                       | Value             |
|-------------------------------|-------------------|
| Algorithm                     | `HS256`           |
| Token expiry                  | 60 minutes        |
| Secret key                    | `SECRET_KEY` env  |

---

## 17. Database Schema

### SQLite (`database/friday_agent.db`)

#### `user_facts`
| Column       | Type    | Description                           |
|--------------|---------|---------------------------------------|
| `id`         | INTEGER | Primary key                           |
| `fact`       | TEXT    | The stored fact/preference            |
| `category`   | TEXT    | Classification (general, habit, etc.) |
| `created_at` | TEXT    | ISO timestamp                         |

#### `conversations`
| Column       | Type    | Description                        |
|--------------|---------|------------------------------------|
| `id`         | INTEGER | Primary key                        |
| `session_id` | TEXT    | Session identifier                 |
| `role`       | TEXT    | `user` / `assistant` / `tool`      |
| `content`    | TEXT    | Message content                    |
| `timestamp`  | TEXT    | ISO timestamp                      |

#### `tool_executions` (audit log)
| Column       | Type    | Description                        |
|--------------|---------|------------------------------------|
| `id`         | INTEGER | Primary key                        |
| `tool_name`  | TEXT    | Tool identifier                    |
| `arguments`  | TEXT    | JSON-serialized arguments          |
| `result`     | TEXT    | JSON-serialized result             |
| `success`    | BOOLEAN | Execution success flag             |
| `timestamp`  | TEXT    | ISO timestamp                      |

### JSON Config Files

| File                        | Purpose                                          |
|-----------------------------|--------------------------------------------------|
| `user_profile.json`         | User name, agent name, wake word, contact info  |
| `add_path.json`             | Custom app/file path aliases                    |
| `device_settings.json`      | Hardware and device preferences                 |
| `overlay_config.json`       | Overlay HUD display settings                   |
| `lock_screen_security.json` | PIN and security configuration                 |
| `power_settings.json`       | Power profile and battery thresholds           |

---

## 18. Configuration Reference

### Environment Variables (`.env`)

```ini
# LLM Provider: groq | ollama | openrouter | openai | lmstudio
LLM_PROVIDER=groq

# Model Settings
TEMPERATURE=0.7
MAX_TOKENS=1024
TIMEOUT=60

# Groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_URL=https://api.groq.com/openai/v1

# Ollama (local)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:4b

# OpenRouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=deepseek/deepseek-chat
OPENROUTER_URL=https://openrouter.ai/api/v1

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
OPENAI_URL=https://api.openai.com/v1

# Tavily Web Search
TAVILY_API_KEY=tvly-...
TAVILY_SEARCH_DEPTH=fast
TAVILY_MAX_RESULTS=5

# Database
DATABASE_URL=sqlite:///./assistant.db

# JWT Auth
SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# App
APP_NAME=AI Assistant
APP_VERSION=2.0.0
DEBUG=true
```

### User Profile (`database/user_profile.json`)

```json
{
  "name": "Harishan",
  "agent_name": "friday",
  "wake_word": "friday",
  "age": "",
  "email": "",
  "city": "",
  "profile": {
    "name": "Harishan",
    "age": "",
    "email": "",
    "city": ""
  },
  "agent_profile": {
    "agent_name": "Friday",
    "wake_word": "friday"
  }
}
```

---

## 19. Data Flow Diagrams

### Text Chat Flow

```
User Types Message
       |
       v
  POST /api/v1/chat
       |
       v
  CommandExecutor.execute()
       |
       +-- AgentRouter.route()
       |         |
       |         +-- Keyword match -> direct tool call
       |         +-- No match -> LLM fallthrough
       |
       +-- Check PENDING_DISAMBIGUATION / PENDING_CONFIRMATION
       |
       +-- Memory recall (long-term facts + vector search)
       |
       +-- Web context if needed (Tavily)
       |
       +-- AgentEngine.execute() [if complex task]
                 |
                 +-- ReAct Loop -> tool calls -> final response
       |
       v
  Response JSON { message, tool_results, audio_url? }
```

### Voice Command Flow

```
Microphone Input
       |
       v
  SenseVoice STT.listen_utterance()
       |
       v
  Wake word detected: "friday"
       |
       v
  play_chime() + listen_command()
       |
       v
  SenseVoice STT -> text string
       |
       v
  CommandExecutor.execute(text)
       |
       v
  [Same as text chat flow]
       |
       v
  Piper TTS -> audio output spoken to user
```

### Memory Fetch Flow

```
User Query
       |
       v
  embed_query(query)
       |
       v
  VectorStore.search(embedding, top_k=5, min_score=0.35)
       |
       +-- Matched docs
       +-- Recent long-term facts from SQLite
       |
       v
  Merge + Format -> Inject into LLM system prompt
```

---

## 20. Known Limitations & Roadmap

### Current Limitations

| Area             | Limitation                                                         |
|------------------|--------------------------------------------------------------------|
| **Platform**     | Windows-only (Win32 APIs, pyautogui, uiautomation, winreg)        |
| **Voice**        | Wake-word false positives in noisy environments                   |
| **WhatsApp**     | Requires WhatsApp Desktop (not web) to be installed and open      |
| **GPU Telemetry**| Requires NVIDIA drivers with NVML; AMD via WMI fallback           |
| **RAG**          | Limited to text-based documents; no PDF image/table parsing       |
| **Streaming**    | LLM streaming partially implemented in some endpoints             |

### Planned Enhancements

| Feature                            | Priority |
|------------------------------------|----------|
| Multi-language TTS (Tamil voice)   | High     |
| Telegram / Signal automation       | Medium   |
| Outlook / Calendar deep integration| Medium   |
| Vision LLM (GPT-4V / LLaVA)       | High     |
| Plugin system for 3rd-party tools  | Medium   |
| Mobile companion app               | Low      |
| Cross-platform (macOS / Linux)     | Low      |
| Fine-tuned Friday persona model    | High     |

---

## Appendix A: Quick Start

```powershell
# 1. Start Backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py

# 2. Start Frontend
cd ..\frontend
npm install
npm run dev

# 3. Start Desktop Overlay (optional)
cd ..
python desktop_overlay.py
```

---

## Appendix B: File Quick Reference

| File | Purpose | Size |
|------|---------|------|
| `backend/app/services/command_executor.py` | Primary execution engine | ~120 KB |
| `backend/app/services/whatsapp_service.py` | WhatsApp automation | ~68 KB |
| `backend/app/services/context_service.py`  | Foreground app context | ~36 KB |
| `backend/app/core/agent.py`                | ReAct agent engine | ~14 KB |
| `backend/app/services/agent_router.py`     | Intent routing | ~18 KB |
| `backend/app/memory/memory_manager.py`     | Unified memory orchestrator | ~9 KB |
| `desktop_overlay.py`                       | HUD overlay launcher | ~22 KB |
| `database/user_profile.json`               | User identity config | ~305 B |
| `database/add_path.json`                   | Custom app aliases | ~269 B |
| `backend/.env`                             | Environment configuration | ~427 B |

---

*This specification was auto-generated from the live codebase of the Friday AI Assistant project.*  
*Last updated: September 2026*
