# auto_label.py
import json, os, time, re, math
from google import genai
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
client     = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

with open("data/knowledge_base.json", encoding="utf-8") as f:
    articles = json.load(f)

dataset = []
failed  = []

BATCH_SIZE = 5

# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────
def extract_retry_delay(error_msg: str, default: float = 60.0) -> float:
    match = re.search(r"retry[^\d]*(\d+(?:\.\d+)?)\s*s", str(error_msg), re.IGNORECASE)
    return float(match.group(1)) + 2 if match else default

def call_gemini_with_retry(prompt: str, max_retries: int = 5) -> str:
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            err = str(e)

            # ❌ hết quota thì dừng luôn
            if "quota" in err.lower():
                print("❌ Hết quota hôm nay → dừng script")
                exit()

            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                wait = extract_retry_delay(err)
                print(f"  ⏳ Rate limit, chờ {wait:.0f}s...")
                time.sleep(wait)
            else:
                raise

    raise Exception("Retry failed")

# ─────────────────────────────────────────
# Batch loop
# ─────────────────────────────────────────
total_batches = math.ceil(len(articles) / BATCH_SIZE)

for i in range(0, len(articles), BATCH_SIZE):
    batch = articles[i:i+BATCH_SIZE]

    # 🧠 Build prompt cho nhiều bài
    articles_text = ""
    for art in batch:
        articles_text += f"""
ID: {art['id']}
Tiêu đề: {art.get("title", "")}
Nội dung: {art.get("content", "")[:1000]}
---
"""

    prompt = f"""
Bạn là người đọc tin tức Việt Nam.

Dựa vào các bài báo dưới đây, hãy tạo cho MỖI bài:
- 1 câu hỏi tự nhiên (không dùng từ trong tiêu đề)
- 1 câu trả lời ngắn (2-3 câu)

Trả về JSON ARRAY, mỗi phần tử có format:
[
  {{
    "article_id": ...,
    "question": "...",
    "reference_answer": "..."
  }}
]

Danh sách bài:
{articles_text}
"""

    try:
        text = call_gemini_with_retry(prompt)
        text = text.replace("```json", "").replace("```", "").strip()

        parsed_list = json.loads(text)

        for item in parsed_list:
            article = next((a for a in batch if a["id"] == item["article_id"]), None)

            if not article:
                continue

            dataset.append({
                "article_id": article["id"],
                "article_title": article.get("title", ""),
                "question": item["question"],
                "reference_answer": item["reference_answer"],
                "relevant_article_ids": [article["id"]]
            })

            print(f"✓ {article['id']} | {item['question'][:60]}")

    except Exception as e:
        print(f"✗ Batch {i//BATCH_SIZE} | {e}")
        for art in batch:
            failed.append(art["id"])

    time.sleep(5)  # tăng nhẹ vì batch nặng hơn

    # auto-save
    if len(dataset) % 10 == 0 and dataset:
        with open("data/eval_dataset.json", "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved {len(dataset)} samples")

# ─────────────────────────────────────────
# Save cuối
# ─────────────────────────────────────────
with open("data/eval_dataset.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

print(f"\n✓ {len(dataset)} samples  ✗ {len(failed)} failed")