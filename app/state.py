from __future__ import annotations
from typing import Any, Dict, List, Literal, TypedDict

Domain = Literal["chat", "medical", "weather", "search", "image"]
Action = Literal[
    "chat", "check_schedule", "book_appointment", "get_clinic_info", 
    "get_doctor_list", "get_doctor_schedule_list", "get_weather", 
    "web_search", "generate_image"
]

class AgentState(TypedDict, total=False):
    user_input: str
    domain: Domain
    action: Action
    title: str
    content: str
    location: str
    search_query: str
    search_mode: str
    search_results: List[Dict[str, Any]]
    image_prompt: str
    image_url: str
    doctor_name: str
    dokter_id: str
    poli_name: str
    poli_id: str
    booking_date: str
    booking_time: str
    patient_name: str
    metode_pembayaran: str
    final_answer: str
    error_message: str