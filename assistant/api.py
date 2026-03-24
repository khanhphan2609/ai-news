# api.py

import os
import json
import re
from functools import lru_cache

from dotenv import load_dotenv
from rank_bm25 import BM25Okapi
from groq import Groq
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# -------------------------
# CONFIG
# -------------------------
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

client = Groq(api_key=GROQ_API_KEY)

TOP_K = 5
MIN_SCORE = 0.5

# -------------------------
# FASTAPI
# -------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Question(BaseModel):
    question: str

# -------------------------
# LOAD SYNONYMS
# -------------------------
def load_synonyms():
    path = "data/synonyms.json"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        print(f"Synonyms: {len(data)} loaded")
        return data

    return {
        "đảo ngọc": "phú quốc",
        "phi trường": "sân bay",
        "nơi lưu trú": "khách sạn resort",
        "ghé thăm": "du lịch tham quan",
        "giá tốt": "không bị chặt chém",
    }

SYNONYMS = load_synonyms()

# -------------------------
# TEXT UTILS
# -------------------------
def preprocess(text: str):
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return text.split()

def expand_query(query: str):
    q = query.lower()
    for k, v in SYNONYMS.items():
        if k in q:
            q += " " + v
    return q

# -------------------------
# LOAD DATA
# -------------------------
with open("data/chunks.json", encoding="utf-8") as f:
    chunks = json.load(f)

valid_chunks = [c for c in chunks if c.get("text")]
corpus = [preprocess(c["text"]) for c in valid_chunks]
bm25 = BM25Okapi(corpus)

print(f"Chunks: {len(valid_chunks)}")

# -------------------------
# SEARCH (có cache)
# -------------------------
@lru_cache(maxsize=200)
def search(query: str):
    expanded = expand_query(query)
    tokens = preprocess(expanded)

    scores = bm25.get_scores(tokens)

    ranked = sorted(
        [(i, s) for i, s in enumerate(scores)],
        key=lambda x: x[1],
        reverse=True
    )

    results = []
    for i, score in ranked[:TOP_K * 2]:
        if score < MIN_SCORE:
            continue
        results.append(valid_chunks[i])
        if len(results) >= TOP_K:
            break

    return results

# -------------------------
# GENERATE
# -------------------------
def build_context(contexts):
    return "\n".join([
        f"[{i+1}] {c['title']} | {c['link']}\n{c['text'][:500]}"
        for i, c in enumerate(contexts)
    ])

@lru_cache(maxsize=200)
def generate_answer_cached(query: str, context_str: str):
    prompt = f"""Bạn là AI tin tức Phú Quốc.

Chỉ dùng thông tin dưới đây.
Nếu không có → trả lời: "Tôi không có thông tin."

{context_str}

Câu hỏi: {query}

Trả lời 3-5 câu, có link cuối."""

    try:
        res = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"Lỗi AI: {e}"

# -------------------------
# API
# -------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat")
def chat(q: Question):
    contexts = search(q.question)

    if not contexts:
        return {
            "answer": "Không tìm thấy thông tin phù hợp.",
            "sources": []
        }

    context_str = build_context(contexts)
    answer = generate_answer_cached(q.question, context_str)

    sources = [
        {
            "title": c["title"],
            "link": c["link"],
            "post_id": c["post_id"],
        }
        for c in contexts
    ]

    return {
        "answer": answer,
        "sources": sources
    }