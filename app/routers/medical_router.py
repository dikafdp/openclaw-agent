import datetime as dt
import re


DAY_MAP = {
    "senin": 0,
    "selasa": 1,
    "rabu": 2,
    "kamis": 3,
    "jumat": 4,
    "jum'at": 4,
    "sabtu": 5,
    "minggu": 6,
}


def _clean_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _next_weekday(day_idx: int) -> str:
    today = dt.date.today()
    days_ahead = day_idx - today.weekday()

    if days_ahead < 0:
        days_ahead += 7

    return (today + dt.timedelta(days=days_ahead)).strftime("%Y-%m-%d")


def _extract_date(user_input: str) -> str:
    text = user_input.lower()

    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if match:
        return match.group(1)

    today = dt.date.today()

    if "besok" in text:
        return (today + dt.timedelta(days=1)).strftime("%Y-%m-%d")

    if "lusa" in text:
        return (today + dt.timedelta(days=2)).strftime("%Y-%m-%d")

    for day_name, day_idx in DAY_MAP.items():
        if re.search(rf"\b{re.escape(day_name)}\b", text):
            return _next_weekday(day_idx)

    return ""


def _adjust_hour_by_period(hour: int, text: str) -> int:
    lower = text.lower()

    if any(k in lower for k in ["malam", "sore"]):
        if hour < 12:
            return hour + 12

    if "siang" in lower:
        if hour < 11:
            return hour + 12

    return hour


def _extract_time(user_input: str) -> str:
    text = user_input.lower()

    # Contoh: "setengah 8" = 07:30
    match = re.search(r"\bsetengah\s+(\d{1,2})\b", text)
    if match:
        hour = int(match.group(1)) - 1

        if hour < 0:
            hour = 0

        hour = _adjust_hour_by_period(hour, text)
        return f"{hour:02d}:30"

    # Contoh: "jam 07:30", "pukul 7.30"
    match = re.search(r"\b(?:jam|pukul)?\s*([01]?\d|2[0-3])[:.]([0-5]\d)\b", text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        hour = _adjust_hour_by_period(hour, text)
        return f"{hour:02d}:{minute:02d}"

    # Contoh: "jam 8", "pukul 10"
    match = re.search(r"\b(?:jam|pukul)\s+([01]?\d|2[0-3])\b", text)
    if match:
        hour = int(match.group(1))
        hour = _adjust_hour_by_period(hour, text)
        return f"{hour:02d}:00"

    return ""


def _extract_doctor_name(user_input: str) -> str:
    text = _clean_spaces(user_input)

    # Stop di: dari poli, di poli, pada, hari, tanggal, jam, atas nama, pakai, menggunakan
    match = re.search(
        r"(?i)(?:dr\.?|dokter)\s+(.+?)(?=\s+(?:dari|di)\s+poli\b|\s+poli\b|\s+pada\b|\s+hari\b|\s+tanggal\b|\s+tgl\b|\s+jam\b|\s+pukul\b|\s+atas\s+nama\b|\s+pasien\b|\s+menggunakan\b|\s+pakai\b|$)",
        text,
    )

    if not match:
        return ""

    doctor = match.group(1)
    doctor = re.sub(r"(?i)^(dr\.?|dokter|drg\.?)\s+", "", doctor)
    return _clean_spaces(doctor)


def _extract_poli_name(user_input: str) -> str:
    text = _clean_spaces(user_input)

    match = re.search(
        r"(?i)\bpoli\s+(.+?)(?=\s+pada\b|\s+hari\b|\s+tanggal\b|\s+tgl\b|\s+jam\b|\s+pukul\b|\s+atas\s+nama\b|\s+pasien\b|\s+menggunakan\b|\s+pakai\b|$)",
        text,
    )

    if not match:
        return ""

    poli = match.group(1)
    poli = re.sub(r"(?i)\b(dokter|dr\.?|drg\.?|rsud)\b", "", poli)
    return _clean_spaces(poli)


def _extract_patient_name(user_input: str) -> str:
    text = _clean_spaces(user_input)

    patterns = [
        r"(?i)atas\s+nama\s+(.+?)(?=\s+menggunakan\b|\s+pakai\b|\s+bpjs\b|\s+umum\b|$)",
        r"(?i)nama\s+pasien\s+(.+?)(?=\s+menggunakan\b|\s+pakai\b|\s+bpjs\b|\s+umum\b|$)",
        r"(?i)pasien\s+(.+?)(?=\s+menggunakan\b|\s+pakai\b|\s+bpjs\b|\s+umum\b|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _clean_spaces(match.group(1))

    return ""


def _extract_payment(user_input: str) -> str:
    text = user_input.lower()

    if "bpjs" in text:
        return "BPJS"

    if "umum" in text:
        return "Umum"

    return "Umum"


def route_medical_intent(user_input: str) -> dict:
    text = user_input.lower()

    state = {
        "user_input": user_input,
        "action": "chat",
        "doctor_name": _extract_doctor_name(user_input),
        "poli_name": _extract_poli_name(user_input),
        "patient_name": _extract_patient_name(user_input),
        "booking_date": _extract_date(user_input),
        "booking_time": _extract_time(user_input),
        "metode_pembayaran": _extract_payment(user_input),
        "poli_id": "",
        "dokter_id": "",
        "pasien_id": "",
    }

    if any(k in text for k in [
        "booking",
        "buat janji",
        "daftar janji",
        "mendaftar",
        "reservasi",
        "ambil antrian",
        "ambil antrean",
    ]):
        state["action"] = "book_appointment"
        return state

    if any(k in text for k in [
        "list poli",
        "daftar poli",
        "poli apa",
        "poli tersedia",
        "layanan rsud",
        "list layanan",
        "daftar layanan",
        "info rsud",
    ]):
        state["action"] = "get_clinic_info"
        return state

    if any(k in text for k in [
        "daftar dokter",
        "list dokter",
        "dokter di poli",
        "dokter poli",
        "siapa dokter",
        "cek dokter",
        "lihat dokter",
    ]):
        state["action"] = "get_doctor_list"
        return state

    if any(k in text for k in [
        "cek jadwal",
        "apakah tersedia",
        "tersedia tanggal",
        "ada jadwal",
    ]):
        if state["doctor_name"] and state["booking_date"]:
            state["action"] = "check_schedule"
        else:
            state["action"] = "get_doctor_schedule_list"

        return state

    if any(k in text for k in ["jadwal", "praktek", "praktik"]):
        state["action"] = "get_doctor_schedule_list"
        return state

    state["action"] = "get_clinic_info"
    return state