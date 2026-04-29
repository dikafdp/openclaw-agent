from __future__ import annotations

import httpx
import json
import re

from app import config
from app.routers.pre_router import classify_intent
from app.prompts.system_prompts import get_domain_context
from app.tools.executor import execute_tool_by_name


DIRECT_RETURN_TOOLS = {
    "execute_search",
    "get_weather",
    "generate_image",
    "get_clinic_info",
    "get_doctor_list",
    "get_doctor_schedule_list",
    "check_schedule",
    "book_appointment",
}


def is_image_search_request(text: str) -> bool:
    text = (text or "").lower()
    keywords = [
        "cari gambar",
        "carikan gambar",
        "cari foto",
        "carikan foto",
        "search gambar",
        "search foto",
        "image search",
        "search image",
        "gambar dari internet",
        "foto dari internet",
    ]
    return any(k in text for k in keywords)


def is_link_search_request(text: str) -> bool:
    text = (text or "").lower()
    keywords = [
        "cari link",
        "carikan link",
        "berikan link",
        "kasih link",
        "daftar link",
        "sumber link",
        "link asset",
        "link referensi",
        "website",
        "situs",
    ]
    return any(k in text for k in keywords)


def is_news_search_request(text: str) -> bool:
    text = (text or "").lower()
    keywords = [
        "berita",
        "news",
        "terkini",
        "terbaru",
        "update terbaru",
        "kabar terbaru",
        "perkembangan terbaru",
    ]
    return any(k in text for k in keywords)


def guess_search_mode(user_input: str, args: dict | None = None) -> str:
    args = args or {}
    given_mode = str(args.get("search_mode") or args.get("mode") or "").strip().lower()

    if given_mode in ["answer", "links", "news", "images"]:
        return given_mode

    text = f"{user_input} {args.get('search_query', '')}".lower()

    if is_image_search_request(text):
        return "images"

    if is_news_search_request(text):
        return "news"

    if is_link_search_request(text):
        return "links"

    return "answer"


class TrueOpenClawAgent:
    def __init__(self):
        self.last_image_url = ""

    def _final_from_tool(self, tool_res: dict, domain: str, action: str) -> dict:
        final_answer = (
            tool_res.get("final_answer")
            or tool_res.get("answer")
            or f"Tool {action} selesai dijalankan."
        )

        result = {
            "final_answer": final_answer,
            "domain": domain,
            "action": action,
            "image_url": tool_res.get("image_url", self.last_image_url or ""),
        }

        if "search_results" in tool_res:
            result["search_results"] = tool_res.get("search_results", [])

        if "title" in tool_res:
            result["title"] = tool_res.get("title", "")

        if "content" in tool_res:
            result["content"] = tool_res.get("content", "")

        return result

    async def run(self, user_input: str) -> dict:
        self.last_image_url = ""

        domain = classify_intent(user_input)
        system_prompt, active_tools = get_domain_context(domain)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        async with httpx.AsyncClient(
            timeout=config.LLM_TIMEOUT,
            follow_redirects=True
        ) as client:
            target_url = config.OLLAMA_BASE_URL

            if "webhook" not in target_url.lower():
                target_url = target_url.rstrip("/") + "/api/chat"

            for step in range(4):
                payload = {
                    "model": config.OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 160,
                    },
                }

                if active_tools:
                    payload["tools"] = active_tools

                response = await client.post(target_url, json=payload)

                if response.status_code != 200:
                    return {
                        "final_answer": f"API Error {response.status_code}: {response.text}",
                        "domain": domain,
                        "action": "error",
                        "image_url": self.last_image_url,
                    }

                res_data = response.json()
                ai_msg = res_data.get("message", res_data if "content" in res_data else {})
                messages.append(ai_msg)

                # ==============================
                # CASE 1: Model tidak memakai native tool_calls
                # ==============================
                if not ai_msg.get("tool_calls"):
                    content_text = ai_msg.get("content", "").strip()

                    # Jaring pengaman 1:
                    try:
                        json_match = re.search(r"\{.*\}", content_text, re.DOTALL)

                        if json_match:
                            parsed_content = json.loads(json_match.group(0))

                            if isinstance(parsed_content, dict) and "name" in parsed_content:
                                fn_name = parsed_content.get("name")
                                args = parsed_content.get("arguments", {}) or {}

                                if fn_name == "execute_search":
                                    args["search_mode"] = guess_search_mode(user_input, args)

                                tool_res = await self._execute(fn_name, args, user_input, messages)

                                if fn_name in DIRECT_RETURN_TOOLS:
                                    return self._final_from_tool(tool_res, domain, fn_name)

                                continue

                    except Exception:
                        pass

                    # Jaring pengaman 2:
                    leaked_tools = re.findall(r"\[(.*?)\]|\(\{(.*?)\}\)", content_text)

                    if leaked_tools:
                        for match in leaked_tools:
                            val = next((m for m in match if m), "").lower().strip()
                            fn_name = ""

                            if val in ["execute_search", "search", "web_search", "execute search"]:
                                fn_name = "execute_search"
                            elif val in ["get_weather", "weather", "cuaca"]:
                                fn_name = "get_weather"
                            elif val in ["generate_image", "image", "generate image"]:
                                fn_name = "generate_image"
                            elif val in ["get_clinic_info", "clinic", "poli"]:
                                fn_name = "get_clinic_info"

                            if fn_name:
                                if fn_name == "execute_search":
                                    fallback_args = {
                                        "search_query": user_input,
                                        "search_mode": guess_search_mode(user_input),
                                    }
                                elif fn_name == "generate_image":
                                    fallback_args = {
                                        "image_prompt": user_input,
                                    }
                                elif fn_name == "get_weather":
                                    fallback_args = {
                                        "location": user_input,
                                    }
                                else:
                                    fallback_args = {}

                                tool_res = await self._execute(
                                    fn_name,
                                    fallback_args,
                                    user_input,
                                    messages,
                                )

                                if fn_name in DIRECT_RETURN_TOOLS:
                                    return self._final_from_tool(tool_res, domain, fn_name)

                                continue

                    # Jaring pengaman 3:
                    has_tool_history = any(m.get("role") == "tool" for m in messages)

                    if not has_tool_history:
                        if domain == "image" and not self.last_image_url:
                            tool_res = await self._execute(
                                "generate_image",
                                {"image_prompt": content_text or user_input},
                                user_input,
                                messages,
                            )
                            return self._final_from_tool(tool_res, domain, "generate_image")

                        if domain == "search":
                            tool_res = await self._execute(
                                "execute_search",
                                {
                                    "search_query": user_input,
                                    "search_mode": guess_search_mode(user_input),
                                },
                                user_input,
                                messages,
                            )
                            return self._final_from_tool(tool_res, domain, "execute_search")

                        if domain == "weather":
                            tool_res = await self._execute(
                                "get_weather",
                                {"location": user_input},
                                user_input,
                                messages,
                            )
                            return self._final_from_tool(tool_res, domain, "get_weather")

                    return {
                        "final_answer": content_text,
                        "domain": domain,
                        "action": "chat",
                        "image_url": self.last_image_url,
                    }

                # ==============================
                # CASE 2: Native tool calling berhasil
                # ==============================
                last_tool_res = {}

                for tool_call in ai_msg["tool_calls"]:
                    fn_name = tool_call["function"]["name"]
                    args = tool_call["function"].get("arguments", {}) or {}

                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}

                    if fn_name == "execute_search":
                        args["search_mode"] = guess_search_mode(user_input, args)

                    last_tool_res = await self._execute(fn_name, args, user_input, messages)

                    if fn_name in DIRECT_RETURN_TOOLS:
                        return self._final_from_tool(last_tool_res, domain, fn_name)

                if last_tool_res:
                    return self._final_from_tool(last_tool_res, domain, "tool")

        return {
            "final_answer": "Proses terlalu panjang, mohon sederhanakan permintaan Anda.",
            "domain": domain,
            "action": "timeout",
            "image_url": self.last_image_url,
        }

    async def _execute(self, fn_name: str, args: dict, user_input: str, messages: list):
        tool_res = await execute_tool_by_name(fn_name, args, user_input)

        if tool_res.get("image_url"):
            self.last_image_url = tool_res.get("image_url")

        messages.append({
            "role": "tool",
            "name": fn_name,
            "content": str(tool_res.get("final_answer", f"Tool {fn_name} dijalankan.")),
        })

        return tool_res


app_agent = TrueOpenClawAgent()