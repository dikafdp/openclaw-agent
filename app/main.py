from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app import config
from app.openclaw_agent import app_agent
from app.storage.jobs import job_store

app = FastAPI(title=config.APP_NAME, version="2.0.0-openclaw-runtime")


class ChatMessage(BaseModel):
    role: str = "user"
    content: str = ""


class UserRequest(BaseModel):
    message: str = ""
    messages: List[ChatMessage] = Field(default_factory=list)

    def normalized_message(self) -> str:
        if self.message.strip():
            return self.message.strip()
        # Appsmith sometimes sends full chatHistory. Use the latest user message.
        for msg in reversed(self.messages):
            if msg.role == "user" and msg.content.strip():
                return msg.content.strip()
        return ""


async def process_job(job_id: str, message: str) -> None:
    try:
        job_store.set(job_id, {"status": "processing", "pesan": "Aira sedang memproses..."})
        result = await app_agent.run(message)
        job_store.set(
            job_id,
            {
                "status": "completed",
                "data": result,
                "answer": result.get("final_answer", ""),
                "image_url": result.get("image_url", ""),
                "domain": result.get("domain", "chat"),
                "action": result.get("action", "chat"),
            },
        )
    except Exception as e:
        job_store.set(job_id, {"status": "error", "error_message": str(e)})


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "service": config.APP_NAME, "model": config.OLLAMA_MODEL, "llm_provider": config.LLM_PROVIDER}


@app.post("/agent")
async def run_agent(req: UserRequest) -> Dict[str, str]:
    message = req.normalized_message()
    if not message:
        return {"status": "error", "error_message": "Pesan kosong."}

    job_id = str(uuid.uuid4())
    job_store.set(job_id, {"status": "processing", "pesan": "Permintaan diterima, Aira sedang memproses..."})
    asyncio.create_task(process_job(job_id, message))
    return {"status": "processing", "job_id": job_id, "pesan": "Permintaan diterima, Aira sedang memproses..."}


@app.post("/agent/sync")
async def run_agent_sync(req: UserRequest) -> Dict[str, Any]:
    """Optional debug endpoint. Appsmith/n8n should use /agent + /cek-jawaban to avoid timeout."""
    message = req.normalized_message()
    if not message:
        return {"status": "error", "error_message": "Pesan kosong."}
    result = await app_agent.run(message)
    return {"status": "completed", "data": result, "answer": result.get("final_answer", ""), "image_url": result.get("image_url", "")}


@app.get("/cek-jawaban/{job_id}")
async def cek_jawaban(job_id: str) -> Dict[str, Any]:
    data = job_store.get(job_id)
    if not data:
        return {"status": "not_found", "pesan": "Job ID tidak ditemukan di memori server."}
    return data


@app.post("/maintenance/cleanup-jobs")
async def cleanup_jobs() -> Dict[str, Any]:
    deleted = job_store.cleanup()
    return {"status": "ok", "deleted": deleted}
