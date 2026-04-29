from __future__ import annotations
import httpx
import json
import re
from app import config
from app.routers.pre_router import classify_intent
from app.prompts.system_prompts import get_domain_context
from app.tools.executor import execute_tool_by_name

class TrueOpenClawAgent:
    def __init__(self):
        self.last_image_url = ""

    async def run(self, user_input: str) -> dict:
        self.last_image_url = ""
        
        domain = classify_intent(user_input)
        system_prompt, active_tools = get_domain_context(domain)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT, follow_redirects=True) as client:
            target_url = config.OLLAMA_BASE_URL
            if "webhook" not in target_url.lower():
                target_url = target_url.rstrip("/") + "/api/chat"
            
            for step in range(4):
                payload = {
                    "model": config.OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False
                }
                
                if active_tools:
                    payload["tools"] = active_tools
                
                response = await client.post(target_url, json=payload)
                if response.status_code != 200:
                    return {"final_answer": f"API Error {response.status_code}: {response.text}"}
                
                res_data = response.json()
                ai_msg = res_data.get("message", res_data if "content" in res_data else {})
                messages.append(ai_msg)

                # 3. Validasi Output & Jaring Pengaman (Diperkuat!)
                if not ai_msg.get("tool_calls"):
                    content_text = ai_msg.get("content", "").strip()
                    tool_executed_in_this_step = False

                    # --- JARING PENGAMAN 1: Cek JSON mentah di dalam teks ---
                    try:
                        json_match = re.search(r'\{.*\}', content_text, re.DOTALL)
                        if json_match:
                            parsed_content = json.loads(json_match.group(0))
                            if isinstance(parsed_content, dict) and "name" in parsed_content:
                                fn_name = parsed_content.get("name")
                                args = parsed_content.get("arguments", {})
                                await self._execute(fn_name, args, user_input, messages)
                                continue 
                    except Exception:
                        pass

                    # --- JARING PENGAMAN 2: Tangkap halusinasi seperti [Execute Search] ---
                    leaked_tools = re.findall(r'\[(.*?)\]|\(\{(.*?)\}\)', content_text)
                    if leaked_tools:
                        for match in leaked_tools:
                            val = next((m for m in match if m), "").lower().strip()
                            fn_name = ""
                            
                            if val in ["execute_search", "search", "web_search", "execute search"]: fn_name = "execute_search"
                            elif val in ["get_weather", "weather", "cuaca"]: fn_name = "get_weather"
                            elif val in ["generate_image", "image", "generate image"]: fn_name = "generate_image"
                            elif val in ["get_clinic_info", "clinic", "poli"]: fn_name = "get_clinic_info"
                            
                            if fn_name:
                                fallback_args = {}
                                if fn_name in ["generate_image", "execute_search"]: fallback_args = {"search_query": user_input, "image_prompt": user_input}
                                elif fn_name == "get_weather": fallback_args = {"location": user_input}
                                
                                await self._execute(fn_name, fallback_args, user_input, messages)
                                tool_executed_in_this_step = True
                                break 
                        
                        if tool_executed_in_this_step:
                            continue

                    # --- JARING PENGAMAN 3: Ultimate Fallback ala LangGraph (Zero-Shot Routing) ---
                    # Jika di riwayat percakapan belum ada satupun eksekusi tool, kita PAKSAKAN!
                    has_tool_history = any(m.get("role") == "tool" for m in messages)
                    
                    if not has_tool_history:
                        if domain == "image" and not self.last_image_url:
                            await self._execute("generate_image", {"image_prompt": content_text or user_input}, user_input, messages)
                            continue
                        elif domain == "search":
                            await self._execute("execute_search", {"search_query": user_input}, user_input, messages)
                            continue
                        elif domain == "weather":
                            await self._execute("get_weather", {"location": user_input}, user_input, messages)
                            continue

                    # Jawaban teks final dikembalikan jika semua fallback sudah terlewati
                    return {"final_answer": content_text, "domain": domain, "image_url": self.last_image_url}

                # 4. Eksekusi Native Tool Calling API (Jika modelnya pintar & support)
                for tool_call in ai_msg["tool_calls"]:
                    fn_name = tool_call["function"]["name"]
                    args = tool_call["function"]["arguments"]
                    if isinstance(args, str):
                        try: args = json.loads(args)
                        except: args = {}

                    await self._execute(fn_name, args, user_input, messages)
            
            return {"final_answer": "Proses terlalu panjang, mohon sederhanakan permintaan Anda.", "image_url": self.last_image_url}

    # Wrapper eksekusi 
    async def _execute(self, fn_name: str, args: dict, user_input: str, messages: list):
        tool_res = await execute_tool_by_name(fn_name, args, user_input)
        if tool_res.get("image_url"):
            self.last_image_url = tool_res.get("image_url")
            
        messages.append({
            "role": "tool",
            "name": fn_name,
            "content": str(tool_res.get("final_answer", f"Tool {fn_name} dijalankan."))
        })
        return tool_res

app_agent = TrueOpenClawAgent()