# build_synonyms.py
import json, os, re, time
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── Đọc các câu miss từ eval ──────────────────────────────
with open("data/eval_dataset.json", encoding="utf-8") as f:
    eval_data = json.load(f)

with open("data/chunks.json", encoding="utf-8") as f:
    chunks = json.load(f)

chunk_map = {c["post_id"]: c["text"] for c in chunks if c.get("text","").strip()}

# ── Với mỗi câu hỏi, nhờ Gemini tìm từ khóa từ bài gốc ──
synonyms = {}

for sample in eval_data:
    post_id   = sample["relevant_article_ids"][0]
    # map sang post_id trong chunks:
    chunk_map = {c["post_id"]: c["text"] for c in chunks}
    question  = sample["question"]
    ref_text  = chunk_map.get(post_id, "")

    if not ref_text:
        continue

    prompt = f"""
So sánh câu hỏi và đoạn văn bản dưới đây.
Tìm các cụm từ trong câu hỏi mà KHÔNG xuất hiện trong đoạn văn,
nhưng có nghĩa tương đương với một cụm từ trong đoạn văn.

Câu hỏi: {question}
Đoạn văn: {ref_text[:600]}

Trả về JSON, không giải thích:
{{
  "mappings": [
    {{"query_phrase": "...", "doc_phrase": "..."}},
    ...
  ]
}}
Nếu không có cụm nào khác nhau, trả về {{"mappings": []}}
"""
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        text   = resp.text.strip().replace("```json","").replace("```","").strip()
        parsed = json.loads(text)
        for m in parsed.get("mappings", []):
            qp = m["query_phrase"].strip().lower()
            dp = m["doc_phrase"].strip().lower()
            if qp and dp and qp != dp:
                synonyms[qp] = dp
                print(f"  + '{qp}' → '{dp}'")
    except Exception as e:
        print(f"✗ {e}")
    time.sleep(4)

# ── Lưu ra file ───────────────────────────────────────────
with open("data/synonyms.json", "w", encoding="utf-8") as f:
    json.dump(synonyms, f, ensure_ascii=False, indent=2)

print(f"\nDone. {len(synonyms)} mappings → data/synonyms.json")