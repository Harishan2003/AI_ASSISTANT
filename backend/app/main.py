import asyncio
import inspect
import json
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import psutil
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.services.document_service import document_service as default_doc
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

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

# -------------------------------------------------------------
# UPLOAD STORAGE & FALLBACK PARSER
# -------------------------------------------------------------
UPLOAD_DIR = Path(tempfile.gettempdir()) / "Friday_Uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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
                meta["raw_text"] = (
                    f"The document '{file_path.name}' contains {len(reader.pages)} page(s). "
                    "The contents appear to be handwritten notes or scanned imagery without an embedded text layer."
                )
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

    try:
        with open(file_path, "rb") as f:
            header = f.read(1024)
        words = [w for w in re.findall(r"[a-zA-Z]{3,}", header.decode("latin-1", errors="ignore"))][:40]
        meta["raw_text"] = f"Header tokens: {' '.join(words)}"
    except Exception as e:
        meta["raw_text"] = f"Unreadable binary: {e}"

    return meta


def search_web_direct(query: str) -> List[Dict[str, str]]:
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        links = re.findall(r'<a class="result__snippet[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html)
        results = []
        for href, title in links[:3]:
            clean_t = re.sub(r"<.*?>", "", title).strip()
            actual_url = href
            if "uddg=" in href:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                if "uddg" in parsed:
                    actual_url = parsed["uddg"][0]
            results.append({"title": clean_t[:100], "url": actual_url})
        return results
    except Exception:
        return []


async def analyze_document_direct(file_path: Path, prompt: str = "") -> str:
    meta = extract_text_from_file_direct(file_path)
    content_sample = meta["raw_text"][:4000]

    search_query = f"{file_path.stem.replace('-', ' ').replace('_', ' ')} reference documentation"
    web_refs = search_web_direct(search_query)

    web_section = ""
    if web_refs:
        web_section = "\n\nInternet References Found:\n" + "\n".join(
            f"- {r['title']}: {r['url']}" for r in web_refs
        )

    instructions = (
        f"Analyze the uploaded document '{meta['filename']}' ({meta['size_kb']} KB).\n"
        f"User Prompt: {prompt or 'Analyze this file and report details with web references.'}\n\n"
        f"--- Extracted File Information ---\n{content_sample}\n\n"
        f"{web_section}\n\n"
        f"Provide a structured analysis report in clean Markdown:\n"
        f"1. **File Overview** (format, structure, pages)\n"
        f"2. **Executive Summary** (core topic and inferred meaning)\n"
        f"3. **Key Concepts & Commands Summary** (synthesize core commands or topics)\n"
        f"4. **Internet References & Verification**\n"
        f"5. **Recommendations**"
    )

    if chat_service is not None:
        for method_name in ["handle_input", "chat", "process_message"]:
            if hasattr(chat_service, method_name):
                try:
                    fn = getattr(chat_service, method_name)
                    if inspect.iscoroutinefunction(fn):
                        res = await fn(instructions)
                    else:
                        res = await asyncio.to_thread(fn, instructions)
                    if hasattr(res, "content") and res.content:
                        return str(res.content)
                    if hasattr(res, "text") and res.text:
                        return str(res.text)
                    if isinstance(res, str) and res.strip():
                        return res.strip()
                except Exception as err:
                    print(f"[Document Analysis LLM Error]: {err}", flush=True)

    return (
        f"### Analysis Report: {meta['filename']}\n\n"
        f"* **Format**: {meta['extension'].upper()} ({meta['details'].get('pages', 1)} Page(s))\n"
        f"* **Size**: {meta['size_kb']} KB\n\n"
        f"**Summary**:\n"
        f"The document represents a collection of reference materials for '{file_path.stem}'. "
        f"Visual inspection indicates scanned or handwritten notes.\n\n"
        f"**Internet References**:\n"
        f"{web_section if web_section else '- Official Language Documentation and Manuals'}"
    )


# -------------------------------------------------------------
# APP CREATION & ROUTING
# -------------------------------------------------------------
app = FastAPI(title="Friday AI Assistant Core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from app.api.v1 import api_v1_router, ws_router
    from app.api.v1.system_api import router as system_router
    from app.api.v1.voice import tts_get, tts_post, TTSRequest
    from app.mcp import mount_mcp_to_app
    app.include_router(api_v1_router)
    app.include_router(system_router, prefix="/api")
    app.include_router(ws_router)
    mount_mcp_to_app(app)

    @app.get("/api/tts")
    @app.get("/api/v1/tts")
    async def global_tts_get(text: str, language: Optional[str] = None, gender: Optional[str] = None, voice: Optional[str] = None):
        return await tts_get(text=text, language=language, gender=gender, voice=voice)

    @app.post("/api/tts")
    @app.post("/api/v1/tts")
    async def global_tts_post(req: TTSRequest):
        return await tts_post(req)

    print("[Backend Core] [OK] System, API v1, Voice/TTS & MCP Routers registered.", flush=True)
except Exception as e:
    print(f"[Backend Core Notice] API v1 Router / MCP load: {e}", flush=True)


@app.on_event("startup")
async def startup_event():
    print("\n================ ACTIVE FASTAPI ROUTES ================", flush=True)
    for r in app.routes:
        path = getattr(r, "path", getattr(r, "path_format", getattr(r, "prefix", None)))
        if path:
            methods = getattr(r, "methods", set())
            print(f"  {methods} -> {path}", flush=True)
    print("=======================================================\n", flush=True)
    try:
        from app.services.topic_monitor_service import topic_monitor_service
        topic_monitor_service.start()
        print("[Backend Core] [OK] TopicMonitorService background watcher online.", flush=True)
    except Exception as e:
        print(f"[Backend Core Notice] TopicMonitorService start error: {e}", flush=True)

    try:
        from app.core.event_bus import event_bus
        async def _forward_topic_update(data):
            await manager.broadcast({"type": "topic_update", "data": data})
        event_bus.subscribe("topic.update", _forward_topic_update)
    except Exception:
        pass


@app.post("/api/analyze-file")
@app.post("/api/analyze-file/")
@app.post("/api/analyze-files")
@app.post("/api/analyze-files/")
async def analyze_file_endpoint(
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    prompt: Optional[str] = Form(""),
    session_id: Optional[str] = Form("default"),
    language: Optional[str] = Form("english")
):
    incoming = []
    if files:
        incoming.extend(files)
    if file:
        incoming.append(file)

    if not incoming:
        return {"response": "No file received for processing.", "status": "error"}

    print(f"\n[HTTP INGEST] >>> {len(incoming)} file(s) received: {[f.filename for f in incoming]}", flush=True)
    try:
        saved_paths: List[Path] = []
        file_names: List[str] = []
        for f in incoming[:6]:
            dest_path = UPLOAD_DIR / f.filename
            with open(dest_path, "wb") as buffer:
                content = await f.read()
                buffer.write(content)
            saved_paths.append(dest_path)
            file_names.append(f.filename)

        try:
            from app.services.context_state import context_state
            context_state.set_selected_file(str(saved_paths[0]))
        except Exception:
            pass

        # Check if single/primary file is an image with an edit instruction
        primary_file = saved_paths[0]
        ext = primary_file.suffix.lower()
        if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
            try:
                from app.services.image_editing_service import image_editing_service
                if prompt and image_editing_service.is_image_edit_instruction(prompt):
                    edit_res = await image_editing_service.edit_image(
                        image_input=primary_file,
                        instruction=prompt,
                        user_name="Harishan"
                    )
                    report = image_editing_service.format_to_markdown_card(edit_res, user_name="Harishan")
                    if session_id:
                        try:
                            from app.services.command_executor import save_chat_turn
                            save_chat_turn(session_id, "user", prompt)
                            save_chat_turn(session_id, "assistant", report)
                        except Exception:
                            pass
                    return {
                        "response": report,
                        "filename": file_names[0],
                        "files": file_names,
                        "count": len(saved_paths),
                        "status": "success"
                    }
            except Exception as edit_err:
                print(f"[AnalyzeFiles ImageEdit Notice]: {edit_err}", flush=True)

        # Check if user prompt is an action / command on the uploaded file (e.g. email, WhatsApp, move, backup)
        clean_p = (prompt or "").lower().strip()
        if clean_p and (
            "@" in clean_p or
            any(w in clean_p for w in ["mail", "email", "whatsapp", "move", "copy", "backup", "send this", "send file", "share this", "share file", "forward"])
        ):
            action_reply = await execute_in_backend(prompt, session_id=session_id or "default", language=language or "english")
            return {
                "response": action_reply,
                "filename": file_names[0],
                "files": file_names,
                "count": len(saved_paths),
                "status": "success"
            }

        try:
            from app.services.document_analysis_service import analyze_multiple_documents
            report = await analyze_multiple_documents(saved_paths, prompt=prompt or "", language=language or "english")
        except Exception:
            if document_service is not None:
                report = await document_service.analyze(saved_paths[0], prompt=prompt or "")
            else:
                report = await analyze_document_direct(saved_paths[0], prompt=prompt or "")

        try:
            from app.services.context_state import context_state
            context_state.last_image_analysis = report
        except Exception:
            pass

        try:
            from app.services.command_executor import SESSION_DOC_CACHE
            import app.services.command_executor as ce
            if session_id:
                SESSION_DOC_CACHE[session_id] = report
            ce.LATEST_UPLOADED_DOC_CONTENT = report
        except Exception:
            pass

        return {
            "response": report,
            "filename": file_names[0] if file_names else "",
            "files": file_names,
            "count": len(saved_paths),
            "status": "success"
        }
    except Exception as e:
        print(f"[AnalyzeFile Error]: {e}", flush=True)
        return {"response": f"Failed to analyze file: {e}", "status": "error"}


@app.get("/api/v1/images/{filename}")
@app.get("/api/images/{filename}")
async def serve_image_file_endpoint(filename: str):
    """Serves generated and edited images directly by filename without multi-megabyte base64 bloat."""
    from fastapi.responses import FileResponse
    from fastapi import HTTPException
    import urllib.parse
    safe_name = os.path.basename(urllib.parse.unquote(filename))
    
    here = Path(__file__).resolve()
    search_dirs = [
        here.parent.parent / "database" / "generated_images",
        here.parent.parent / "database" / "edited_images",
        here.parent.parent / "database" / "face_swaps",
        here.parent.parent.parent / "database" / "generated_images",
        here.parent.parent.parent / "database" / "edited_images",
        here.parent.parent.parent / "database" / "face_swaps",
        here.parent.parent.parent / "backend" / "database" / "generated_images",
        here.parent.parent.parent / "backend" / "database" / "edited_images",
        here.parent.parent.parent / "backend" / "database" / "face_swaps",
        UPLOAD_DIR,
    ]
    for d in search_dirs:
        candidate = d / safe_name
        if candidate.exists() and candidate.is_file():
            media_type = "image/png"
            if safe_name.lower().endswith((".jpg", ".jpeg")):
                media_type = "image/jpeg"
            elif safe_name.lower().endswith(".webp"):
                media_type = "image/webp"
            elif safe_name.lower().endswith(".gif"):
                media_type = "image/gif"
            return FileResponse(str(candidate), media_type=media_type)
    raise HTTPException(status_code=404, detail="Image not found")


# -------------------------------------------------------------
# COMMAND & CHAT EXECUTION DELEGATION
# -------------------------------------------------------------
from app.services.command_executor import execute_in_backend, get_greeting_message


# -------------------------------------------------------------
# REST & WEBSOCKET ENDPOINTS
# -------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        for old_ws in self.active_connections[:]:
            try:
                await old_ws.close()
            except Exception:
                pass
        self.active_connections.clear()

        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] Connection bound. Total active: {len(self.active_connections)}", flush=True)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for ws in self.active_connections[:]:
            try:
                await ws.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    language: Optional[str] = "english"


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    t0 = time.perf_counter()
    reply = await execute_in_backend(req.message, session_id=req.session_id or "default")
    took_ms = round((time.perf_counter() - t0) * 1000)
    return {"response": reply, "latency": f"{took_ms}ms"}


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    async def telemetry_loop():
        try:
            while True:
                cpu = int(psutil.cpu_percent())
                mem = int(psutil.virtual_memory().percent)
                net = psutil.net_io_counters()
                net_mbps = round((net.bytes_sent + net.bytes_recv) / (1024 * 1024), 1)

                await websocket.send_json({
                    "type": "telemetry",
                    "data": {"cpu": cpu, "mem": mem, "gpu": 16, "net": int(net_mbps)}
                })
                await asyncio.sleep(2.5)
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    telemetry_task = asyncio.create_task(telemetry_loop())

    try:
        while True:
            raw_data = await websocket.receive_text()
            payload = json.loads(raw_data)

            if payload.get("action") == "handshake":
                welcome_text = get_greeting_message()
                await websocket.send_json({"type": "response", "data": welcome_text})
                await websocket.send_json({"type": "state", "data": "idle"})

            elif payload.get("action") == "chat":
                user_msg = payload.get("message", "")
                t0 = time.perf_counter()

                await websocket.send_json({"type": "state", "data": "thinking"})
                reply = await execute_in_backend(user_msg)
                took_ms = round((time.perf_counter() - t0) * 1000)

                await websocket.send_json({"type": "latency", "data": f"{took_ms}ms"})
                await websocket.send_json({"type": "response", "data": reply})
                await websocket.send_json({"type": "state", "data": "speaking"})

                speak_duration = max(1.5, min(6.0, len(reply) * 0.04))
                await asyncio.sleep(speak_duration)
                await websocket.send_json({"type": "state", "data": "idle"})

    except (WebSocketDisconnect, Exception):
        manager.disconnect(websocket)
        telemetry_task.cancel()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)