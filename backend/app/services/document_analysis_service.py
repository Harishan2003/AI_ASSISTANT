"""
Friday AI Assistant - Document & File Analysis Service
Provides direct extraction for text, PDF, images, source code, and multi-document synthesis via LLM.
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

from app.core.agent_config import agent_config


def sanitize_backend_output(raw_text: str) -> str:
    """
    What does this function do:
    Sanitizes raw LLM output text by stripping undesirable tool-calling formatting,
    fenced backticks, leaked JSON representations, or internal thinking blocks.
    
    Args:
        raw_text (str): Raw output generated from LLM providers.
        
    Returns:
        str: Clean, human-friendly conversational output string.
    """
    return agent_config.sanitize(raw_text)


def extract_text_from_file_direct(file_path: Path) -> Dict[str, Any]:
    """
    What does this function do:
    Directly inspects and parses the raw text content of a local file based on its extension.
    Supports .pdf (via pypdf), plain text (.txt, .md, .py, .js, .json, .csv, etc.), and images.
    
    Args:
        file_path (Path): Absolute or relative filesystem Path to the target document.
        
    Returns:
        Dict[str, Any]: Metadata dictionary containing filename, extension, size in KB,
                        and extracted 'raw_text'.
    """
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

    text_exts = {".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".json", ".csv", ".sql", ".xml", ".yaml", ".yml"}
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
        try:
            from PIL import Image
            with Image.open(str(file_path)) as img:
                w, h = img.size
                meta["details"]["dimensions"] = f"{w}x{h}"
                meta["details"]["mode"] = img.mode
                meta["raw_text"] = f"[Image File: {file_path.name} ({w}x{h} px, format: {img.format})]"
        except Exception:
            meta["raw_text"] = f"[Image File: {file_path.name} ({size_kb} KB)]"
    else:
        meta["raw_text"] = f"[Binary File: {file_path.name} ({size_kb} KB)] - No extractable text format found."

    return meta


async def analyze_multiple_documents(
    file_paths: List[Path],
    prompt: str = "",
    language: str = "english",
    agent_name: str = "Friday"
) -> str:
    """
    What does this function do:
    Aggregates text streams and images from up to 6 uploaded documents.
    Uses multimodal vision intelligence (Qwen 3.8 27B Vision / Groq) with high-fidelity facial grounding
    and advanced LLM reasoning to synthesize a unified answer, summary, or report in English, Tamil, or Tanglish.
    
    Args:
        file_paths (List[Path]): List of local file paths to analyze.
        prompt (str): Optional user prompt or specific question regarding the files.
        language (str): Target output language ('english', 'tamil', or 'tanglish').
        agent_name (str): The assistant's persona name (default: 'Friday').
        
    Returns:
        str: Synthesized analysis or error message if extraction fails.
    """
    import io
    import json
    import urllib.request
    from PIL import Image, ImageOps
    import base64

    clean_p = (prompt or "").lower().strip()
    if clean_p and (
        "@" in clean_p or
        any(w in clean_p for w in ["mail", "email", "whatsapp", "move this", "copy this", "backup this", "send this", "send file", "share this", "share file", "forward"])
    ):
        try:
            from app.services.context_state import context_state
            if file_paths:
                context_state.set_selected_file(str(file_paths[0]))
            from app.services.command_executor import execute_in_backend
            action_res = await execute_in_backend(prompt, language=language)
            if action_res:
                return action_res
        except Exception as e:
            print(f"[DocumentAnalysis Action Error]: {e}", flush=True)

    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
    non_image_docs_text = []
    image_payloads = []
    all_extracted_text = []

    for idx, f_path in enumerate(file_paths[:6]):
        meta = extract_text_from_file_direct(f_path)
        all_extracted_text.append(meta["raw_text"])

        if f_path.suffix.lower() in image_exts:
            try:
                with Image.open(str(f_path)) as img:
                    # Automatically orient image upright according to EXIF tags
                    img = ImageOps.exif_transpose(img)
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    # Scale down to optimal vision resolution (512px) to minimize Groq TPM token consumption while keeping sharp details
                    max_dim = 512
                    if img.width > max_dim or img.height > max_dim:
                        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=82, optimize=True)
                    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
                    image_payloads.append((b64_str, "image/jpeg", f_path.name))
            except Exception as img_err:
                print(f"[Image Processor Notice]: Failed to prepare {f_path.name}: {img_err}", flush=True)
        else:
            sample = meta["raw_text"][:25000]
            non_image_docs_text.append(f"### [File {idx+1}: {meta['filename']} ({meta['size_kb']} KB)]\n{sample}\n")

    lang_instruction = "Provide the response in English."
    if language == "tanglish":
        lang_instruction = "Provide the response in Tanglish (Tamil written with English letters)."
    elif language == "tamil":
        lang_instruction = "Provide the response in Tamil script."

    raw_prompt = prompt.strip() if prompt else ""
    is_generic_prompt = (
        not raw_prompt
        or bool(re.match(r"^\[uploaded \d+ file\(s\)\]$", raw_prompt, re.IGNORECASE))
        or raw_prompt.lower() in [
            "analyze this file", "analyze this image", "analyze file", "analyze",
            "inspect", "describe", "who is this", "who is this person", "what is this",
            "describe this image", "identify this", "identify person"
        ]
    )

    groq_key = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")

    # -------------------------------------------------------------------------
    # CASE 1: Multimodal Vision Analysis / Image Editing (Images Present)
    # -------------------------------------------------------------------------
    if image_payloads:
        primary_img_path = next((p for p in file_paths if p.suffix.lower() in image_exts), file_paths[0])
        try:
            from app.services.context_state import context_state
            context_state.set_selected_file(str(primary_img_path))
        except Exception:
            pass

        # Check if the user is asking to edit, modify, or transform the attached image
        from app.services.image_editing_service import image_editing_service
        if raw_prompt and image_editing_service.is_image_edit_instruction(raw_prompt):
            edit_res = await image_editing_service.edit_image(
                image_input=primary_img_path,
                instruction=raw_prompt,
                user_name="Harishan"
            )
            return image_editing_service.format_to_markdown_card(edit_res, user_name="Harishan")

        vision_system_msg = (
            f"You are {agent_name}, an expert visual intelligence and recognition AI.\n\n"
            "Instructions:\n"
            "1. Person Identification: If the subject is a public figure or celebrity, give their full name in bold and their role. If unidentified/private, state factually that they are unidentified and describe them.\n"
            "2. Scene & Details: Describe key visual elements, actions, text/labels, and context.\n"
            f"3. {lang_instruction}\n"
            "4. Output clean markdown only without internal tags."
        )

        if is_generic_prompt:
            effective_user_text = (
                "Analyze the attached image in detail. Identify any persons, objects, text, or notable features accurately."
            )
        else:
            effective_user_text = f"User Request: {raw_prompt}"

        if non_image_docs_text:
            effective_user_text += f"\n\n--- Associated Document Content ---\n" + "\n\n".join(non_image_docs_text)

        # Build multimodal user message
        user_content: List[Dict[str, Any]] = [{"type": "text", "text": effective_user_text}]
        for b64_str, mime, fname in image_payloads:
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime};base64,{b64_str}"
                }
            })

        # Try Groq Vision API
        if groq_key and not groq_key.startswith("gsk_***"):
            vision_models = []
            custom_v = os.getenv("GROQ_VISION_MODEL", "").strip().strip('"').strip("'")
            if custom_v:
                vision_models.append(custom_v)
            vision_models.append("qwen/qwen3.8-27b")

            try:
                from groq import Groq
                client = Groq(api_key=groq_key)

                for v_model in vision_models:
                    for attempt in range(2):
                        try:
                            completion = await asyncio.to_thread(
                                client.chat.completions.create,
                                model=v_model,
                                messages=[
                                    {"role": "system", "content": vision_system_msg},
                                    {"role": "user", "content": user_content}
                                ],
                                temperature=0.0,
                                max_tokens=512
                            )
                            ans = completion.choices[0].message.content.strip()
                            if ans:
                                return sanitize_backend_output(ans)
                        except Exception as v_err:
                            print(f"[Vision Model {v_model} Attempt {attempt+1} Error]: {v_err}", flush=True)
                            await asyncio.sleep(1.0)
            except Exception as ex:
                print(f"[DocumentAnalysisService Groq Vision Error]: {ex}", flush=True)

        # Fallback to local Ollama Vision if available
        try:
            b64_first = image_payloads[0][0]
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=json.dumps({
                    "model": "qwen2.5vl:3b",
                    "prompt": f"{vision_system_msg}\n\n{effective_user_text}",
                    "images": [b64_first],
                    "stream": False,
                    "options": {"temperature": 0.0}
                }).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=12.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ans = data.get("response", "").strip()
                if ans:
                    return sanitize_backend_output(ans)
        except Exception:
            pass

        # NEVER fall through to a text LLM for images; return honest vision status
        return "I was unable to visually analyze the image at this moment due to vision API rate limits. Please try again in a few moments."

    # -------------------------------------------------------------------------
    # CASE 2: Pure Text / PDF / Code Documents (No Images)
    # -------------------------------------------------------------------------
    corpus = "\n\n".join(non_image_docs_text) if non_image_docs_text else "\n\n".join(all_extracted_text)
    
    if is_generic_prompt:
        effective_doc_prompt = "Provide a comprehensive, well-structured synthesis and summary of the document(s) above, highlighting key points, structure, and findings."
    else:
        effective_doc_prompt = raw_prompt

    doc_instructions = (
        f"You are {agent_name}, an expert file and document analysis assistant analyzing {len(file_paths)} uploaded file(s).\n\n"
        f"User Prompt: {effective_doc_prompt}\n\n"
        f"--- Document Content ---\n{corpus[:40000]}\n\n"
        f"Instructions:\n"
        f"- Analyze and answer the request thoroughly based on the document content.\n"
        f"- {lang_instruction}\n"
        f"- Output ONLY the final structured analysis in clean Markdown. Do NOT output internal reasoning traces."
    )

    if groq_key and not groq_key.startswith("gsk_***"):
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            doc_models = [
                os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip().strip('"').strip("'"),
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
                "qwen/qwen3.8-27b",
                "openai/gpt-oss-20b",
            ]
            seen = set()
            for d_model in [m for m in doc_models if m and not (m in seen or seen.add(m))]:
                try:
                    completion = await asyncio.to_thread(
                        client.chat.completions.create,
                        model=d_model,
                        messages=[
                            {"role": "system", "content": f"You are {agent_name}, Harishan's intelligent Windows AI assistant with full device control, file operations, and email capabilities. Never claim you cannot send emails, access files, or control the PC."},
                            {"role": "user", "content": doc_instructions}
                        ],
                        temperature=0.1,
                        max_tokens=4096
                    )
                    ans = completion.choices[0].message.content.strip()
                    if ans:
                        return sanitize_backend_output(ans)
                except Exception as d_err:
                    print(f"[Doc Model {d_model} Notice]: {d_err}", flush=True)
                    continue
        except Exception as ex:
            print(f"[DocumentAnalysisService Groq Error]: {ex}", flush=True)

    return f"File Analysis Result:\n{corpus[:50000]}"
