# 🏝️ Hệ Thống Hỏi Đáp Tự Động — Tin Tức Phú Quốc

> **Môn học:** Truy Hồi Thông Tin
> **Trường:** Đại học Ngoại Ngữ - Tin Học TP.HCM (HUFLIT) — Khoa Công Nghệ Thông Tin
> **Giảng viên:** ThS. Nguyễn Thị Phương Trang
> **Thực hiện:** Phan Văn Khánh — MSSV: 23DH111605

---

## 📌 Giới thiệu

Hệ thống hỏi đáp tự động (Question Answering) cho website tin tức địa phương **[news.phuquocandyou.com](https://news.phuquocandyou.com)**, kết hợp thuật toán truy hồi **BM25** và mô hình ngôn ngữ lớn **Gemini** để trả lời câu hỏi chính xác, có dẫn nguồn bài viết.

### Kiến trúc RAG (Retrieval-Augmented Generation)

```
Câu hỏi người dùng
        ↓
  Query Expansion  ←── synonyms.json (tự động sinh bởi Gemini)
        ↓
   BM25 Search  ←── chunks.json + inverted_index.json
        ↓
  Top-5 Chunks liên quan (score ≥ 0.5)
        ↓
  Gemini LLM  ←── prompt với ngữ cảnh (500 ký tự/chunk)
        ↓
  Câu trả lời + Link bài báo
```

---

## 🗂️ Cấu trúc dự án

```
assistant/
├── api.py                  # FastAPI server — endpoint chính (/chat, /health)
├── rag_assistant.py        # Pipeline RAG CLI (baseline, test nhanh)
├── search_engine.py        # BM25 search engine CLI (debug retrieval)
│
├── crawl_data.py           # Bước 1: Crawl WordPress REST API
├── preprocess_kb.py        # Bước 2: Tiền xử lý NLP tiếng Việt
├── chunking_indexing.py    # Bước 3: Chunking + xây dựng inverted index
│
├── build_synonyms.py       # Tự động sinh bảng từ đồng nghĩa (Gemini)
├── auto_label.py           # Tự động sinh tập đánh giá (Gemini)
├── eval_retrieval.py       # Đánh giá Precision@K, Recall@K, MRR
├── eval_generation.py      # Đánh giá ROUGE-L, Semantic Similarity
├── run_eval.py             # Chạy toàn bộ pipeline đánh giá
├── check_models.py         # Kiểm tra Gemini models available
├── run_pipeline.sh         # Script chạy toàn bộ pipeline một lệnh
│
└── data/
    ├── categories.json         # 15 danh mục bài viết (cache)
    ├── knowledge_base.json     # 38 bài viết thô từ WordPress API
    ├── processed_kb.json       # Dữ liệu sau tiền xử lý NLP
    ├── chunks.json             # 61 chunks (38 valid, 23 rỗng)
    ├── inverted_index.json     # Inverted index cho BM25
    ├── synonyms.json           # Bảng từ đồng nghĩa cho query expansion
    ├── auto_stopwords.json     # ~70 stopwords tự động học từ corpus
    ├── eval_dataset.json       # Tập đánh giá (33 cặp Q&A)
    └── eval_results.json       # Kết quả đánh giá chi tiết
```

---

## ⚙️ Cài đặt

### Yêu cầu

- Python 3.11+
- Google Gemini API Key ([lấy tại đây](https://makersuite.google.com/app/apikey))

### Cài thư viện

```bash
pip install fastapi uvicorn rank-bm25 underthesea \
            sentence-transformers rouge-score \
            google-generativeai requests beautifulsoup4 \
            python-dotenv
```

### Cấu hình

Tạo file `.env` trong thư mục gốc:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

---

## 🚀 Hướng dẫn sử dụng

### Chạy toàn bộ pipeline (khuyến nghị)

```bash
bash run_pipeline.sh
```

### Hoặc chạy từng bước thủ công

#### Bước 1 — Crawl dữ liệu từ WordPress API

```bash
python crawl_data.py
```

- Lần đầu: tự động crawl danh mục và lưu vào `categories.json`
- Để crawl lại danh mục: đặt `USE_SAVED_CATEGORY = False` trong file
- **Output:** `data/knowledge_base.json` — 38 bài viết, 15 danh mục

#### Bước 2 — Tiền xử lý NLP tiếng Việt

```bash
python preprocess_kb.py
```

- Loại bỏ HTML, chuẩn hóa văn bản, tách từ (Underthesea)
- Tự động học stopwords từ corpus (top 1% TF cao + IDF < 0.1)
- **Output:** `data/processed_kb.json`, `data/auto_stopwords.json`

#### Bước 3 — Chunking & xây dựng Inverted Index

```bash
python chunking_indexing.py
```

- Chia bài viết thành chunks theo đoạn văn (max 500 ký tự/chunk)
- **Output:** `data/chunks.json` (61 chunks), `data/inverted_index.json`

#### Bước 4 — Khởi động API Server

```bash
python -m uvicorn api:app --port 3000 --reload
```

- API docs tại: **http://localhost:3000/docs**

---

## 🔌 API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/chat` | Đặt câu hỏi, nhận câu trả lời + link bài |
| `GET`  | `/health` | Kiểm tra trạng thái server |

**Ví dụ request:**

```bash
curl -X POST http://localhost:3000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Phú Quốc có những điểm du lịch nào nổi tiếng?"}'
```

**Ví dụ response:**

```json
{
  "answer": "Phú Quốc nổi tiếng với nhiều điểm du lịch hấp dẫn như...",
  "sources": [
    {
      "title": "Top 10 điểm tham quan Phú Quốc",
      "link": "https://news.phuquocandyou.com/...",
      "post_id": 123
    }
  ]
}
```

---

## 📊 Thống kê dữ liệu thực tế

| Thành phần | Số liệu |
|---|---|
| Tổng bài viết | 38 bài |
| Số danh mục | 15 danh mục |
| Tổng chunks | 61 (38 valid, 23 rỗng) |
| Tập đánh giá | 33 cặp Q&A |
| Stopwords tự học | ~70 từ |
| Avg chunk size | ~1,549 ký tự |

**Phân bố danh mục:**

| Danh mục | Số bài |
|---|---|
| Du lịch | 10 |
| Tin tức | 9 |
| Kinh nghiệm | 7 |
| Văn hóa | 6 |
| Điểm đến | 6 |
| Ẩm thực | 4 |
| Khách sạn | 3 |
| Khác | 3 |

---

## 📈 Kết quả đánh giá

### Retrieval — BM25 + Query Expansion (33 câu hỏi)

| Metric | Baseline (BM25 thuần) | Sau cải thiện | Tăng |
|--------|----------------------|---------------|------|
| Precision@5 | 0.080 | 0.121 | +51% |
| Recall@5 | 0.400 | 0.606 | +52% |
| MRR | 0.338 | 0.461 | +36% |

> Cải thiện nhờ: **Query Expansion** + **lọc chunk rỗng** + **MIN_SCORE = 0.5**

### Generation — Gemini

> ⚠️ **Lưu ý:** Kết quả generation bị ảnh hưởng bởi **rate limit 429** của Gemini free tier trong quá trình đánh giá tự động. `eval_generation.py` đã được cập nhật với **retry tự động** để xử lý vấn đề này. Chạy lại để có kết quả đầy đủ trên 33 mẫu.

| Metric | Giá trị (1 mẫu thành công) |
|--------|---------------------------|
| ROUGE-L | 0.332 |
| Semantic Similarity | 0.716 |

---

## 🛠️ Công cụ & Thư viện

| Công cụ | Phiên bản | Mục đích |
|---------|-----------|----------|
| Python | 3.11 | Ngôn ngữ lập trình chính |
| FastAPI | 0.110+ | REST API server |
| rank_bm25 | 0.2.2 | Thuật toán BM25Okapi |
| Underthesea | 6.8+ | NLP tiếng Việt: tách từ |
| Google Gemini API | gemini-2.5-flash | Sinh câu trả lời + query expansion |
| sentence-transformers | latest | Semantic Similarity (đánh giá) |
| rouge-score | latest | ROUGE-L (đánh giá) |
| BeautifulSoup4 | 4.12+ | Xử lý và làm sạch HTML |
| WordPress REST API | v2 | Nguồn dữ liệu bài viết |

---

## 🧪 Chạy đánh giá

```bash
# Bước 0: Sinh tập đánh giá — chỉ chạy 1 lần (không cần chạy khi chưa có bài viết mới)
python auto_label.py

# Bước 1: Sinh bảng từ đồng nghĩa — chỉ chạy 1 lần (không cần chạy khi chưa có bài viết mới)
python build_synonyms.py

# Bước 2: Đánh giá retrieval
python eval_retrieval.py

# Bước 3: Đánh giá generation (có retry tự động khi rate limit)
python eval_generation.py

# Hoặc chạy cả retrieval + generation cùng lúc
python run_eval.py
```

---

## 🔧 Lưu ý kỹ thuật

- **Rate limit Gemini free tier:** ~15 req/min → các script tự động `sleep(4)` và retry khi gặp lỗi 429, đọc `retryDelay` từ response để chờ đúng thời gian
- **Cache BM25:** `search_cached` dùng `lru_cache(maxsize=200)` — tránh tính lại BM25 cho cùng một query
- **MIN_SCORE = 0.5:** Lọc chunk không liên quan, tránh đưa context nhiễu vào LLM
- **Chunk rỗng:** 23/61 chunks không có nội dung — đã lọc qua `valid_chunks` trong `api.py`
- **`synonyms.json` rỗng:** Nếu `build_synonyms.py` chưa chạy, `api.py` tự dùng fallback hardcode

---

## 📈 Hướng phát triển

- [ ] Mở rộng corpus từ 38 lên 500+ bài viết
- [ ] Áp dụng **Hybrid Search** (BM25 + Dense Retrieval với FAISS/Qdrant)
- [ ] Fine-tune embedding model cho tiếng Việt chuyên ngành du lịch Phú Quốc
- [ ] Deploy FastAPI lên VPS/cloud (hiện đang chạy local port 3000)
- [ ] Xây dựng giao diện người dùng thân thiện hơn

---

## 📚 Tài liệu tham khảo

1. S. Robertson & H. Zaragoza, *"The probabilistic relevance framework: BM25 and beyond"*, Foundations and Trends in IR, 2009.
2. P. Lewis et al., *"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"*, NeurIPS, 2020.
3. V. Karpukhin et al., *"Dense Passage Retrieval for Open-Domain QA"*, EMNLP, 2020.
4. T. Nguyen et al., *"Vietnamese QA System using BERT and BM25"*, IALP, 2021.
5. Y. Gao et al., *"RAG for Large Language Models: A Survey"*, arXiv:2312.10997, 2024.
6. Underthesea Team, *"Underthesea: Vietnamese NLP Toolkit"*, GitHub, 2024.