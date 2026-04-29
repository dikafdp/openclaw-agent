from __future__ import annotations

import base64

import httpx

from app import config
from app.state import AgentState


async def generate_image(state: AgentState) -> AgentState:
    prompt = state.get("image_prompt", "beautiful scenery") or "beautiful scenery"
    if not config.HF_TOKEN:
        return {"final_answer": "Gagal generate gambar: HF_TOKEN belum diisi di .env."}

    api_url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {config.HF_TOKEN}"}
    try:
        async with httpx.AsyncClient(timeout=config.IMAGE_TIMEOUT) as client:
            response = await client.post(api_url, headers=headers, json={"inputs": prompt})
        if response.status_code == 200:
            encoded = base64.b64encode(response.content).decode("utf-8")
            image_data_url = f"data:image/jpeg;base64,{encoded}"
            return {"final_answer": f"Gambar berhasil dibuat.\nPrompt: {prompt}", "image_url": image_data_url}
        try:
            error_msg = response.json()
        except Exception:
            error_msg = response.text
        return {"final_answer": f"Gagal generate gambar (Error {response.status_code}):\n{error_msg}"}
    except Exception as e:
        return {"final_answer": f"Gagal sistem Python saat generate gambar: {str(e)}"}
