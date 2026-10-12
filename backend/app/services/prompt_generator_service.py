"""
Prompt Generator Service for Friday AI Assistant.
Generates master-grade, production-ready prompts for Image Models (Midjourney v6, Flux.1, SDXL, DALL-E 3),
LLM System Prompts & Agents, Coding Assistants, and Video Generation (Sora, Runway Gen-3).
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional


class PromptGeneratorService:
    """
    Intelligent multi-domain prompt generator and enhancer.
    """

    # Image enhancement artistic and technical vocabulary
    IMAGE_STYLES = {
        "cinematic": "cinematic 35mm film photography, volumetric lighting, dynamic shadows, anamorphic lens flare, Arri Alexa 8k, color graded, ultra-detailed textures",
        "photorealistic": "hyperrealistic 8k photograph, natural sunlight, 85mm f/1.4 portrait lens, depth of field, sharp focus, micro details, Hasselblad H6D-100c",
        "cyberpunk": "cyberpunk aesthetics, glowing neon reflections, holographic displays, rain-slicked futuristic streets, atmospheric fog, octane render 8k",
        "anime": "Makoto Shinkai aesthetic, vibrant anime art style, painterly sky, detailed lighting, emotional atmosphere, Studio Ghibli inspired, high resolution",
        "fantasy": "epic high fantasy illustration, ethereal glow, magical particles, ornate detailed armor, Greg Rutkowski & ArtStation trending, 8k masterpiece",
        "minimalist": "minimalist clean composition, soft studio lighting, pastel color palette, architectural clarity, elegant negative space, editorial design"
    }

    NEGATIVE_IMAGE_PROMPT = (
        "blurry, low quality, distorted anatomy, extra limbs, bad hands, missing fingers, "
        "watermark, signature, text, oversaturated, deformed, jpeg artifacts, ugly, duplicate"
    )

    def __init__(self):
        pass

    def detect_prompt_type(self, text: str) -> str:
        """Determines if the target prompt is for image, code, llm, video, or general writing."""
        t = text.lower()
        if any(k in t for k in ["midjourney", "image", "photo", "wallpaper", "portrait", "drawing", "illustration", "stable diffusion", "flux", "dall-e", "dalle", "render", "logo", "poster", "art"]):
            return "image"
        elif any(k in t for k in ["code", "coding", "python", "javascript", "typescript", "react", "fastapi", "backend", "frontend", "api", "database", "algorithm", "function", "refactor"]):
            return "code"
        elif any(k in t for k in ["video", "sora", "runway", "kling", "pika", "animation", "motion", "cinematic shot"]):
            return "video"
        elif any(k in t for k in ["system prompt", "agent", "llm", "roleplay", "persona", "ai assistant", "chatgpt", "claude", "instruction"]):
            return "llm"
        else:
            return "general"

    def _generate_image_prompt_fallback(self, topic: str, style: str = "cinematic") -> Dict[str, Any]:
        """Local high-quality template synthesis for image generation."""
        clean_topic = re.sub(r'^(?:generate|create|write|make|give me)\s+(?:the\s+|an?\s+)?(?:image\s+prompt|midjourney\s+prompt|prompt)?\s*(?:for|about)?\s*', '', topic, flags=re.IGNORECASE).strip()
        if not clean_topic:
            clean_topic = "futuristic AI assistant core floating in holographic space"

        # Specialized handling for background removal / cutout / isolation requests
        if any(k in clean_topic.lower() for k in ["remove bg", "background removal", "remove background", "transparent", "white background", "isolate subject", "cutout"]):
            master_prompt = (
                f"Isolate the subject from {clean_topic} with razor-sharp edge definition, ultra-clean cutout against a pure solid white studio backdrop or transparent alpha channel, "
                "preserving ultra-fine hair strands and edge details, clean studio lighting, zero background bleeding, commercial product photography quality."
            )
            return {
                "category": "image",
                "topic": clean_topic,
                "master_prompt": master_prompt,
                "negative_prompt": "complex background, noisy textures, halos, jagged edges, background artifacts, color spill, blurred contours",
                "engine": "local_synthesizer"
            }

        style_details = self.IMAGE_STYLES.get(style.lower(), self.IMAGE_STYLES["cinematic"])
        master_prompt = f"A breathtaking masterwork of {clean_topic}, {style_details}, intricate details, masterpiece composition, Unreal Engine 5 render, ray tracing, 8k resolution --ar 16:9 --v 6.0 --style raw"

        return {
            "category": "image",
            "topic": clean_topic,
            "master_prompt": master_prompt,
            "negative_prompt": self.NEGATIVE_IMAGE_PROMPT,
            "aspect_ratio": "16:9 (or 9:16 for vertical/mobile)",
            "recommended_models": ["Midjourney v6", "FLUX.1-dev", "Stable Diffusion XL (SDXL)", "DALL-E 3"],
            "engine": "local_synthesizer"
        }

    def _generate_llm_prompt_fallback(self, topic: str) -> Dict[str, Any]:
        """Local high-quality template synthesis for LLM system prompts."""
        clean_topic = re.sub(r'^(?:generate|create|write|make)\s+(?:an?\s+)?(?:system\s+prompt|llm\s+prompt|agent\s+prompt|prompt)?\s*(?:for|about)?\s*', '', topic, flags=re.IGNORECASE).strip()
        if not clean_topic:
            clean_topic = "Senior AI Software Architect and Coding Mentor"

        master_prompt = (
            f"### Role & Identity\n"
            f"You are an expert specialist in {clean_topic}. Your mission is to provide authoritative, rigorous, and highly actionable solutions with exceptional clarity.\n\n"
            f"### Core Objectives & Instructions\n"
            f"1. **Deep Analytical Depth:** Analyze incoming requirements thoroughly before formulating answers.\n"
            f"2. **Precision & Best Practices:** Adhere strictly to industry standards, modular architecture, and modern best practices.\n"
            f"3. **Step-by-Step Reasoning:** When tackling complex tasks, explain the rationale behind key decisions clearly.\n"
            f"4. **No Fluff:** Deliver direct, high-signal, clean responses formatted with clear Markdown headers and code blocks.\n\n"
            f"### Constraints\n"
            f"- Never provide untested or incomplete code snippets.\n"
            f"- Always highlight potential edge cases, security implications, and performance optimizations."
        )

        return {
            "category": "llm",
            "topic": clean_topic,
            "master_prompt": master_prompt,
            "recommended_models": ["Claude 3.5 Sonnet", "GPT-4o", "Qwen 2.5 72B", "Llama 3.3 70B"],
            "variations": [
                f"Concise / Fast Agent Prompt: Direct {clean_topic} specialist with strict 3-bullet answer structure.",
                f"Interactive Mentor Prompt: Socratic guide in {clean_topic} that asks clarifying questions before writing code."
            ],
            "engine": "local_synthesizer"
        }

    def _generate_code_prompt_fallback(self, topic: str) -> Dict[str, Any]:
        """Local synthesis for code generation prompts."""
        clean_topic = re.sub(r'^(?:generate|create|write|make)\s+(?:an?\s+)?(?:coding\s+prompt|code\s+prompt|prompt)?\s*(?:for|about)?\s*', '', topic, flags=re.IGNORECASE).strip()
        master_prompt = (
            f"Develop a clean, production-ready, fully typed solution for: {clean_topic}.\n\n"
            f"Requirements:\n"
            f"1. Implement modular, self-contained architecture with robust error handling.\n"
            f"2. Include complete type annotations and docstrings explaining inputs and outputs.\n"
            f"3. Optimize for low memory footprint, zero redundant loops, and fast async execution.\n"
            f"4. Provide a runnable unit test or verification example demonstrating success."
        )
        return {
            "category": "code",
            "topic": clean_topic,
            "master_prompt": master_prompt,
            "recommended_models": ["Qwen 2.5 Coder 32B", "Claude 3.5 Sonnet", "DeepSeek-V3 / R1"],
            "variations": [
                f"Async / High Performance: {clean_topic} with asyncio, non-blocking I/O, and connection pooling.",
                f"Test-Driven Development (TDD): Full pytest test suite for {clean_topic} with edge cases and mock fixtures."
            ],
            "engine": "local_synthesizer"
        }

    def _generate_video_prompt_fallback(self, topic: str) -> Dict[str, Any]:
        """Local synthesis for AI video generation prompts."""
        clean_topic = re.sub(r'^(?:generate|create|write|make)\s+(?:an?\s+)?(?:video\s+prompt|prompt)?\s*(?:for|about)?\s*', '', topic, flags=re.IGNORECASE).strip()
        master_prompt = (
            f"Cinematic slow tracking shot of {clean_topic}. Smooth camera motion pushing forward, "
            f"atmospheric lighting with golden hour dust motes floating in the air, photorealistic 8k video, "
            f"natural physics, subtle motion blur, 60fps cinematic grading."
        )
        return {
            "category": "video",
            "topic": clean_topic,
            "master_prompt": master_prompt,
            "negative_prompt": "choppy framerate, morphing artifacts, distorted limbs, flicker, static image, sudden cuts",
            "recommended_models": ["OpenAI Sora", "Runway Gen-3 Alpha", "Kling AI", "Luma Dream Machine"],
            "variations": [
                f"Drone FPV Sweep: High-speed cinematic drone dive over {clean_topic}, dynamic lighting.",
                f"Slow Motion 120fps: Hyper-detailed 120fps slow-motion capture of {clean_topic}."
            ],
            "engine": "local_synthesizer"
        }

    async def generate(self, user_query: str, target_type: Optional[str] = None, style: str = "cinematic") -> Dict[str, Any]:
        """
        Generates master prompts with LLM reasoning when online, falling back to instant local synthesis.
        """
        category = target_type or self.detect_prompt_type(user_query)

        # 1. Attempt online LLM generation with Groq if available
        groq_key = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")
        if groq_key and not groq_key.startswith("gsk_***"):
            for model_cand in ["llama-3.1-8b-instant", "llama3-70b-8192", "llama3-8b-8192", "gemma2-9b-it", "mixtral-8x7b-32768"]:
                try:
                    from groq import Groq
                    client = Groq(api_key=groq_key, timeout=8.0)

                    system_prompt = (
                        "You are a world-class AI Prompt Engineering Master like ChatGPT and Gemini. "
                        "Your mission is to generate 1 (or at most 2) crystal-clear, production-grade, ready-to-use prompts for the user's exact request.\n\n"
                        "CRITICAL OUTPUT RULES:\n"
                        "1. OUTPUT ONLY THE PROMPT(S). Do NOT provide long background explanations, tool tutorials, programming scripts, or advice unless explicitly asked for code.\n"
                        "2. ALWAYS enclose the Master Prompt inside a markdown fenced code block labeled ```prompt ... ``` so the user can 1-click copy it.\n"
                        "3. If a Negative Prompt is relevant (e.g. for image generation, subject cutout, or background cleanup), enclose it in ```negative_prompt ... ```.\n"
                        "4. If the request is for image generation or editing (like background removal, subject cutout, photorealism), craft the exact high-fidelity prompt with lighting, subject clarity, and isolation parameters.\n"
                        "5. Keep the response concise, punchy, and modern with a brief 1-sentence introduction."
                    )

                    resp = client.chat.completions.create(
                        model=model_cand,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Generate the optimal prompt for: {user_query}"}
                        ],
                        temperature=0.7,
                        max_tokens=600
                    )

                    content = resp.choices[0].message.content.strip()
                    if content:
                        return {
                            "category": category,
                            "topic": user_query,
                            "master_prompt": content,
                            "engine": "groq_neural_engineer"
                        }
                except Exception as e:
                    continue

        # 2. Local Instant Synthesis
        if category == "image":
            return self._generate_image_prompt_fallback(user_query, style=style)
        elif category == "code":
            return self._generate_code_prompt_fallback(user_query)
        elif category == "video":
            return self._generate_video_prompt_fallback(user_query)
        else:
            return self._generate_llm_prompt_fallback(user_query)

    def format_to_natural_speech(self, res: Dict[str, Any], user_name: str = "Harishan") -> str:
        """Formats prompt generator output into a concise, beautiful ChatGPT/Gemini-style response."""
        topic = res.get("topic", "your request")
        master = res.get("master_prompt", "").strip()
        neg = res.get("negative_prompt", "").strip() if res.get("negative_prompt") else ""

        out = []
        if res.get("engine") == "groq_neural_engineer":
            if "```" in master:
                out.append(master)
            else:
                out.append(f"Here is your prompt for **{topic}**, {user_name}:\n\n```prompt\n{master}\n```")
        else:
            out.append(f"Here is your prompt for **{topic}**, {user_name}:\n\n```prompt\n{master}\n```")
            if neg:
                out.append(f"\n### 🚫 Negative Prompt:\n```negative_prompt\n{neg}\n```")

        return "\n".join(out)


prompt_generator_service = PromptGeneratorService()
