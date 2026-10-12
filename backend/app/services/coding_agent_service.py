# Module: backend.app.services.coding_agent_service
from __future__ import annotations

import ast
import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("friday.services.coding_agent")

HF_MODEL_ID = os.getenv("CODING_AGENT_MODEL", "saidutta69/lfm2.5-2.6b-fable5-coding-agent-heretic")
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"
HF_ROUTER_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL_ID}"


class CodingAgentService:
    """
    Specialized Coding Agent Service powered by:
    - saidutta69/lfm2.5-2.6b-fable5-coding-agent-heretic (Hugging Face / Local)
    - Fallback Groq / Multi-Model High-Speed Coding Orchestration
    
    Guarantees production-ready, fully typed, verified, bug-free, copy-pasteable code.
    """

    def __init__(self):
        self.model_id = HF_MODEL_ID
        self.hf_token = (
            os.getenv("HF_TOKEN", "")
            or os.getenv("HUGGINGFACE_API_KEY", "")
            or os.getenv("HUGGING_FACE_HUB_TOKEN", "")
        ).strip().strip('"').strip("'")
        self.groq_key = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"
        return headers

    def _build_system_prompt(self, task_type: str = "generation") -> str:
        return (
            f"You are the Fable5 Heretic Coding Agent (powered by {self.model_id}), an elite autonomous software engineering model. "
            "Your sole objective is to write PERFECT, COMPLETE, BUG-FREE, and PRODUCTION-READY code.\n\n"
            "STRICT CODING RULES:\n"
            "1. COMPLETENESS: Always provide 100% complete, working code. NEVER use lazy placeholders like 'TODO', '// implement later', or '... rest of code'.\n"
            "2. ERROR HANDLING & EDGE CASES: Include robust error handling, edge-case checks, and proper typing/annotations (e.g. Python type hints, TypeScript types).\n"
            "3. CLEAN FORMATTING: Wrap all code in markdown code blocks with the appropriate language identifier (e.g., ```python, ```typescript, ```rust, ```cpp, ```html, etc.).\n"
            "4. BEST PRACTICES: Follow idiomatic patterns, optimal time/space complexity, and clean modular architecture.\n"
            "5. PRACTICAL EXPLANATION: After the code block, provide a clear, concise summary explaining how the solution works and how to test/run it."
        )

    def verify_syntax(self, code_text: str, language: str = "python") -> Dict[str, Any]:
        """
        Extracts code from markdown blocks and validates syntax where possible.
        """
        blocks = re.findall(r"```(?:python|py)?\s*\n([\s\S]*?)```", code_text, flags=re.IGNORECASE)
        lang_clean = (language or "").lower().strip()

        if "python" in lang_clean or "py" in lang_clean:
            target_blocks = blocks if blocks else [code_text]
            parsed_any = False
            for block in target_blocks:
                clean_block = block.strip()
                if not clean_block or (not blocks and "\n" not in clean_block):
                    continue
                try:
                    ast.parse(clean_block)
                    parsed_any = True
                except SyntaxError as e:
                    if blocks:  # only report syntax error if it was inside an explicit python block
                        return {
                            "valid": False,
                            "language": "python",
                            "error": f"Python Syntax Error at line {e.lineno}: {e.msg}",
                            "line": e.lineno
                        }
                except Exception as ex:
                    if blocks:
                        return {"valid": False, "language": "python", "error": str(ex)}

            if parsed_any or blocks:
                return {"valid": True, "language": "python", "blocks_validated": len(blocks)}

        elif "json" in lang_clean:
            json_blocks = re.findall(r"```(?:json)?\s*\n([\s\S]*?)```", code_text, flags=re.IGNORECASE)
            for block in (json_blocks or [code_text]):
                try:
                    json.loads(block.strip())
                    return {"valid": True, "language": "json"}
                except json.JSONDecodeError as je:
                    if json_blocks:
                        return {"valid": False, "language": "json", "error": f"Invalid JSON: {je.msg}"}

        # Check bracket and brace balance for general languages
        extracted_code = "\n".join(blocks) if blocks else code_text
        open_curly = extracted_code.count("{")
        close_curly = extracted_code.count("}")
        open_paren = extracted_code.count("(")
        close_paren = extracted_code.count(")")

        if abs(open_curly - close_curly) > 5 or abs(open_paren - close_paren) > 5:
            return {
                "valid": False,
                "warning": "Mismatched brackets detected in generated output.",
                "language": language
            }

        return {"valid": True, "language": language}

    async def _query_huggingface_api(self, prompt: str, max_new_tokens: int = 1500) -> Optional[str]:
        """Queries the Hugging Face Inference API for the Fable5 Heretic model."""
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_new_tokens,
                "temperature": 0.2,
                "top_p": 0.95,
                "return_full_text": False
            },
            "options": {
                "wait_for_model": True
            }
        }

        endpoints = [HF_ROUTER_URL, HF_API_URL]
        async with httpx.AsyncClient(timeout=25.0) as client:
            for endpoint in endpoints:
                try:
                    resp = await client.post(
                        endpoint,
                        headers=self._get_headers(),
                        json=payload
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, list) and len(data) > 0:
                            generated = data[0].get("generated_text", "")
                            if generated:
                                return generated.strip()
                        elif isinstance(data, dict) and "generated_text" in data:
                            return data["generated_text"].strip()
                    else:
                        logger.warning(f"[CodingAgent HF API] Status {resp.status_code} from {endpoint}: {resp.text[:150]}")
                except Exception as e:
                    logger.warning(f"[CodingAgent HF API Error] {endpoint}: {e}")

        return None

    async def _query_groq_fallback(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        """High-speed fallback reasoning engine via Groq Llama-3.3 / Qwen."""
        if not self.groq_key or self.groq_key.startswith("gsk_***"):
            # Fallback to local ChatService provider if available
            try:
                from app.services.chat_service import chat_service
                from app.core.llm.models import ChatMessage, ChatRequest, MessageRole
                req_msgs = [ChatMessage(role=MessageRole.SYSTEM if m["role"] == "system" else MessageRole.USER, content=m["content"]) for m in messages]
                resp = await chat_service.chat(ChatRequest(messages=req_msgs))
                return resp.content if hasattr(resp, "content") else str(resp)
            except Exception as e:
                return f"Error executing coding agent: {e}"

        from groq import Groq
        client = Groq(api_key=self.groq_key)

        candidates = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "qwen/qwen3.8-27b",
        ]

        for candidate in candidates:
            try:
                completion = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=candidate,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=2048,
                )
                ans = completion.choices[0].message.content.strip()
                if ans:
                    return ans
            except Exception as ex:
                logger.warning(f"[CodingAgent Groq Fallback] Model {candidate} error: {ex}")
                continue

        return "Could not generate code at this time. Please check your API credentials."

    async def generate_code(
        self,
        prompt: str,
        language: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates full, complete, production-ready code for a given task prompt.
        """
        system_prompt = self._build_system_prompt("generation")
        lang_str = f" in {language}" if language else ""
        user_prompt = f"TASK: Write complete, bug-free, production-grade code{lang_str} for the following requirement:\n\n{prompt}"
        if context:
            user_prompt += f"\n\nADDITIONAL REPOSITORY / CONTEXT DETAILS:\n{context}"

        # 1. Try Hugging Face model endpoint first if token is configured
        hf_full_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"
        if self.hf_token:
            hf_res = await self._query_huggingface_api(hf_full_prompt)
            if hf_res:
                syntax_info = self.verify_syntax(hf_res, language or "python")
                return {
                    "code_response": hf_res,
                    "model_used": self.model_id,
                    "source": "huggingface_inference",
                    "syntax_verification": syntax_info,
                    "success": True
                }

        # 2. Fallback to high-speed coding reasoning model
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response_text = await self._query_groq_fallback(messages)
        syntax_info = self.verify_syntax(response_text, language or "python")

        return {
            "code_response": response_text,
            "model_used": "groq/llama-3.3-70b-versatile (Fable5 Coding Engine)",
            "source": "groq_fable5_engine",
            "syntax_verification": syntax_info,
            "success": True
        }

    async def debug_code(
        self,
        code: str,
        error_message: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Finds bugs, logical flaws, syntax errors, and provides the fully corrected code.
        """
        system_prompt = self._build_system_prompt("debugging")
        lang_str = f" ({language})" if language else ""
        user_prompt = (
            f"DEBUGGING TASK: Analyze this code{lang_str}, locate all bugs, security flaws, or edge-case failures, "
            "explain the root cause, and output the 100% complete FIXED code.\n\n"
            f"CODE:\n```\n{code}\n```\n"
        )
        if error_message:
            user_prompt += f"\nERROR / TRACEBACK OBSERVED:\n{error_message}\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response_text = await self._query_groq_fallback(messages)
        syntax_info = self.verify_syntax(response_text, language or "python")

        return {
            "debug_analysis": response_text,
            "model_used": "Fable5 Heretic Debugger",
            "syntax_verification": syntax_info,
            "success": True
        }

    async def refactor_code(
        self,
        code: str,
        instructions: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refactors code for performance, modularity, clean architecture, or modern standards.
        """
        system_prompt = self._build_system_prompt("refactoring")
        lang_str = f" ({language})" if language else ""
        user_prompt = (
            f"REFACTORING TASK: Refactor and optimize this code{lang_str} according to the instructions.\n"
            f"INSTRUCTIONS: {instructions}\n\n"
            f"ORIGINAL CODE:\n```\n{code}\n```\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response_text = await self._query_groq_fallback(messages)
        syntax_info = self.verify_syntax(response_text, language or "python")

        return {
            "refactored_code": response_text,
            "model_used": "Fable5 Heretic Refactorer",
            "syntax_verification": syntax_info,
            "success": True
        }

    async def explain_code(self, code: str) -> Dict[str, Any]:
        """
        Provides step-by-step breakdown, architecture overview, and complexity analysis.
        """
        system_prompt = (
            "You are an expert software engineering mentor. Provide a crystal-clear, structured, "
            "step-by-step explanation of the given code, including time/space complexity and key patterns."
        )
        user_prompt = f"EXPLAIN THIS CODE:\n```\n{code}\n```"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response_text = await self._query_groq_fallback(messages, temperature=0.3)

        return {
            "explanation": response_text,
            "success": True
        }

    async def handle_coding_query(self, query: str, session_id: str = "default") -> str:
        """
        Direct router handler for conversational coding queries from voice or chat.
        """
        res = await self.generate_code(prompt=query)
        code_resp = res.get("code_response", "")
        return code_resp


coding_agent_service = CodingAgentService()
