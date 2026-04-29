from __future__ import annotations

import httpx

from app.state import AgentState


async def execute_weather(state: AgentState) -> AgentState:
    lokasi = state.get("location", "Jakarta") or "Jakarta"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(f"https://wttr.in/{lokasi}", params={"format": 4})
        if res.status_code == 200:
            return {"final_answer": f"☁️ Cuaca:\n{res.text}"}
        return {"final_answer": f"Gagal ambil cuaca untuk {lokasi} (Error {res.status_code})."}
    except Exception as e:
        return {"final_answer": f"Error cuaca: {str(e)}"}
