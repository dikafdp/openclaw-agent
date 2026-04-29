MASTER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_clinic_info",
            "description": "Melihat daftar poli atau layanan yang tersedia di RSUD.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_doctor_list",
            "description": "Melihat daftar dokter di poli tertentu.",
            "parameters": {
                "type": "object",
                "properties": {"poli_name": {"type": "string", "description": "Nama poli. Contoh: Anak, Gigi"}},
                "required": ["poli_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_doctor_schedule_list",
            "description": "Melihat jadwal praktek dokter tertentu.",
            "parameters": {
                "type": "object",
                "properties": {"doctor_name": {"type": "string", "description": "Nama dokter"}},
                "required": ["doctor_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_schedule",
            "description": "Cek apakah jadwal dokter tersedia di tanggal tertentu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string", "description": "Nama dokter"},
                    "poli_name": {"type": "string", "description": "Nama poli"},
                    "booking_date": {"type": "string", "description": "Tanggal format YYYY-MM-DD"}
                },
                "required": ["doctor_name", "poli_name", "booking_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Booking atau mendaftar janji medis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string", "description": "Nama dokter"},
                    "poli_name": {"type": "string", "description": "Nama poli"},
                    "patient_name": {"type": "string", "description": "Nama pasien"},
                    "booking_date": {"type": "string", "description": "Tanggal format YYYY-MM-DD"},
                    "booking_time": {"type": "string", "description": "Jam HH:MM (opsional)"},
                    "metode_pembayaran": {"type": "string", "description": "BPJS atau Umum"}
                },
                "required": ["doctor_name", "poli_name", "patient_name", "booking_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Mengecek cuaca di suatu lokasi.",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string", "description": "Nama kota"}},
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_search",
            "description": "Mencari informasi atau berita terbaru dari internet (Web Search).",
            "parameters": {
                "type": "object",
                "properties": {"search_query": {"type": "string", "description": "Kata kunci pencarian"}},
                "required": ["search_query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Membuat, melukis, atau meng-generate gambar/ilustrasi.",
            "parameters": {
                "type": "object",
                "properties": {"image_prompt": {"type": "string", "description": "Deskripsi gambar dalam bahasa Inggris"}},
                "required": ["image_prompt"]
            }
        }
    }
]