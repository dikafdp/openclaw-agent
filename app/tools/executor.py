import inspect

from app.tools.medical import (
    get_clinic_info,
    check_schedule,
    get_doctor_list,
    get_doctor_schedule_list,
    book_appointment,
)
from app.tools.weather import execute_weather
from app.tools.search import execute_search
from app.tools.image import generate_image


def is_image_search_request(user_input: str, args: dict) -> bool:
    text = f"{user_input} {args.get('search_query', '')}".lower()

    image_search_keywords = [
        "cari gambar",
        "carikan gambar",
        "cari foto",
        "carikan foto",
        "search gambar",
        "search foto",
        "gambar dari internet",
        "foto dari internet",
        "image search",
        "search image",
        "lihat gambar",
        "lihat foto",
    ]

    return any(keyword in text for keyword in image_search_keywords)


async def execute_tool_by_name(name: str, args: dict, user_input: str) -> dict:
    try:
        res = None

        if name == "get_clinic_info":
            res = get_clinic_info({})

        elif name == "get_doctor_list":
            res = get_doctor_list({
                "poli_name": args.get("poli_name", "")
            })

        elif name == "get_doctor_schedule_list":
            res = get_doctor_schedule_list({
                "doctor_name": args.get("doctor_name", "")
            })

        elif name == "check_schedule":
            res = check_schedule({
                "doctor_name": args.get("doctor_name", ""),
                "poli_name": args.get("poli_name", ""),
                "booking_date": args.get("booking_date", "")
            })

        elif name == "book_appointment":
            res = book_appointment({
                "doctor_name": args.get("doctor_name", ""),
                "poli_name": args.get("poli_name", ""),
                "patient_name": args.get("patient_name", ""),
                "booking_date": args.get("booking_date", ""),
                "booking_time": args.get("booking_time", ""),
                "metode_pembayaran": args.get("metode_pembayaran", "Umum")
            })

        elif name == "get_weather":
            res = execute_weather({
                "location": args.get("location", "")
            })

        elif name == "execute_search":
            search_query = args.get("search_query", "").strip() or user_input.strip()

            search_mode = (
                args.get("search_mode")
                or args.get("mode")
                or ""
            ).strip().lower()

            if not search_mode:
                search_mode = "images" if is_image_search_request(user_input, args) else "answer"

            if search_mode not in ["answer", "links", "news", "images"]:
                search_mode = "answer"

            res = execute_search({
                "user_input": user_input,
                "search_query": search_query,
                "search_mode": search_mode
            })

        elif name == "generate_image":
            res = generate_image({
                "image_prompt": args.get("image_prompt", "")
            })

        else:
            return {
                "final_answer": f"Fungsi {name} tidak ditemukan."
            }

        if inspect.iscoroutine(res):
            res = await res

        if isinstance(res, str):
            res = {"final_answer": res}
        elif not isinstance(res, dict):
            res = {"final_answer": str(res)}

        return res

    except Exception as e:
        return {
            "final_answer": f"Error di dalam tool: {str(e)}"
        }