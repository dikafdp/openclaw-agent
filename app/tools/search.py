from __future__ import annotations

import base64
import re
from typing import Any, Dict, List
from urllib.parse import urlparse

import httpx

from app import config
from app.providers.llm_client import llm_client
from app.state import AgentState


def _clean_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _get_source_name(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def _normalize_results(raw_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    seen_urls = set()
    for item in raw_results:
        url = _clean_text(item.get("url") or item.get("link") or "")
        title = _clean_text(item.get("title") or "")
        snippet = _clean_text(item.get("content") or item.get("snippet") or item.get("description") or "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        normalized.append({
            "title": title or url,
            "url": url,
            "snippet": snippet,
            "source": _get_source_name(url),
        })
    return normalized


def _format_links(query: str, results: List[Dict[str, str]], *, title: str = "Berikut beberapa sumber") -> str:
    lines = [f"{title} untuk topik: {query}\n"]
    for i, item in enumerate(results[:7], 1):
        lines.append(f"{i}. {item['title']}")
        lines.append(f"   {item['url']}")
        if item["snippet"]:
            lines.append(f"   {item['snippet']}")
        lines.append("")
    return "\n".join(lines).strip()


def _remove_raw_urls(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _fallback_answer(query: str, results: List[Dict[str, str]], mode: str) -> str:
    snippets = [item["snippet"] for item in results[:5] if item.get("snippet")]
    sources = [item["source"] for item in results[:5] if item.get("source")]
    if snippets:
        joined = " ".join(snippets[:2])
        source_text = f" Sumber yang diringkas antara lain: {', '.join(dict.fromkeys(sources))}." if sources else ""
        return f"Berdasarkan hasil pencarian saat ini, {joined}{source_text}"
    return f"Saya menemukan beberapa hasil terkait {query}, tetapi ringkasannya belum cukup jelas untuk dijawab dengan yakin."


async def _generate_natural_answer(user_input: str, query: str, mode: str, results: List[Dict[str, str]]) -> str:
    context_blocks = []
    for i, item in enumerate(results[:5], 1):
        snippet_text = item["snippet"][:350] + "..." if len(item["snippet"]) > 350 else item["snippet"]
        context_blocks.append(
            f"[{i}]\nJudul: {item['title']}\nSumber: {item['source']}\nRingkasan: {snippet_text}\n"
        )
    context = "\n".join(context_blocks)
    prompt = f"""
Anda adalah Aira, asisten AI berbahasa Indonesia.
Tugas:
- Jawab pertanyaan pengguna secara natural, akurat, dan langsung ke inti.
- Gunakan data pencarian web di bawah ini.
- Jangan mengarang informasi di luar data.
- Jangan tampilkan URL mentah kecuali pengguna meminta link.

Mode jawaban: {mode}
Pertanyaan pengguna: {user_input}
Query pencarian: {query}
Data web:
{context}

Jawaban:
""".strip()
    try:
        text = await llm_client.complete(prompt, temperature=0.0)
        text = text.strip()
        if not text:
            return _fallback_answer(query, results, mode)
        return _remove_raw_urls(text) if mode != "links" else text
    except Exception:
        return _fallback_answer(query, results, mode)


async def _fetch_accessible_image(client: httpx.AsyncClient, raw_results: List[Dict[str, Any]]) -> str:
    for item in raw_results[:15]:
        candidate_url = item.get("img_src") or item.get("thumbnail") or ""
        if not candidate_url:
            continue
        if candidate_url.startswith("//"):
            candidate_url = "https:" + candidate_url
        if not candidate_url.startswith("http") or candidate_url.lower().endswith((".svg", ".ico")):
            continue
        try:
            img_res = await client.get(
            candidate_url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, 
            timeout=8,
            follow_redirects=True
            )
            if img_res.status_code != 200:
                continue
            content_type = img_res.headers.get("Content-Type", "image/jpeg").lower()
            if "text/" in content_type or "html" in content_type or "svg" in content_type:
                continue
            encoded = base64.b64encode(img_res.content).decode("utf-8")
            return f"data:{content_type};base64,{encoded}"
        except Exception:
            continue
    return ""


async def execute_search(state: AgentState) -> AgentState:
    user_input = state.get("user_input", "").strip()
    query = state.get("search_query", "").strip()
    mode = (state.get("search_mode", "answer") or "answer").strip().lower()
    if not query:
        return {"final_answer": "Query kosong, tidak bisa mencari."}

    category = "images" if mode == "images" else "general"
    try:
        async with httpx.AsyncClient(timeout=config.SEARXNG_TIMEOUT) as client:
            response = await client.get(
                f"{config.SEARXNG_URL}/search",
                params={
                    "q": query,
                    "format": "json",
                    "language": "id-ID",
                    "safesearch": 1,
                    "categories": category,
                },
                headers=config.SEARXNG_HEADERS,
            )
            response.raise_for_status()
            data = response.json()
            raw_results = data.get("results", [])

            if mode == "images":
                image_url = await _fetch_accessible_image(client, raw_results)
                if image_url:
                    return {"search_results": raw_results[:2], "final_answer": f"Berikut gambar dari internet untuk: {query}", "image_url": image_url}
                return {"search_results": [], "final_answer": f"Maaf, saya tidak menemukan gambar yang bisa diakses untuk: {query}"}

        results = _normalize_results(raw_results)[:7]
        if not results:
            return {"search_results": [], "final_answer": f"Saya belum menemukan hasil yang relevan untuk: {query}"}

        if mode == "links":
            final_answer = _format_links(query, results)
        elif mode == "news":
            final_answer = _format_links(query, results, title="Berikut berita terkini")
        else:
            final_answer = await _generate_natural_answer(user_input, query, "answer", results)
        return {"search_results": results, "final_answer": final_answer}
    except httpx.HTTPError as e:
        return {"final_answer": f"Maaf, mesin pencarian sedang tidak dapat dihubungi. Search gagal: {str(e)}"}
    except ValueError:
        return {"final_answer": "Search gagal: respons bukan JSON yang valid."}
    except Exception as e:
        return {"final_answer": f"Search gagal: {str(e)}"}
