from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from app import config


class LLMClient:
    """Small async LLM client.

    Default mode calls the existing n8n workflow that talks to office Ollama.
    Direct Ollama mode is available only as fallback/testing.
    """

    def __init__(self) -> None:
        self.provider = config.LLM_PROVIDER
        self.model = config.OLLAMA_MODEL

    async def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.0,
        system: Optional[str] = None,
    ) -> str:
        clean_messages = []
        if system:
            clean_messages.append({"role": "system", "content": system})
        for msg in messages[-8:]:
            role = msg.get("role", "user")
            content = str(msg.get("content", ""))
            if content.strip():
                clean_messages.append({"role": role, "content": content})

        if not clean_messages:
            return ""

        if self.provider == "ollama":
            return await self._chat_direct_ollama(clean_messages, temperature=temperature)
        return await self._chat_via_n8n(clean_messages, temperature=temperature)

    async def complete(self, prompt: str, *, system: Optional[str] = None, temperature: float = 0.0) -> str:
        return await self.chat(
            [{"role": "user", "content": prompt}],
            temperature=temperature,
            system=system,
        )

    async def _chat_via_n8n(self, messages: List[Dict[str, str]], *, temperature: float) -> str:
        payload = {
            "model": self.model,
            "baseUrl": config.OLLAMA_BASE_URL,
            "messages": messages,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT) as client:
            res = await client.post(config.N8N_LLM_WEBHOOK_URL, json=payload)
            res.raise_for_status()
            data: Any = res.json()

        if isinstance(data, list) and data:
            data = data[0].get("json", data[0]) if isinstance(data[0], dict) else data[0]
        if isinstance(data, dict):
            answer = data.get("answer") or data.get("response")
            if answer:
                return str(answer).strip()
            message = data.get("message")
            if isinstance(message, dict) and message.get("content"):
                return str(message["content"]).strip()
        return str(data).strip()

    async def _chat_direct_ollama(self, messages: List[Dict[str, str]], *, temperature: float) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT) as client:
            res = await client.post(f"{config.OLLAMA_BASE_URL}/api/chat", json=payload)
            res.raise_for_status()
            data = res.json()
        return str(data.get("message", {}).get("content") or data.get("response") or "").strip()


def extract_json_object(text: str) -> Dict[str, Any]:
    """Best-effort JSON extraction for small local models that sometimes add prose."""
    if not text:
        return {}
    cleaned = text.replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(cleaned[start : end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


llm_client = LLMClient()
