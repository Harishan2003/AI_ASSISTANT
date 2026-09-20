"""
Friday AI Assistant - Document & File Analysis Service
Provides direct extraction for text, PDF, images, source code, and multi-document synthesis via LLM.
"""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
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
        meta["raw_text"] = (
            f"[Image File: {file_path.name}]\n"
            f"Visual inspection note: File received and staged for multimodal processing."
        )
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
    Aggregates text streams from up to 6 uploaded documents and queries the LLM (Groq / Ollama fallback)
    to synthesize a unified answer, summary, or report in the requested language (English, Tamil, Tanglish).
    
    Args:
        file_paths (List[Path]): List of local file paths to analyze.
        prompt (str): Optional user prompt or specific question regarding the files.
        language (str): Target output language ('english', 'tamil', or 'tanglish').
        agent_name (str): The assistant's persona name (default: 'Friday').
        
    Returns:
        str: Synthesized analysis or error message if extraction fails.
    """
    combined_docs_text = []

    for idx, f_path in enumerate(file_paths[:6]):
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
            print(f"[DocumentAnalysisService Groq Error]: {ex}", flush=True)

    return f"File Analysis Result:\n{corpus[:50000]}"
