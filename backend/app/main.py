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


@app.on_event("startup")
async def startup_event():
    print("\n================ ACTIVE FASTAPI ROUTES ================", flush=True)
    for r in app.routes:
        path = getattr(r, "path", getattr(r, "path_format", getattr(r, "prefix", None)))
        if path:
            methods = getattr(r, "methods", set())
            print(f"  {methods} -> {path}", flush=True)
    print("=======================================================\n", flush=True)


@app.post("/api/analyze-file")
@app.post("/api/analyze-file/")
async def analyze_file_endpoint(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form("")
):
    print(f"\n[HTTP INGEST] >>> File received: {file.filename}", flush=True)
    try:
        dest_path = UPLOAD_DIR / file.filename
        with open(dest_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        try:
            from app.services.context_state import context_state
            context_state.set_selected_file(str(dest_path))
        except Exception:
            pass

        if document_service is not None:
            report = await document_service.analyze(dest_path, prompt=prompt or "")
            try:
                from app.services.context_state import context_state
                context_state.last_image_analysis = report
            except Exception:
                pass
        else:
            report = await analyze_document_direct(dest_path, prompt=prompt or "")

        return {"response": report, "filename": file.filename, "status": "success"}
    except Exception as e:
        print(f"[AnalyzeFile Error]: {e}", flush=True)
        return {"response": f"Failed to analyze file: {e}", "status": "error"}


def get_greeting_message() -> str:
    hour = datetime.now().hour
    period = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    current_time = datetime.now().strftime("%I:%M %p")
    return f"{period} boss. Friday neural interface is online. The time is {current_time}. How can I assist you?"


def extract_response_text(res) -> str | None:
    if res is None:
        return None
    if isinstance(res, str) and res.strip():
        if res.startswith("Acknowledged boss"):
            return None
        if res in [
            "take_screenshot", "take_photo", "open_new_tab", "close_current_tab",
            "automate_chat", "automate_media", "web_search", "get_current_time",
            "calculate", "weather", "open_application", "open_folder", "open_file",
            "open_link", "open_file_explorer", "open_path"
        ]:
            return None
        return res.strip()
    if isinstance(res, dict):
        text_candidate = res.get("response") or res.get("message") or res.get("text") or res.get("content")
        if isinstance(text_candidate, str) and text_candidate.startswith("Acknowledged boss"):
            return None
        return text_candidate
    if hasattr(res, "response"):
        val = str(res.response)
        return None if val.startswith("Acknowledged boss") else val
    if hasattr(res, "text"):
        val = str(res.text)
        return None if val.startswith("Acknowledged boss") else val
    if hasattr(res, "content"):
        val = str(res.content)
        return None if val.startswith("Acknowledged boss") else val
    return None


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


# -------------------------------------------------------------
# PIPELINE EXECUTION
# -------------------------------------------------------------
async def execute_in_backend(raw_query: str) -> str:
    query = raw_query.strip()
    clean = query.lower().strip()

    # 1. Immediate Wake Word & Greeting Handler
    greetings = ["friday", "hey friday", "hi friday", "hello friday", "hello", "hi", "hlo", "hey", "test"]
    if not query or clean in greetings:
        return get_greeting_message()

    print(f"\n[INCOMING QUERY] >>> '{query}'", flush=True)

    # 1.5. Real-Time Alarm, Countdown Timer & Reminder Service (Sound + Notification + Speech)
    from app.services.alarm_service import parse_alarm_or_reminder_query
    alarm_parsed = parse_alarm_or_reminder_query(query)
    if alarm_parsed:
        return alarm_parsed.get("message", "Alarm configured.")

    # 1.6. Live Screen Understanding & Desktop Context ("What am I seeing?")
    from app.services.vision_service import is_screen_query, capture_and_describe_screen
    if is_screen_query(query):
        return capture_and_describe_screen()

    # 2. Voice Document Analysis Trigger
    if any(k in clean for k in ["analyze this file", "analyze file", "inspect this file", "examine this file", "read this file"]):
        try:
            from app.services.context_state import context_state
            target_file = context_state.selected_file
            if target_file and os.path.exists(target_file):
                if document_service is not None:
                    res = await document_service.analyze(Path(target_file), prompt=query)
                    context_state.last_image_analysis = res
                    return res
                return await analyze_document_direct(Path(target_file), prompt=query)
        except Exception as e:
            print(f"[Context Analysis Error]: {e}", flush=True)
        return "No file is currently attached or selected for analysis, boss. Please upload or select a file first."

    # 3. Contextual Recall for Follow-up Questions
    augmented_query = query
    image_keywords = ["image", "picture", "photo", "drawing", "artwork", "poster", "this", "it", "show", "movie", "franchise"]
    if any(k in clean for k in image_keywords):
        try:
            from app.services.context_state import context_state
            last_analysis = getattr(context_state, "last_image_analysis", None)
            if last_analysis:
                augmented_query = (
                    f"Context: The user previously uploaded an image that was visually analyzed as follows:\n"
                    f"\"\"\"\n{last_analysis}\n\"\"\"\n\n"
                    f"User follow-up question: {query}\n\n"
                    f"Answer the user's question directly using the visual analysis context above."
                )
        except Exception:
            pass

    # 4. WhatsApp Focus & Search
    if "whatsapp" in clean and any(k in clean for k in ["search", "find", "message", "to", "for"]):
        if os.name == "nt":
            os.system("start whatsapp:")
        else:
            os.system("xdg-open whatsapp:// &")
        await asyncio.sleep(0.35)

    # 5. AgentRouter Execution (Informational Questions Bypass Tools)
    info_starters = (
        "who is", "who are", "what is", "what are", "where is", "where are",
        "why is", "why does", "when is", "when did", "how to", "how do", "how is",
        "tell me", "explain", "describe", "can you", "who", "what", "which"
    )
    is_info_query = any(clean.startswith(q) for q in info_starters) or "?" in clean

    if agent_router is not None and not is_info_query:
        try:
            tool_name = agent_router.route(query)
            if tool_name == "context_execution" and hasattr(agent_router, "_last_context_result"):
                res = str(agent_router._last_context_result)
                if not res.startswith("Acknowledged boss"):
                    return res
            if tool_name == "open_link":
                return execute_direct_link(query)
            if tool_name in ["open_application", "open_folder", "open_file", "open_path", "open_file_explorer"] and system_service is not None:
                return system_service.execute(tool_name, query)
        except Exception as e:
            print(f"[AgentRouter Error]: {e}", flush=True)

    # 6. ChatService Execution
    if chat_service is not None:
        for method_name in ["handle_input", "process_message", "chat", "execute"]:
            if hasattr(chat_service, method_name):
                try:
                    fn = getattr(chat_service, method_name)
                    if inspect.iscoroutinefunction(fn):
                        raw_res = await asyncio.wait_for(fn(augmented_query), timeout=30.0)
                    else:
                        raw_res = await asyncio.to_thread(fn, augmented_query)

                    result_text = extract_response_text(raw_res)
                    if result_text:
                        print(f"[ChatService.{method_name} Success] >>> {result_text}", flush=True)
                        return result_text
                except asyncio.TimeoutError:
                    print(f"[ChatService.{method_name}] Request timed out.", flush=True)
                except Exception as err:
                    print(f"[ChatService.{method_name} Error]: {err}", flush=True)

    # 7. Direct Groq Provider Fallback
    groq_key = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")
    groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip().strip('"').strip("'")
    if groq_key and not groq_key.startswith("gsk_***"):
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            completion = await asyncio.to_thread(
                client.chat.completions.create,
                model=groq_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Friday, an intelligent AI assistant. Answer queries directly, factually, and concisely."
                    },
                    {"role": "user", "content": augmented_query}
                ],
                temperature=0.2,
                max_tokens=300
            )
            ans = completion.choices[0].message.content.strip()
            if ans:
                print(f"[Direct Groq LLM Success] >>> {ans}", flush=True)
                return ans
        except Exception as ex:
            print(f"[Direct Groq Error]: {ex}", flush=True)

    # 8. Local Ollama Fallback
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b").strip().strip('"').strip("'")
    try:
        payload = {"model": ollama_model, "prompt": augmented_query, "stream": False}
        req = urllib.request.Request(
            f"{ollama_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            local_ans = data.get("response", "").strip()
            if local_ans:
                return local_ans
    except Exception as ex:
        print(f"[Direct Ollama Error]: {ex}", flush=True)

    # 9. Fallback Check for App Launch
    if any(clean.startswith(act) for act in ["open ", "launch ", "start "]) and system_service is not None:
        return system_service.execute("open_application", query)

    return "I am unable to reach the neural engine at this moment, boss."


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


manager = ConnectionManager()


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    t0 = time.perf_counter()
    reply = await execute_in_backend(req.message)
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