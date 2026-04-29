import datetime as dt
import re


def _clean_poli_name(text: str) -> str:
    text = text or ""
    text = re.sub(r"(?i)\b(poli|klinik|rsud|dokter|daftar|list|lihat|cek|di|untuk)\b", "", text)
    return text.strip()


def _clean_doctor_name(text: str) -> str:
    text = text or ""
    text = re.sub(r"(?i)\b(dr\.|drg\.|dokter|jadwal|praktek|praktik|cek|lihat)\b", "", text)
    return text.strip()


def _extract_date(user_input: str) -> str:
    text = user_input.lower()
    today = dt.date.today()

    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if match:
        return match.group(1)

    if "besok" in text:
        return (today + dt.timedelta(days=1)).strftime("%Y-%m-%d")

    if "lusa" in text:
        return (today + dt.timedelta(days=2)).strftime("%Y-%m-%d")

    days = {
        "senin": 0,
        "selasa": 1,
        "rabu": 2,
        "kamis": 3,
        "jumat": 4,
        "jum'at": 4,
        "sabtu": 5,
        "minggu": 6,
    }

    for day_name, day_idx in days.items():
        if day_name in text:
            days_ahead = day_idx - today.weekday()
            if days_ahead < 0:
                days_ahead += 7
            return (today + dt.timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    return ""


def _extract_time(user_input: str) -> str:
    match = re.search(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", user_input)
    if not match:
        return ""

    return f"{int(match.group(1)):02d}:{match.group(2)}"


def _extract_poli_name(user_input: str) -> str:
    text = user_input

    match = re.search(r"(?i)poli\s+([a-zA-ZÀ-ÿ\s]+)", text)
    if match:
        return _clean_poli_name(match.group(1))

    return ""


def _extract_doctor_name(user_input: str) -> str:
    text = user_input

    match = re.search(r"(?i)(?:dr\.?|dokter)\s+([a-zA-ZÀ-ÿ\s\.]+)", text)
    if match:
        return _clean_doctor_name(match.group(1))

    return ""


def _extract_patient_name(user_input: str) -> str:
    patterns = [
        r"(?i)atas nama\s+([a-zA-ZÀ-ÿ\s]+)",
        r"(?i)nama pasien\s+([a-zA-ZÀ-ÿ\s]+)",
        r"(?i)pasien\s+([a-zA-ZÀ-ÿ\s]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, user_input)
        if match:
            name = match.group(1)
            name = re.sub(r"(?i)\b(pakai|menggunakan|bpjs|umum|tanggal|jam|pukul)\b.*$", "", name)
            return name.strip()

    return ""


def _extract_payment(user_input: str) -> str:
    text = user_input.lower()

    if "bpjs" in text:
        return "BPJS"

    if "umum" in text:
        return "Umum"

    return "Umum"


def route_medical_intent(user_input: str) -> dict:
    text = user_input.lower().strip()

    state = {
        "user_input": user_input,
        "action": "chat",
        "doctor_name": _extract_doctor_name(user_input),
        "poli_name": _extract_poli_name(user_input),
        "booking_date": _extract_date(user_input),
        "booking_time": _extract_time(user_input),
        "patient_name": _extract_patient_name(user_input),
        "metode_pembayaran": _extract_payment(user_input),
        "poli_id": "",
        "dokter_id": "",
    }

    # 1. Daftar poli / info RSUD
    if any(k in text for k in [
        "list poli",
        "daftar poli",
        "poli apa",
        "poli tersedia",
        "layanan rsud",
        "list layanan",
        "daftar layanan",
        "info rsud",
        "berikan list poli",
    ]):
        state["action"] = "get_clinic_info"
        return state

    # 2. Booking / buat janji
    if any(k in text for k in [
        "booking",
        "buat janji",
        "daftar janji",
        "mendaftar",
        "reservasi",
        "ambil antrean",
        "ambil antrian",
    ]):
        state["action"] = "book_appointment"
        return state

    # 3. Daftar dokter di poli
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

        if not state["poli_name"]:
            # fallback sederhana: ambil kata setelah "poli"
            match = re.search(r"(?i)poli\s+(.+)", user_input)
            if match:
                state["poli_name"] = _clean_poli_name(match.group(1))

        return state

    # 4. Cek jadwal spesifik tanggal
    if any(k in text for k in ["cek jadwal", "apakah tersedia", "tersedia tanggal", "ada jadwal"]):
        if state["doctor_name"] and state["booking_date"]:
            state["action"] = "check_schedule"
        else:
            state["action"] = "get_doctor_schedule_list"

        return state

    # 5. Jadwal dokter umum
    if any(k in text for k in ["jadwal", "praktek", "praktik"]):
        state["action"] = "get_doctor_schedule_list"
        return state

    # Fallback medical paling aman:
    # Kalau sudah masuk domain medical tapi tidak jelas, jangan biarkan model mengarang.
    state["action"] = "get_clinic_info"
    return state