from __future__ import annotations

import datetime as dt
from typing import Any, Dict

import httpx

from app import config
from app.state import AgentState


def _first_json_item(data: Any) -> Any:
    if isinstance(data, list) and data:
        return data[0]
    return data


async def _request(method: str, path: str, *, json: Dict[str, Any] | None = None) -> Any:
    url = f"{config.N8N_BASE_URL}/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=config.N8N_TIMEOUT) as client:
        res = await client.request(method, url, json=json)
        # 400/409 are business responses for booking collision; keep the body.
        if res.status_code not in {200, 201, 400, 409}:
            res.raise_for_status()
        try:
            return res.status_code, res.json()
        except Exception:
            return res.status_code, res.text


async def check_schedule(state: AgentState) -> AgentState:
    payload = {
        "dokter_id": state.get("dokter_id", ""),
        "doctor_name": state.get("doctor_name", ""),
        "poli_id": state.get("poli_id", ""),
        "poli_name": state.get("poli_name", ""),
        "tanggal": state.get("booking_date", ""),
    }
    try:
        status, data = await _request("POST", "Jdokter-Refreshdb-copy", json=payload)
        if isinstance(data, dict) and data.get("error"):
            return {"final_answer": f"Mohon maaf: {data['error']}\nSilakan sebutkan nama poli, dokter, dan tanggalnya dengan jelas."}
        if status == 200 and data:
            return {"final_answer": f"Jadwal dokter tersedia:\n{data}"}
        return {"final_answer": "Mohon maaf, dokter sedang tidak tersedia atau tidak ada jadwal di hari tersebut."}
    except Exception as e:
        return {"final_answer": f"Terjadi kesalahan sistem saat cek jadwal: {str(e)}"}


async def book_appointment(state: AgentState) -> AgentState:
    doctor = str(state.get("doctor_name", "")).strip()
    dokter_id = str(state.get("dokter_id", "")).strip()
    poli = str(state.get("poli_name", "")).strip()
    poli_id = str(state.get("poli_id", "")).strip()
    patient = str(state.get("patient_name", "")).strip()
    pasien_id = str(state.get("pasien_id", "")).strip()
    date = str(state.get("booking_date", "")).strip()
    time = str(state.get("booking_time", "")).strip()
    pembayaran = str(state.get("metode_pembayaran", "Umum")).strip() or "Umum"

    missing = []

    if not (poli_id or poli):
        missing.append("Nama/ID Poli")

    if not (dokter_id or doctor):
        missing.append("Nama/ID Dokter")

    if not patient:
        missing.append("Nama Pasien")

    if not date:
        missing.append("Tanggal")

    if not time or time in ["-", "00:00", "00:00:00"]:
        missing.append("Jam Booking")

    if missing:
        return {
            "final_answer": (
                "Mohon lengkapi data booking Anda:\n"
                + "\n".join(f"- {item}" for item in missing)
                + "\n\nContoh:\n"
                "booking jadwal dr. Anthony Pratama dari poli Bedah Umum Eksekutif "
                "pada hari jumat jam 07:30 atas nama Carlos menggunakan BPJS."
            )
        }

    # Normalisasi jam agar n8n/SQL tidak menerima string aneh.
    if len(time) == 5:
        jam_mulai = f"{time}:00"
    else:
        jam_mulai = time

    try:
        base_dt = dt.datetime.strptime(jam_mulai, "%H:%M:%S")
        jam_akhir = (base_dt + dt.timedelta(minutes=30)).strftime("%H:%M:%S")
    except Exception:
        jam_akhir = ""

    payload = {
        # Kirim dua format sekaligus agar cocok dengan n8n lama maupun baru.
        "dokter_id": dokter_id,
        "doctor_name": doctor,
        "poli_id": poli_id,
        "poli_name": poli,
        "pasien_id": pasien_id,
        "patient_name": patient,
        "booking_date": date,
        "tanggal": date,
        "booking_time": time,
        "jam_mulai": jam_mulai,
        "jam_akhir": jam_akhir,
        "metode_pembayaran": pembayaran,
    }

    try:
        status, raw_data = await _request("POST", "buat-janji-copy", json=payload)

        data = _first_json_item(raw_data)
        data = data if isinstance(data, dict) else {}

        insert_id = data.get("insertId") or data.get("insert_id")
        appt_id = data.get("appointment_id") or data.get("id")
        is_success = data.get("success", data.get("ok"))
        status_code = data.get("statusCode", status)

        if status in {400, 409} or status_code in {400, 409} or is_success is False:
            return {
                "final_answer": (
                    f"Mohon maaf, jadwal dr. {doctor or dokter_id} "
                    f"di Poli {poli or poli_id} untuk tanggal {date} jam {time} "
                    "sudah terisi atau jadwal bentrok.\n\n"
                    "Silakan pilih jam lain atau cek ketersediaan dokter lain."
                )
            }

        if is_success or status_code in {200, 201} or insert_id or appt_id:
            return {
                "final_answer": (
                    "✅ Booking berhasil terdaftar.\n\n"
                    f"Detail:\n"
                    f"- Pasien: {patient}\n"
                    f"- Dokter: dr. {doctor or dokter_id}\n"
                    f"- Poli: {poli or poli_id}\n"
                    f"- Tanggal: {date}\n"
                    f"- Jam: {time}\n"
                    f"- Pembayaran: {pembayaran}\n\n"
                    "Terima kasih."
                ),
                "payload": payload,
                "raw_response": raw_data,
            }

        return {
            "final_answer": "Permintaan booking telah dikirim ke sistem, tetapi status akhir belum jelas dari n8n.",
            "payload": payload,
            "raw_response": raw_data,
        }

    except Exception as e:
        return {
            "final_answer": f"Terjadi kesalahan sistem internal saat booking: {str(e)}",
            "payload": payload,
        }

async def get_clinic_info(state: AgentState) -> AgentState:
    try:
        status, data = await _request("GET", "data-poli-api-copy")
        if status != 200:
            return {"final_answer": f"Gagal mengambil daftar poli (Error {status})."}
        if isinstance(data, list) and data:
            lines = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                name = item.get("ref_layanan_nama") or item.get("nama") or item.get("poli") or "Poli"
                poli_id = item.get("ref_layanan_id") or item.get("poli_id") or item.get("id")
                suffix = f" (ID: {poli_id})" if poli_id else ""
                lines.append(f"⚕️ {name}{suffix}")
            return {"final_answer": "Berikut daftar poli yang tersedia di RSUD kami:\n\n" + "\n".join(lines)}
        return {"final_answer": "Maaf, saat ini daftar poli tidak ditemukan."}
    except Exception as e:
        return {"final_answer": f"Terjadi kesalahan saat mengambil info RSUD: {str(e)}"}


async def get_doctor_list(state: AgentState) -> AgentState:
    poli_name = state.get("poli_name", "")
    poli_id = state.get("poli_id", "")
    if not (poli_name or poli_id):
        return {"final_answer": "Mohon sebutkan nama poli untuk melihat daftar dokternya. Contoh: lihat dokter di poli gigi."}

    payload = {"poli_name": poli_name, "poli_id": poli_id}
    try:
        status, raw_data = await _request("POST", "dokterAPI-copy", json=payload)
        if status != 200:
            return {"final_answer": f"Gagal mengambil daftar dokter (Error {status})."}
        actual_doctors = []
        if isinstance(raw_data, list) and raw_data:
            actual_doctors = raw_data[0].get("data", raw_data) if isinstance(raw_data[0], dict) else raw_data
        elif isinstance(raw_data, dict):
            actual_doctors = raw_data.get("data", [])
        if isinstance(actual_doctors, list) and actual_doctors:
            lines = []
            for item in actual_doctors:
                if not isinstance(item, dict):
                    continue
                name = item.get("nama_dokter") or item.get("doctor_name") or item.get("nama") or ""
                dokter_id = item.get("dokter_id") or item.get("id_dokter") or item.get("id")
                if name:
                    suffix = f" (ID: {dokter_id})" if dokter_id else ""
                    lines.append(f"👨‍⚕️ dr. {name}{suffix}")
            if lines:
                return {"final_answer": f"Berikut daftar dokter di Poli {poli_name or poli_id}:\n\n" + "\n".join(lines) + "\n\nSilakan sebutkan nama/ID dokter untuk melihat jadwalnya."}
        return {"final_answer": f"Maaf, saat ini tidak ditemukan dokter untuk poli {poli_name or poli_id}."}
    except Exception as e:
        return {"final_answer": f"Terjadi kesalahan saat mengambil data dokter: {str(e)}"}


async def get_doctor_schedule_list(state: AgentState) -> AgentState:
    doctor_name = state.get("doctor_name", "")
    dokter_id = state.get("dokter_id", "")
    if not (doctor_name or dokter_id):
        return {"final_answer": "Mohon sebutkan nama dokter untuk melihat jadwalnya. Contoh: cek jadwal dr. DWI KAMARATIH."}

    try:
        status, data = await _request("POST", "get-schedule-list", json={"doctor_name": doctor_name, "dokter_id": dokter_id})
        if status != 200:
            return {"final_answer": f"Gagal mengambil jadwal (Error {status})."}
        if not isinstance(data, list) or not data:
            return {"final_answer": f"Maaf, tidak ditemukan jadwal praktek untuk dr. {doctor_name or dokter_id}."}

        days_map = {"senin": 0, "selasa": 1, "rabu": 2, "kamis": 3, "jumat": 4, "jum'at": 4, "sabtu": 5, "minggu": 6}
        months = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agt", "Sep", "Okt", "Nov", "Des"]
        today = dt.date.today()
        valid_schedules = []
        for item in data:
            if not isinstance(item, dict):
                continue
            hari = str(item.get("hari_praktek", "")).strip()
            jam_mulai = str(item.get("jam_praktek_mulai", ""))
            jam_akhir = str(item.get("jam_praktek_akhir", ""))
            poli = item.get("poli") or item.get("poli_name") or ""
            if jam_mulai == "00:00:00" and jam_akhir == "00:00:00":
                continue
            jm = jam_mulai[:5] if len(jam_mulai) >= 5 else jam_mulai
            ja = jam_akhir[:5] if len(jam_akhir) >= 5 else jam_akhir
            target_day = days_map.get(hari.lower())
            hari_str = hari
            if target_day is not None:
                days_ahead = target_day - today.weekday()
                if days_ahead < 0:
                    days_ahead += 7
                date1 = today + dt.timedelta(days=days_ahead)
                date2 = date1 + dt.timedelta(days=7)
                hari_str = f"{hari} (Tgl {date1.day} {months[date1.month]} & {date2.day} {months[date2.month]})"
            valid_schedules.append(f"- {hari_str}: {jm} - {ja} (Poli: {poli})")

        if valid_schedules:
            return {"final_answer": f"Berikut jadwal praktek dr. {doctor_name or dokter_id}:\n\n" + "\n".join(valid_schedules) + "\n\nSilakan tentukan tanggal dan jam jika ingin booking."}
        return {"final_answer": f"Maaf, saat ini dr. {doctor_name or dokter_id} belum memiliki jadwal praktek aktif."}
    except Exception as e:
        return {"final_answer": f"Terjadi kesalahan saat mengambil jadwal: {str(e)}"}
