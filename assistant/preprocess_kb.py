# preprocess_kb.py

import json
import re
import math
from collections import Counter
from bs4 import BeautifulSoup
from underthesea import word_tokenize

INPUT_FILE  = "data/knowledge_base.json"
OUTPUT_FILE = "data/processed_kb.json"

# ─────────────────────────────────────────
# Seed stopwords (tối thiểu, chỉ ký tự đặc biệt)
# ─────────────────────────────────────────
SEED_STOPWORDS = {
    ".", "?", "!", ";", ":", ",", "-", "_",
    "(", ")", "[", "]", "{", "}", "\"", "'",
    "/", "\\", "|", "@", "#", "$", "%", "^",
    "&", "*", "+", "=",
    "bookmark", "share", "comment", "like",
    "view", "author", "category", "date"
}

# ─────────────────────────────────────────
# HTML / clean / tokenize
# ─────────────────────────────────────────
def remove_html(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(separator=" ")

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def tokenize(text: str) -> list[str]:
    return word_tokenize(text)

# ─────────────────────────────────────────
# Tự động học stopword từ toàn bộ corpus
# ─────────────────────────────────────────
def build_auto_stopwords(
    all_token_lists: list[list[str]],
    tf_top_ratio: float = 0.01,   # top 1% từ phổ biến nhất → stopword
    idf_low_thresh: float = 0.1,  # IDF < ngưỡng này → xuất hiện ở > 90% bài
    min_token_len: int = 1,        # bỏ token quá ngắn
) -> set[str]:
    """
    Kết hợp 2 tiêu chí:
      1. TF cao:  tần suất toàn corpus nằm trong top tf_top_ratio
      2. IDF thấp: log(N / df) < idf_low_thresh  ↔  từ có mặt ở hầu hết bài
    Trả về tập stopword tự động.
    """
    N = len(all_token_lists)

    # --- TF toàn corpus ---
    total_tf: Counter = Counter()
    for tokens in all_token_lists:
        total_tf.update(tokens)

    total_count = sum(total_tf.values())
    cutoff_rank = max(1, int(len(total_tf) * tf_top_ratio))
    top_tf_words = {w for w, _ in total_tf.most_common(cutoff_rank)}

    # --- IDF ---
    df: Counter = Counter()
    for tokens in all_token_lists:
        for w in set(tokens):         # mỗi bài chỉ đếm 1 lần
            df[w] += 1

    low_idf_words = set()
    for word, doc_freq in df.items():
        idf = math.log(N / doc_freq) if doc_freq > 0 else 0
        if idf < idf_low_thresh:
            low_idf_words.add(word)

    # --- Token quá ngắn ---
    short_tokens = {w for w in total_tf if len(w) <= min_token_len}

    auto_stopwords = top_tf_words | low_idf_words | short_tokens
    return auto_stopwords

# ─────────────────────────────────────────
# Remove stopwords + simple stem
# ─────────────────────────────────────────
def remove_stopwords(tokens: list[str], stopwords: set[str]) -> list[str]:
    return [t for t in tokens if t not in stopwords]

def stem_tokens(tokens: list[str]) -> list[str]:
    return [re.sub(r"^(đang|đã|sẽ)\s*", "", t) for t in tokens]

# ─────────────────────────────────────────
# Main
# ─────────────────────────────────────────
def main():
    print("Loading knowledge base...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # --- Pass 1: raw tokenize toàn bộ corpus ---
    print("Pass 1 – tokenizing all articles to learn stopwords...")
    raw_token_lists: list[list[str]] = []
    raw_texts: list[str] = []

    for article in data:
        text = clean_text(remove_html(article["content"]))
        tokens = tokenize(text)
        # loại seed stopword trước khi học để không nhiễu thống kê
        tokens = [t for t in tokens if t not in SEED_STOPWORDS]
        raw_texts.append(text)
        raw_token_lists.append(tokens)

    # --- Học stopword tự động ---
    print("Learning stopwords from corpus statistics...")
    auto_stopwords = build_auto_stopwords(
        raw_token_lists,
        tf_top_ratio=0.01,   # điều chỉnh nếu corpus nhỏ/lớn
        idf_low_thresh=0.1,
        min_token_len=1,
    )
    all_stopwords = SEED_STOPWORDS | auto_stopwords

    print(f"  → {len(auto_stopwords)} auto stopwords detected")
    print(f"  → {len(all_stopwords)} total stopwords (seed + auto)")
    # In 30 từ đại diện để kiểm tra
    sample = sorted(auto_stopwords)[:30]
    print(f"  → Sample auto stopwords: {sample}")

    # Lưu danh sách stopword để kiểm tra / tái sử dụng
    with open("data/auto_stopwords.json", "w", encoding="utf-8") as f:
        json.dump(sorted(all_stopwords), f, ensure_ascii=False, indent=2)

    # --- Pass 2: xử lý từng bài với stopword đã học ---
    print("Pass 2 – processing articles...")
    processed = []
    for article, text, raw_tokens in zip(data, raw_texts, raw_token_lists):
        tokens = remove_stopwords(raw_tokens, all_stopwords)
        tokens = stem_tokens(tokens)
        article["clean_text"] = text
        article["tokens"] = tokens
        processed.append(article)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)

    print(f"Done. Saved {len(processed)} articles to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()