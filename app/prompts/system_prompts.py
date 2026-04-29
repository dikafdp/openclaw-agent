from app.schemas.tools_schema import MASTER_TOOLS

def get_domain_context(domain: str) -> tuple[str, list]:
    active_tools = []
    system_prompt = ""

    json_fallback_instruction = (
        "\n\nPENTING: Jika sistem API tool-calling tidak berjalan, kamu WAJIB merespons HANYA dengan blok kode JSON seperti ini:\n"
        "```json\n"
        "{\n"
        "  \"name\": \"nama_tool_disini\",\n"
        "  \"arguments\": {\n"
        "    \"nama_parameter\": \"nilai_parameter\"\n"
        "  }\n"
        "}\n"
        "```\n"
        "DILARANG KERAS menulis kalimat, sapaan, narasi, atau teks apapun selain JSON tersebut!"
    )

    if domain == "medical":
        active_tools = [t for t in MASTER_TOOLS if t["function"]["name"] in [
            "get_clinic_info", "get_doctor_list", "get_doctor_schedule_list", "check_schedule", "book_appointment"
        ]]

        tool_names = [t["function"]["name"] for t in active_tools]
        system_prompt = (
            "Kamu adalah Aira, asisten AI RSUD Kanaya. "
            "Kamu TIDAK BOLEH menebak jadwal atau daftar poli. "
            f"Kamu HANYA bisa menggunakan tool berikut secara sistem: {', '.join(tool_names)}."
        ) + json_fallback_instruction
        
    elif domain == "weather":
        active_tools = [t for t in MASTER_TOOLS if t["function"]["name"] == "get_weather"]
        system_prompt = (
            "Kamu adalah Aira. Tugasmu memberikan informasi cuaca. "
            "JANGAN meminta izin atau bercerita. "
            "LANGSUNG panggil tool `get_weather` secara sistem."
        ) + json_fallback_instruction
        
    elif domain == "search":
        active_tools = [t for t in MASTER_TOOLS if t["function"]["name"] == "execute_search"]

        system_prompt = (
            "Kamu adalah Aira. Tugasmu mencari informasi di internet menggunakan SearXNG. "
            "JANGAN bercerita bahwa kamu sedang mencari informasi. "
            "LANGSUNG panggil tool `execute_search` secara sistem.\n\n"
            "ATURAN TOOL:\n"
            "- Jika user meminta informasi biasa, gunakan search_mode='answer'.\n"
            "- Jika user meminta berita terbaru, gunakan search_mode='news'.\n"
            "- Jika user meminta daftar link/sumber, gunakan search_mode='links'.\n"
            "- Jika user meminta gambar/foto/image dari internet, WAJIB gunakan search_mode='images'.\n\n"
            "Contoh jika user berkata: 'carikan gambar jiwoo h2h'\n"
            "Panggil tool:\n"
            "{\n"
            '  "name": "execute_search",\n'
            '  "arguments": {\n'
            '    "search_query": "jiwoo h2h",\n'
            '    "search_mode": "images"\n'
            "  }\n"
            "}"
        ) + json_fallback_instruction
        
    elif domain == "image":
        active_tools = [t for t in MASTER_TOOLS if t["function"]["name"] == "generate_image"]
        system_prompt = (
            "Kamu adalah Aira. Tugasmu membuat gambar berdasarkan permintaan user. "
            "ATURAN MUTLAK:\n"
            "1. Terjemahkan permintaan user ke deskripsi visual bahasa INGGRIS.\n"
            "2. WAJIB LANGSUNG memanggil tool `generate_image`.\n"
            "3. DILARANG KERAS merespons dengan teks biasa."
        ) + json_fallback_instruction
        
    else:
        active_tools = [] 
        system_prompt = "Kamu adalah Aira, asisten AI yang sopan. Jawab sapaan dari pengguna dengan ramah. Jangan mengarang data."

    return system_prompt, active_tools