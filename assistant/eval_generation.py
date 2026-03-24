# eval_generation.py
# pip install rouge-score sentence-transformers
import json, os, time, re
from rouge_score import rouge_scorer
from sentence_transformers import SentenceTransformer, util
from dotenv import load_dotenv
import sys
sys.path.append(".")
from api import search, generate_answer_cached, build_context

load_dotenv()

rouge_fn = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)
encoder  = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# ─────────────────────────────────────────
# Retry helper
# ─────────────────────────────────────────
def extract_retry_delay(err, default=60.0):
    match = re.search(r"retry[^\d]*(\d+(?:\.\d+)?)\s*s", str(err), re.IGNORECASE)
    return float(match.group(1)) + 5 if match else default

def ask_gemini(question: str, max_retries: int = 5) -> str:
    for attempt in range(max_retries):
        try:
            contexts    = search(question)
            context_str = build_context(contexts)
            result      = generate_answer_cached(question, context_str)

            # generate_answer_cached trả về "Lỗi AI: 429..." thay vì raise
            if "429" in result or "RESOURCE_EXHAUSTED" in result:
                wait = extract_retry_delay(result, default=60.0)
                print(f"  ⏳ Rate limit, chờ {wait:.0f}s (lần {attempt+1}/{max_retries})...")
                time.sleep(wait)
                continue

            return result

        except Exception as e:
            err = str(e)
            if "quota" in err.lower():
                print("❌ Hết quota hôm nay → dừng")
                raise
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                wait = extract_retry_delay(err, default=60.0)
                print(f"  ⏳ Rate limit, chờ {wait:.0f}s (lần {attempt+1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    return "Lỗi: vượt quá số lần thử"

# ─────────────────────────────────────────
# Main eval
# ─────────────────────────────────────────
def run(eval_path="data/eval_dataset.json"):
    search.cache_clear()
    generate_answer_cached.cache_clear()
    
    with open(eval_path, encoding="utf-8") as f:
        data = json.load(f)

    rouge_list, sem_list = [], []
    details = []

    for i, s in enumerate(data, 1):
        print(f"[{i}/{len(data)}] {s['question'][:50]}")
        try:
            prediction = ask_gemini(s["question"])
            reference  = s["reference_answer"]

            if prediction.startswith("Lỗi"):
                print(f"  ✗ Bỏ qua: {prediction[:60]}")
                continue

            # ROUGE-L
            r = rouge_fn.score(reference, prediction)["rougeL"].fmeasure

            # Semantic Similarity
            e_ref  = encoder.encode(reference,  convert_to_tensor=True)
            e_pred = encoder.encode(prediction, convert_to_tensor=True)
            sim    = float(util.cos_sim(e_ref, e_pred))

            rouge_list.append(r)
            sem_list.append(sim)

            flag = "⚠" if sim < 0.6 else "✓"
            details.append({
                "question"  : s["question"],
                "reference" : reference,
                "prediction": prediction,
                "rouge_l"   : round(r, 3),
                "sem_sim"   : round(sim, 3),
                "flag"      : flag
            })

            print(f"  {flag} sem={sim:.2f} rouge={r:.2f}")

        except Exception as e:
            print(f"  ✗ Lỗi không xử lý được: {e}")

        time.sleep(6)  # gemini-2.5-flash-lite: 15 RPM → 1 req/4s, dùng 6s cho an toàn

        # Auto-save mỗi 10 câu
        if len(details) % 10 == 0 and details:
            with open("data/eval_results.json", "w", encoding="utf-8") as f:
                json.dump(details, f, ensure_ascii=False, indent=2)
            print(f"  💾 Auto-saved {len(details)} results")

    # Lưu lần cuối
    with open("data/eval_results.json", "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=2)

    if not rouge_list:
        print("Không có kết quả nào!")
        return

    n       = len(details)
    flagged = [d for d in details if d["flag"] == "⚠"]

    print("\n" + "=" * 40)
    print("      GENERATION METRICS")
    print("=" * 40)
    print(f"  Tổng đánh giá    : {n}/{len(data)}")
    print(f"  ROUGE-L avg      : {sum(rouge_list)/n:.3f}")
    print(f"  Semantic Sim avg : {sum(sem_list)/n:.3f}")
    print(f"  Tốt (sim≥0.6)    : {n - len(flagged)}/{n}")
    print(f"  Kém (sim<0.6)    : {len(flagged)}/{n}")
    print("=" * 40)

    if flagged:
        print("\n⚠ Câu trả lời cần cải thiện:")
        for d in flagged[:3]:
            print(f"\n  Q   : {d['question']}")
            print(f"  Ref : {d['reference'][:80]}...")
            print(f"  Pred: {d['prediction'][:80]}...")

if __name__ == "__main__":
    run()