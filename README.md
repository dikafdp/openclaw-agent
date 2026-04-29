# Aira Agent - OpenClaw Runtime Migration

Migrasi ini mengganti dependensi LangGraph dengan runtime bergaya OpenClaw: router → skill/tool → response. Alur eksternal tetap sama:

`Appsmith UI → n8n webhook /appsmith-aira → FastAPI AI Agent → n8n tools / n8n LLM webhook → Ollama qwen2.5:1.5b`

## Yang dipertahankan

- UI Appsmith tetap dipakai.
- n8n tetap menjadi proxy utama dari Appsmith dan tetap menjadi tool workflow RSUD.
- Model tetap `qwen2.5:1.5b` di Ollama kantor.
- SearXNG tetap bisa berjalan di Docker.
- Fitur lama tetap ada: chat, medis/booking, cuaca, search/browsing, search gambar, generate gambar.
- Endpoint polling tetap ada supaya tidak timeout: `/agent` dan `/cek-jawaban/{job_id}`.

## Struktur penting

```txt
app/
  main.py                  # FastAPI endpoint async + polling
  openclaw_agent.py         # Runtime pengganti LangGraph
  config.py                 # Env config
  routers/                  # Intent router per domain
  tools/                    # Tool medis, search, weather, image
  providers/llm_client.py   # LLM via n8n webhook ke Ollama
  storage/jobs.py           # SQLite job store
n8n-workflows/
  aiagent-openclaw-fixed.json
  llm-model-fixed.json
appsmith/
  ChatLogic.js
  Api_LLM_setup.md
```

## Cara pasang

1. Backup repo lama.
2. Copy isi folder ini ke repo `aira-agent` Anda.
3. Buat `.env` dari `.env.example`.
4. Pastikan `N8N_LLM_WEBHOOK_URL` mengarah ke workflow LLM n8n Anda, contoh:

```env
N8N_LLM_WEBHOOK_URL=https://flow.eraenterprise.id/webhook/aluna-aira
LLM_PROVIDER=n8n
OLLAMA_MODEL=qwen2.5:1.5b
OLLAMA_BASE_URL=http://192.168.253.29:11434
```

5. Jalankan Docker:

```bash
docker compose up -d --build
```

6. Test health:

```bash
curl http://localhost:8000/health
```

7. Test start job:

```bash
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"message":"halo aira"}'
```

8. Copy `job_id`, lalu test polling:

```bash
curl http://localhost:8000/cek-jawaban/JOB_ID_ANDA
```

## n8n

Import dua workflow ini:

1. `n8n-workflows/llm-model-fixed.json`
   - Path webhook: `/webhook/aluna-aira`
   - Tugas: menerima request dari FastAPI dan memanggil Ollama kantor.

2. `n8n-workflows/aiagent-openclaw-fixed.json`
   - Path webhook: `/webhook/appsmith-aira`
   - Tugas: menerima request Appsmith, start job ke FastAPI, dan polling status.

Di environment n8n, set:

```env
AIAGENT_BASE_URL=http://host.docker.internal:8000
OLLAMA_BASE_URL=http://192.168.253.29:11434
OLLAMA_MODEL=qwen2.5:1.5b
```

Jika n8n berada dalam Docker network yang sama dengan FastAPI, gunakan:

```env
AIAGENT_BASE_URL=http://aira-openclaw-fastapi:8000
```

Jika FastAPI dipublish dengan ngrok, gunakan URL ngrok Anda sebagai `AIAGENT_BASE_URL`.

## Appsmith

Pada API `Api_LLM`, gunakan:

```json
{
  "message": "{{ this.params.message || '' }}",
  "job_id": "{{ this.params.job_id || '' }}"
}
```

Path API harus:

```txt
/webhook/appsmith-aira
```

Lalu ganti JS Object `ChatLogic` dengan isi `appsmith/ChatLogic.js`.

## Catatan keamanan

- Jangan commit `.env`, token ngrok, token HuggingFace, atau kredensial n8n.
- Jangan expose SearXNG tanpa kebutuhan. Default Docker hanya expose di port `8888` host Anda.
- Jika endpoint dipublikasi dengan ngrok, pertimbangkan validasi token/API key di n8n atau FastAPI.
