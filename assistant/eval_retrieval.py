# eval_retrieval.py
import json, sys
sys.path.append(".")
from api import search

# ─────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────
def precision_at_k(retrieved, relevant, k):
    return len(set(retrieved[:k]) & set(relevant)) / k

def recall_at_k(retrieved, relevant, k):
    if not relevant:
        return 0
    return len(set(retrieved[:k]) & set(relevant)) / len(relevant)

def mrr(retrieved, relevant):
    for rank, rid in enumerate(retrieved, start=1):
        if rid in relevant:
            return 1 / rank
    return 0.0

# ─────────────────────────────────────────
# Run
# ─────────────────────────────────────────
def run(eval_path="data/eval_dataset.json", k=5):
    with open(eval_path, encoding="utf-8") as f:
        data = json.load(f)

    p_list, r_list, mrr_list = [], [], []
    misses = []

    for s in data:
        results = search(s["question"])

        # chunks.json dùng "post_id"
        # eval_dataset.json dùng "relevant_article_ids" (article_id == post_id)
        retrieved = [r["post_id"] for r in results]
        relevant  = s["relevant_article_ids"]   # giá trị giống post_id

        p = precision_at_k(retrieved, relevant, k)
        r = recall_at_k(retrieved, relevant, k)
        m = mrr(retrieved, relevant)

        p_list.append(p)
        r_list.append(r)
        mrr_list.append(m)

        if m == 0:
            misses.append({
                "question" : s["question"],
                "expected" : relevant,
                "retrieved": retrieved
            })

    n = len(data)
    print("=" * 40)
    print("       RETRIEVAL METRICS")
    print("=" * 40)
    print(f"  Precision@{k}  : {sum(p_list)/n:.3f}")
    print(f"  Recall@{k}     : {sum(r_list)/n:.3f}")
    print(f"  MRR            : {sum(mrr_list)/n:.3f}")
    print(f"  Miss rate      : {len(misses)}/{n}")
    print("=" * 40)

    if misses:
        print("\n⚠ BM25 không tìm được bài đúng:")
        for m in misses[:5]:
            print(f"  Q       : {m['question']}")
            print(f"  Expected: {m['expected']}")
            print(f"  Got     : {m['retrieved']}")
            print()

if __name__ == "__main__":
    run()