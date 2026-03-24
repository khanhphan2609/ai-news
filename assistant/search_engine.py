# search_engine.py

import json
import re
from rank_bm25 import BM25Okapi


# -------------------------
# Clean + tokenize query
# -------------------------
def preprocess(text):

    text = text.lower()

    text = re.sub(r'[^\w\s]', ' ', text)

    tokens = text.split()

    return tokens


# -------------------------
# Load chunks
# -------------------------
with open("data/chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)


# -------------------------
# Prepare corpus
# -------------------------
corpus = []
for chunk in chunks:
    corpus.append(preprocess(chunk["text"]))


# -------------------------
# Build BM25
# -------------------------
bm25 = BM25Okapi(corpus)

print("Search engine ready")

# -------------------------
# Query loop
# -------------------------
while True:

    query = input("\nNhập câu hỏi: ")

    if query == "exit":
        break

    tokenized_query = preprocess(query)

    scores = bm25.get_scores(tokenized_query)

    top_n = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:5]

    print("\nTop kết quả:\n")

    for i in top_n:

        chunk = chunks[i]

        print("Tiêu đề:", chunk["title"])
        print("Link:", chunk["link"])
        print("Đoạn:", chunk["text"][:200])
        print("Score:", scores[i])
        print("-" * 50)