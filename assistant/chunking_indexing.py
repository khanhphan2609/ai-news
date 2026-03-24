import json
import re

INPUT_FILE = "data/processed_kb.json"
CHUNK_FILE = "data/chunks.json"
INDEX_FILE = "data/inverted_index.json"


# -------------------------
# Chunk text theo đoạn
# -------------------------
def chunk_text(text, max_len=500):

    paragraphs = text.split("\n")

    chunks = []
    current = ""

    for p in paragraphs:

        if len(current) + len(p) < max_len:
            current += " " + p
        else:
            chunks.append(current.strip())
            current = p

    if current:
        chunks.append(current.strip())

    return chunks


# -------------------------
# Build chunks
# -------------------------
def build_chunks(data):

    chunks = []
    chunk_id = 0

    for article in data:

        article_chunks = chunk_text(article["clean_text"])

        for c in article_chunks:

            chunk = {
                "chunk_id": chunk_id,
                "post_id": article["id"],
                "title": article["title"],
                "link": article["link"],
                "text": c
            }

            chunks.append(chunk)

            chunk_id += 1

    return chunks


# -------------------------
# Build inverted index
# -------------------------
def build_inverted_index(chunks):

    index = {}

    for chunk in chunks:

        words = chunk["text"].split()

        for word in words:

            if word not in index:
                index[word] = []

            index[word].append(chunk["chunk_id"])

    return index


# -------------------------
# MAIN
# -------------------------
def main():

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("Building chunks...")

    chunks = build_chunks(data)

    with open(CHUNK_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print("Chunks saved:", len(chunks))

    print("Building inverted index...")

    index = build_inverted_index(chunks)

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print("Index size:", len(index))


if __name__ == "__main__":
    main()