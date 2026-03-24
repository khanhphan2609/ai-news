# rag_assistant.py

import os
from dotenv import load_dotenv
import json
import re
from rank_bm25 import BM25Okapi
from google import genai

# -------------------------
# CONFIG
# -------------------------
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY)

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


# -------------------------
# Preprocess
# -------------------------

def preprocess(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)

    return text.split()


# -------------------------
# Load chunks
# -------------------------

with open("data/chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

corpus = [preprocess(c["text"]) for c in chunks]
bm25 = BM25Okapi(corpus)
print("AI News Assistant Ready")

# -------------------------
# Search
# -------------------------

def search(query, top_k=5):

    tokens = preprocess(query)

    scores = bm25.get_scores(tokens)

    top_ids = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:top_k]

    results = [chunks[i] for i in top_ids]

    return results


# -------------------------
# Generate Answer
# -------------------------

def generate_answer(query, contexts):

    context_text = ""

    for c in contexts:

        context_text += f"""
Tiêu đề: {c['title']}
Link: {c['link']}
Nội dung: {c['text']}
"""

    prompt = f"""
Bạn là trợ lý AI cho website tin tức Phú Quốc.

Dựa trên các đoạn bài báo sau để trả lời câu hỏi.

{context_text}

Câu hỏi: {query}

Yêu cầu:
- Trả lời ngắn gọn
- Nếu có bài báo liên quan hãy dẫn link
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text


# -------------------------
# Chat Loop
# -------------------------

while True:
    query = input("\nHỏi: ")

    if query == "exit":
        break

    contexts = search(query)

    answer = generate_answer(query, contexts)

    print("\nAI:", answer)