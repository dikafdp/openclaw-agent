import inspect
from app.tools.medical import get_clinic_info, check_schedule, get_doctor_list, get_doctor_schedule_list, book_appointment
from app.tools.weather import execute_weather
from app.tools.search import execute_search
from app.tools.image import generate_image

async def execute_tool_by_name(name: str, args: dict, user_input: str) -> dict:
    try:
        res = None
        if name == "get_clinic_info":
            res = get_clinic_info({})
        elif name == "get_doctor_list":
            res = get_doctor_list({"poli_name": args.get("poli_name", "")})
        elif name == "get_doctor_schedule_list":
            res = get_doctor_schedule_list({"doctor_name": args.get("doctor_name", "")})
        elif name == "check_schedule":
            res = check_schedule({"doctor_name": args.get("doctor_name", ""), "poli_name": args.get("poli_name", ""), "booking_date": args.get("booking_date", "")})
        elif name == "book_appointment":
            res = book_appointment({
                "doctor_name": args.get("doctor_name", ""), "poli_name": args.get("poli_name", ""), "patient_name": args.get("patient_name", ""),
                "booking_date": args.get("booking_date", ""), "booking_time": args.get("booking_time", ""), "metode_pembayaran": args.get("metode_pembayaran", "Umum")
            })
        elif name == "get_weather":
            res = execute_weather({"location": args.get("location", "")})
        elif name == "execute_search":
            res = execute_search({"user_input": user_input, "search_query": args.get("search_query", ""), "search_mode": "answer"})
        elif name == "generate_image":
            res = generate_image({"image_prompt": args.get("image_prompt", "")})
        else:
            return {"final_answer": f"Fungsi {name} tidak ditemukan."}

        if inspect.iscoroutine(res):
            res = await res
            
        # Pastikan response selalu berupa dictionary
        if isinstance(res, str):
            res = {"final_answer": res}
        elif not isinstance(res, dict):
            res = {"final_answer": str(res)}
            
        return res
    except Exception as e:
        return {"final_answer": f"Error di dalam tool: {str(e)}"}