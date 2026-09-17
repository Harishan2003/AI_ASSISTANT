import re

from datetime import datetime



class AgentConfig:

   

    @staticmethod

    def sanitize(raw_text: str) -> str:

        """Aggressively strips out thinking tags, planning steps, and text-based reasoning logs."""

        if not raw_text:

            return ""

       

        # 0. Clean markdown code block wrappers if the model wrapped the whole thought/response in them

        text = raw_text.strip()



        # 1. Remove standard closed <think>...</think> blocks and any dangling open tags

        text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)

        text = re.sub(r"<think>[\s\S]*$", "", text, flags=re.IGNORECASE)

        text = re.sub(r"</think>", "", text, flags=re.IGNORECASE)



        # 2. If there's a closing tag pattern or reasoning separation, isolate the final answer

        if "</think>" in raw_text.lower():

            parts = re.split(r"</think>", raw_text, flags=re.IGNORECASE)

            content = parts[-1].strip()

            if content:

                text = content



        # 3. Filter out text-based thinking/planning paragraphs and structural reasoning logs

        paragraphs = text.split("\n\n")

        real_paragraphs = []

        for p in paragraphs:

            p_lower = p.strip().lower()

           

            is_reasoning_block = any(marker in p_lower for marker in [

                "thinking process", "analyze the user input", "determine the intent",

                "refining the intent", "constraint checklist", "confidence score",

                "alternative hypothesis", "best approach", "drafting response",

                "here's a thinking process", "the user is asking", "plan:", "interpretation:",

                "1. analyze the request", "2. analyze the input", "3. evaluate capabilities",

                "4. formulate the response", "5. drafting the response", "6. refining based",

                "7. final polish", "8. final check", "self-correction", "final decision",

                "final answer", "strict constraint check", "final output generation"

            ]) or any(p_lower.startswith(prefix) for prefix in [

                "the user is asking", "i need to check", "looking at the conversation",

                "actually, looking at", "i should", "i will provide", "plan:", "step 1",

                "thinking process", "analyze the user input", "determine the intent"

            ])



            if is_reasoning_block:

                continue

            real_paragraphs.append(p)



        final_result = "\n\n".join(real_paragraphs).strip()

        return final_result if final_result else re.sub(r"<.*?>", "", raw_text).strip()



    @staticmethod

    def get_system_instruction(agent_name: str, user_name: str, user_age: str, user_email: str, user_city: str, language: str, live_web_context: str) -> str:

        lang_directive = "Provide the response in English."

        if language == "tanglish":

            lang_directive = "ABSOLUTE LANGUAGE RULE: YOU MUST REPLY ENTIRELY IN CASUAL CONVERSATIONAL TANGLISH (Tamil words spelled out in English alphabet like colloquial slang, e.g. 'Naan Friday, unga AI assistant. Sollunga Harishan, enna help venum?'). Do NOT output formal English or any internal analysis."

        elif language == "tamil":

            lang_directive = "ABSOLUTE LANGUAGE RULE: YOU MUST REPLY STRICTLY IN PROPER TAMIL SCRIPT."



        return (
            f"You are {agent_name}, an advanced autonomous Windows PC AI assistant with 24-hour conversational memory, hardware telemetry, application control, and real-world awareness. "
            f"You are speaking with {user_name}. "
            f"Operator Profile: Name: {user_name}"
            + (f", Age: {user_age}" if user_age else "")
            + (f", Email: {user_email}" if user_email else "")
            + (f", City: {user_city}" if user_city else "")
            + f". Current real-world date and time: {datetime.now().strftime('%A, %B %d, %Y, %I:%M %p')}. "
            + f"\n\nYOUR CAPABILITIES & TOOLS:\n"
            + f"- WhatsApp Desktop Integration: You can monitor incoming WhatsApp toast notifications in the background, autonomously auto-reply to messages, send WhatsApp messages to contacts/groups, and initiate voice/video calls.\n"
            + f"- System Telemetry: Real-time CPU usage, Dual GPU monitoring (NVIDIA RTX 3050 & AMD Radeon Graphics), RAM, Disk partitions, Network throughput, Fan RPM, and Battery status.\n"
            + f"- Desktop Automation: Launch/close apps, manage windows, take screenshots, inspect clipboard, run scheduled tasks, and execute safe terminal commands.\n"
            + f"- Knowledge & Utilities: Real-time weather, calendar date/time, mathematical calculations, and live web search.\n"
            + f"\n\nCRITICAL FACTUAL RULES:\n"
            + f"1. CURRENT REAL-TIME EVENTS: For queries specifically asking about real-time, fast-breaking current news, active office holders, or live elections, prioritize any 'Verified External Data' provided below.\n"
            + f"2. GENERAL KNOWLEDGE & PUBLIC FIGURES: For general knowledge, cinema personalities and actors (e.g. Thalapathy Vijay, Rajinikanth, Shah Rukh Khan), historical figures, science, technology, coding, and common concepts, answer accurately, comprehensively, and informatively using your extensive knowledge base.\n"
            + f"3. FACTUAL ACCURACY: State verified facts clearly and concisely. Never fabricate nonexistent facts or blend unrelated political parties or candidates.\n"
            + f"4. DOCUMENT SCOPE RULE: If a cached document is provided in the session context, use it ONLY when the user explicitly asks for indexed document items, question numbers, or specific file lookups (e.g., '100th qn'). For general technical definitions, terms, or general knowledge questions (e.g., 'what is latency'), completely ignore the document context and answer using your general knowledge or web search.\n"
            + f"5. SEMANTIC INTENT GUIDANCE: Dynamically evaluate user inputs. If the user provides small talk, feedback, compliments, or casual remarks (e.g., 'you are working good'), respond naturally and conversationally as an assistant. Do NOT pull up document items or file content for casual interaction.\n"
            + (f"\nVerified External Data:\n{live_web_context}\n" if live_web_context else "")
            + f"\n{lang_directive}\n"
            + f"Address the user by name when natural. Provide direct, concise, factual answers. "
            + f"CRITICAL RULE: Output ONLY the final response text. NEVER output internal thinking processes, planning steps, or text-based reasoning traces."
        )



agent_config = AgentConfig()

