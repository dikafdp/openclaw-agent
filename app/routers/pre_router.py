import re

def classify_intent(user_input: str) -> str:
    text_lower = user_input.lower().strip()

    if not text_lower:
        return "chat"

    def contains_keyword(text, keywords):
        pattern = r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b'
        return bool(re.search(pattern, text))

    # Image Search
    search_image_keywords = ["cari gambar", "carikan gambar", "cari foto", "carikan foto", "minta gambar"]
    if contains_keyword(text_lower, search_image_keywords):
        return "search"

    # 1. Image (Generate)
    image_keywords = [
        "buat gambar", "bikin gambar", "generate gambar", "buatkan gambar",
        "gambarin", "lukis", "ilustrasikan", "buat ilustrasi", 
        "stable diffusion", "stabble difusion", "image generator", "bikinin gambar",
        "tolong gambar", "sketsa", "potret", "gambarkan", "bikin ilustrasi", "flux"
    ]
    if contains_keyword(text_lower, image_keywords) or text_lower.startswith("gambar"):
        return "image"

    # 2. Medical (Aira RSUD)
    medical_keywords = [
        "dokter", "poli", "jadwal", "booking", "janji", "buat janji",
        "klinik", "rsud", "pasien", "bpjs", "rawat jalan", "pendaftaran",
        "spesialis", "periksa", "berobat", "antrian", "antrean", "nomor antrean",
        "rujukan", "igd", "ugd", "rawat inap", "kamar", "obat", "resep",
        "tebus obat", "sakit", "keluhan", "batal janji", "kanaya", "registrasi"
    ]
    if contains_keyword(text_lower, medical_keywords):
        return "medical"

    # 3. Weather
    weather_keywords = [
        "cuaca", "suhu", "hujan", "panas", "mendung", "gerimis", "badai", 
        "weather", "forecast", "prakiraan", "iklim", "cerah", "banjir",
        "bmkg", "derajat", "celcius", "celsius"
    ]
    if contains_keyword(text_lower, weather_keywords):
        return "weather"

    # 4. Web Search
    search_keywords = [
        "cari", "search", "browse", "berita", "informasi", "artikel",
        "info", "siapa", "apa itu", "apa", "kapan", "googling", "searxng",
        "dimana", "kenapa", "bagaimana", "jelaskan", "tolong cari", "carikan",
        "cariin", "pengertian", "definisi", "tolong jelaskan", "maksud dari",
        "tolong carikan"
    ]
    is_question = text_lower.endswith("?")
    
    if contains_keyword(text_lower, search_keywords) or is_question:
        return "search"

    return "chat"