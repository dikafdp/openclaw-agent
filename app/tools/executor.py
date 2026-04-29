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


def detect_search_mode(user_input: str, args: dict) -> str:
    given_mode = str(
        args.get("search_mode")
        or args.get("mode")
        or ""
    ).strip().lower()

    if given_mode in ["answer", "links", "news", "images"]:
        return given_mode

    text = f"{user_input} {args.get('search_query', '')}".lower()

    image_keywords = [
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

    link_keywords = [
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

    news_keywords = [
        "berita",
        "news",
        "terkini",
        "terbaru",
        "update terbaru",
        "kabar terbaru",
        "perkembangan terbaru",
    ]

    if any(k in text for k in image_keywords):
        return "images"

    if any(k in text for k in news_keywords):
        return "news"

    if any(k in text for k in link_keywords):
        return "links"

    return "answer"


async def execute_tool_by_name(name: str, args: dict, user_input: str) -> dict:
    try:
        args = args or {}
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
                "booking_date": args.get("booking_date", ""),
            })

        elif name == "book_appointment":
            res = book_appointment({
                "doctor_name": args.get("doctor_name", ""),
                "poli_name": args.get("poli_name", ""),
                "patient_name": args.get("patient_name", ""),
                "booking_date": args.get("booking_date", ""),
                "booking_time": args.get("booking_time", ""),
                "metode_pembayaran": args.get("metode_pembayaran", "Umum"),
            })

        elif name == "get_weather":
            res = execute_weather({
                "location": args.get("location", "")
            })

        elif name == "execute_search":
            search_query = (
                args.get("search_query")
                or args.get("query")
                or user_input
            )

            search_mode = detect_search_mode(user_input, args)

            res = execute_search({
                "user_input": user_input,
                "search_query": search_query,
                "search_mode": search_mode,
            })

        elif name == "generate_image":
            res = generate_image({
                "image_prompt": args.get("image_prompt", "") or user_input
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