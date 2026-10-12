"""
Friday Document Service
Parses any file format (images, text, code, pdf, docx, xlsx, pptx, binary),
features local Ollama vision parsing for images & handwriting via Qwen-VL,
searches the web for references/cross-verification, and generates structured analysis reports.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import re
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


class DocumentService:

    UPLOAD_DIR = Path(tempfile.gettempdir()) / "Friday_Uploads"

    def __init__(self):
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def encode_image_base64(self, file_path: Path) -> str:
        """Encodes image in high fidelity without destroying facial details."""
        try:
            from PIL import Image, ImageOps

            with Image.open(file_path) as img:
                img = ImageOps.exif_transpose(img)
                if img.mode != "RGB":
                    img = img.convert("RGB")

                max_dim = 1400
                if max(img.size) > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=95, optimize=True)
                return base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"[Image Preprocessor Notice]: {e}, falling back to raw bytes.")
            with open(file_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode("utf-8")

    def classify_user_intent(self, prompt: str) -> str:
        """Determines what the user wants based on the query:
        - 'identity': Explicit query asking who the person is.
        - 'report': Explicit request for deep analysis or multi-section report.
        - 'describe': Default behavior on simple upload or generic command.
        - 'targeted': Any specific custom question.
        """
        clean = prompt.lower().strip()

        clean = re.sub(r"-\s*analyze this file", "", clean).strip()
        clean = re.sub(r"analyze this file", "", clean).strip()
        clean = re.sub(r"analyze this image", "", clean).strip()
        clean = re.sub(r"analyze this document", "", clean).strip()

        if not clean or clean in ["describe this", "what is this", "inspect", "inspect this", "read this", "analyze this", "analyze", "summarize this"]:
            return "describe"

        if any(w in clean for w in ["who is", "who's", "who", "identify person", "name of", "which actor", "celebrity", "person name"]):
            return "identity"

        if any(w in clean for w in ["deep analysis", "detailed report", "full report", "comprehensive", "full analysis", "breakdown", "study"]):
            return "report"

        return "targeted"

    async def analyze_image_with_ollama(self, file_path: Path, prompt: str = "") -> str:
        """High-precision vision engine configured for accurate visual grounding and concise outputs."""
        b64_image = self.encode_image_base64(file_path)
        intent = self.classify_user_intent(prompt)

        system_msg = (
            "You are Friday, an advanced computer vision and visual intelligence assistant.\n"
            "CRITICAL VISUAL RECOGNITION INSTRUCTIONS:\n"
            "1. Facial & Person Identification:\n"
            "   - Carefully examine distinct facial features: bone structure, eyes, nose, hairstyle/hairline, facial hair, skin tone, and expression.\n"
            "   - If the subject is a recognized public figure, celebrity, actor, cinema star, world leader, politician, scientist, athlete, or tech executive:\n"
            "     * State their EXACT FULL NAME clearly in bold.\n"
            "     * Briefly state their key profession, notable works, or historical significance.\n"
            "   - If the individual is a private person, user, non-celebrity, or NOT definitively recognized as a world-famous public figure:\n"
            "     * NEVER guess, fabricate, or hallucinate a celebrity name.\n"
            "     * State clearly that this is an unidentified individual or private person, and describe their physical appearance, attire, and expression factually.\n"
            "2. Text & OCR Transcription:\n"
            "   - Transcribe all visible text, labels, formulas, and badges with high fidelity.\n"
            "3. Output format:\n"
            "   - Provide a clear, factual, direct, and structured response addressing the user's prompt without reasoning traces."
        )

        if intent == "identity":
            user_instruction = (
                f"Question: '{prompt or 'Who is in this image?'}'\n"
                "Examine facial features carefully. State the recognized person's verified exact name directly in line 1. "
                "Provide 1-2 accurate factual sentences regarding their identity. If private/unknown, state that clearly."
            )
        elif intent == "describe":
            user_instruction = (
                "Provide a comprehensive, accurate analysis of this image.\n"
                "- If a person is present: Accurately state their exact name if they are a recognized public figure, or describe them factually if private/unidentified.\n"
                "- Clearly describe the primary subject, objects, environment, and visual composition.\n"
                "- Transcribe any visible text, labels, equations, or code.\n"
                "- State your findings clearly in clean Markdown without internal thinking blocks."
            )
        elif intent == "report":
            user_instruction = (
                f"Analyze the image in detail for the following request: '{prompt}'.\n"
                "Provide a structured analysis covering:\n"
                "1. **Overview & Key Subject**\n"
                "2. **Detailed Visual Elements & Text/Data Transcription**\n"
                "3. **Context & Key Insights**"
            )
        else:
            user_instruction = f"Inspect the image and answer the user's question directly, factually, and accurately: {prompt}"

        # 1. Primary: Groq Vision (Using supported vision model IDs)
        groq_api_key = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")
        if not groq_api_key:
            try:
                from app.core.config import settings
                groq_api_key = getattr(settings, "GROQ_API_KEY", "").strip()
            except Exception:
                pass

        if groq_api_key and not groq_api_key.startswith("gsk_***"):
            vision_models = []
            custom_v_model = os.getenv("GROQ_VISION_MODEL", "").strip().strip('"').strip("'")
            if custom_v_model:
                vision_models.append(custom_v_model)
            vision_models.extend(["qwen/qwen3.8-27b"])
            
            try:
                from groq import Groq
                client = Groq(api_key=groq_api_key)

                for v_model in vision_models:
                    try:
                        completion = await asyncio.to_thread(
                            client.chat.completions.create,
                            model=v_model,
                            messages=[
                                {"role": "system", "content": system_msg},
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": user_instruction},
                                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                                    ]
                                }
                            ],
                            temperature=0.0,
                            max_tokens=1024
                        )
                        res = completion.choices[0].message.content.strip()

                        if "</think>" in res:
                            res = res.split("</think>")[-1].strip()
                        elif "<think>" in res:
                            res = re.sub(r"<think>[\s\S]*", "", res).strip()

                        if res:
                            return res
                    except Exception as model_err:
                        print(f"[Vision Pipeline Notice]: Groq vision with {v_model} failed ({model_err})", flush=True)
                        continue
            except Exception as e:
                print(f"[Vision Pipeline Notice]: Groq client failed ({e}), falling back to local Ollama.", flush=True)

        # 2. Local Ollama Fallback
        target_model = None
        try:
            with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3.0) as resp:
                tags_data = json.loads(resp.read().decode("utf-8"))
                installed = [m.get("name", "") for m in tags_data.get("models", [])]
                for m in installed:
                    clean = m.lower()
                    if any(v in clean for v in ["vl", "vision", "llava", "moondream"]):
                        target_model = m
                        break
                if not target_model and installed:
                    target_model = installed[0]
        except Exception:
            pass

        target_model = target_model or "qwen2.5vl:3b"

        payload = {
            "model": target_model,
            "prompt": user_instruction,
            "images": [b64_image],
            "stream": False,
            "options": {"temperature": 0.05, "num_predict": 350}
        }

        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=90.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                out = data.get("response", "").strip()
                if "</think>" in out:
                    out = out.split("</think>")[-1].strip()
                elif "<think>" in out:
                    out = re.sub(r"<think>[\s\S]*", "", out).strip()
                return out or "No visual description could be generated."
        except Exception as e:
            return f"Visual inspection error: {e}. Ensure Ollama is running locally with a vision model installed (e.g. `ollama run llava`)."

    def extract_text_from_file(self, file_path: Path) -> Dict[str, Any]:
        """Extracts text, metadata, and structural details from any file format."""
        ext = file_path.suffix.lower()
        size_kb = round(file_path.stat().st_size / 1024, 2)
        meta: Dict[str, Any] = {
            "filename": file_path.name,
            "extension": ext or "none",
            "size_kb": size_kb,
            "raw_text": "",
            "is_handwritten_or_scanned": False,
            "details": {},
        }

        text_extensions = {
            ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".html",
            ".css", ".json", ".csv", ".log", ".yaml", ".yml", ".xml",
            ".sql", ".sh", ".bat", ".ini", ".env", ".c", ".cpp", ".java"
        }
        if ext in text_extensions:
            for enc in ["utf-8", "latin-1", "cp1252"]:
                try:
                    meta["raw_text"] = file_path.read_text(encoding=enc, errors="ignore")
                    break
                except Exception:
                    continue
            return meta

        if ext == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(file_path))
                text_pages: List[str] = []
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text_pages.append(f"--- Page {i + 1} ---\n{page_text.strip()}")

                meta["details"]["pages"] = len(reader.pages)
                if text_pages:
                    meta["raw_text"] = "\n\n".join(text_pages)
                else:
                    meta["is_handwritten_or_scanned"] = True
                    meta["raw_text"] = (
                        f"The document '{file_path.name}' contains {len(reader.pages)} page(s). "
                        "Because this is a handwritten or scanned image PDF without an embedded OCR/digital text layer, "
                        "the visual strokes cannot be parsed via standard text extraction."
                    )
            except Exception as e:
                meta["raw_text"] = f"Failed to extract PDF: {e}"
            return meta

        if ext == ".docx":
            try:
                import docx
                doc = docx.Document(str(file_path))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                tables_data: List[str] = []
                for t_idx, table in enumerate(doc.tables):
                    rows_str = []
                    for row in table.rows:
                        rows_str.append(" | ".join([cell.text.strip() for cell in row.cells]))
                    tables_data.append(f"Table {t_idx + 1}:\n" + "\n".join(rows_str))
                meta["raw_text"] = "\n\n".join(paragraphs + tables_data)
                meta["details"]["paragraphs_count"] = len(paragraphs)
                meta["details"]["tables_count"] = len(doc.tables)
            except Exception as e:
                meta["raw_text"] = f"Failed to extract Word text: {e}"
            return meta

        if ext in [".xlsx", ".xls"]:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(str(file_path), data_only=True)
                sheets_summary = []
                for sheet in wb.sheetnames:
                    ws = wb[sheet]
                    rows_extracted = []
                    for row in ws.iter_rows(values_only=True):
                        non_empty = [str(cell) for cell in row if cell is not None]
                        if non_empty:
                            rows_extracted.append(", ".join(non_empty))
                        if len(rows_extracted) > 60:
                            rows_extracted.append("... [Row limit reached]")
                            break
                    sheets_summary.append(f"--- Sheet: {sheet} ---\n" + "\n".join(rows_extracted))
                meta["raw_text"] = "\n\n".join(sheets_summary)
                meta["details"]["sheets"] = wb.sheetnames
            except Exception as e:
                meta["raw_text"] = f"Failed to extract Excel content: {e}"
            return meta

        if ext == ".pptx":
            try:
                from pptx import Presentation
                prs = Presentation(str(file_path))
                slides_text = []
                for idx, slide in enumerate(prs.slides):
                    slide_lines = []
                    for shape in slide.shapes:
                        if shape.has_text_frame:
                            for paragraph in shape.text_frame.paragraphs:
                                if paragraph.text.strip():
                                    slide_lines.append(paragraph.text.strip())
                    if slide_lines:
                        slides_text.append(f"--- Slide {idx + 1} ---\n" + "\n".join(slide_lines))
                meta["raw_text"] = "\n\n".join(slides_text)
                meta["details"]["slide_count"] = len(prs.slides)
            except Exception as e:
                meta["raw_text"] = f"Failed to extract PowerPoint text: {e}"
            return meta

        try:
            with open(file_path, "rb") as f:
                header = f.read(1024)
            printable = "".join(chr(b) if 32 <= b <= 126 or b in (10, 13) else " " for b in header)
            words = [w for w in printable.split() if len(w) > 3][:50]
            meta["raw_text"] = f"Binary file header strings: {' '.join(words)}"
            meta["details"]["type"] = "Binary/Archive/Executable"
        except Exception as e:
            meta["raw_text"] = f"Unreadable binary: {e}"

        return meta

    def search_internet_references(self, query: str) -> List[Dict[str, str]]:
        """Searches DuckDuckGo for external internet verification and references."""
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            snippets: List[Dict[str, str]] = []
            results = re.findall(r'<a class="result__snippet[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html)
            if not results:
                results = re.findall(r'<a class="result__url"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html)

            for href, text in results[:3]:
                clean_text = re.sub(r"<.*?>", "", text).strip()
                actual_link = href
                if "uddg=" in href:
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    if "uddg" in parsed:
                        actual_link = parsed["uddg"][0]
                snippets.append({"title": clean_text[:120], "url": actual_link})
            return snippets
        except Exception:
            return []

    async def analyze(self, file_path: Path, prompt: str = "") -> str:
        """Processes images, documents, and code dynamically based on prompt intent."""
        ext = file_path.suffix.lower()

        if ext in IMAGE_EXTENSIONS:
            report = await self.analyze_image_with_ollama(file_path, prompt=prompt)
            try:
                from app.services.context_state import context_state
                context_state.last_image_analysis = report
                context_state.set_selected_file(str(file_path))
            except Exception:
                pass
            return report

        meta = self.extract_text_from_file(file_path)
        content_sample = meta["raw_text"][:4000]
        intent = self.classify_user_intent(prompt)

        if intent in ["describe", "targeted"]:
            instructions = (
                f"The user uploaded '{meta['filename']}'. "
                f"Query: {prompt or 'Summarize this file.'}\n\n"
                f"Extracted content:\n\"\"\"\n{content_sample}\n\"\"\"\n\n"
                "Respond directly and concisely in 2 to 4 sentences without large tables or formal template headers."
            )
        else:
            search_terms = file_path.stem.replace("-", " ").replace("_", " ")
            web_refs = self.search_internet_references(f"{search_terms} tutorial reference")
            web_context = ""
            if web_refs:
                web_context = "\n\nInternet References Found:\n" + "\n".join(
                    f"- {ref['title']}: {ref['url']}" for ref in web_refs
                )

            instructions = (
                f"Analyze the uploaded document '{meta['filename']}' ({meta['size_kb']} KB).\n"
                f"Handwritten/Scanned Image Status: {meta.get('is_handwritten_or_scanned', False)}\n"
                f"User Prompt: {prompt or 'Analyze this file and report details.'}\n\n"
                f"--- Extracted File Information ---\n{content_sample}\n\n"
                f"{web_context}\n\n"
                f"Provide a structured analysis report in Markdown:\n"
                f"1. **File Overview**\n"
                f"2. **Executive Summary**\n"
                f"3. **Key Concepts & Commands Summary**\n"
                f"4. **Recommendations**"
            )

        from app.services.chat_service import ChatService
        try:
            cs = ChatService()
            for method in ["handle_input", "chat", "process_message"]:
                if hasattr(cs, method):
                    fn = getattr(cs, method)
                    import inspect
                    if inspect.iscoroutinefunction(fn):
                        res = await fn(instructions)
                    else:
                        res = fn(instructions)

                    if hasattr(res, "content") and res.content:
                        return str(res.content)
                    if hasattr(res, "text") and res.text:
                        return str(res.text)
                    if isinstance(res, str) and res.strip():
                        return res.strip()
        except Exception as e:
            print(f"[DocumentService] LLM analysis error: {e}")

        return f"File '{meta['filename']}' ({meta['size_kb']} KB) loaded. Summary: {content_sample[:250]}..."


document_service = DocumentService()