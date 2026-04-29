from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root and secrets/.env if present.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / "secrets" / ".env", override=True)

APP_NAME = os.getenv("APP_NAME", "Aira OpenClaw Agent")
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Jakarta")
PORT = int(os.getenv("PORT", "8000"))

# Job storage. SQLite makes polling survive container restart as long as ./data is mounted.
JOB_DB_PATH = os.getenv("JOB_DB_PATH", str(BASE_DIR / "data" / "jobs_memory.db"))
JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", "1800"))
JOB_STALE_SECONDS = int(os.getenv("JOB_STALE_SECONDS", "300"))

# n8n endpoints.
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "https://flow.eraenterprise.id/webhook").rstrip("/")
N8N_TIMEOUT = float(os.getenv("N8N_TIMEOUT", "60"))

# LLM is intentionally called via n8n webhook by default, so the office Ollama server is not exposed
# directly from this FastAPI service.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "n8n").lower().strip()
N8N_LLM_WEBHOOK_URL = os.getenv("N8N_LLM_WEBHOOK_URL", f"{N8N_BASE_URL}/aluna-aira")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://flow.eraenterprise.id/webhook/aluna-aira").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "120"))

# SearXNG is inside docker-compose by default.
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng:8080").rstrip("/")
SEARXNG_TIMEOUT = float(os.getenv("SEARXNG_TIMEOUT", "30"))
SEARXNG_HEADERS = {}
if "ngrok" in SEARXNG_URL:
    SEARXNG_HEADERS["ngrok-skip-browser-warning"] = "true"

HF_TOKEN = os.getenv("HF_TOKEN", "")
IMAGE_TIMEOUT = float(os.getenv("IMAGE_TIMEOUT", "120"))
