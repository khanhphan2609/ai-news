# 🤖 Auto Post WordPress

Tự động cào bài viết từ các trang báo và đăng lên WordPress.

---

## 📁 Cấu trúc thư mục
```
auto_post/
├── .env              # Thông tin xác thực (không commit lên Git)
├── sites.json        # Config selector cho từng trang báo
├── crawl.py          # Cào & làm sạch nội dung bài viết
├── media.py          # Tải & upload ảnh lên WordPress
├── post.py           # Đăng bài lên WordPress
├── main.py           # Chạy toàn bộ pipeline
├── requirements.txt  # Thư viện cần cài
└── data/
    ├── images/       # Ảnh tải về từ bài gốc
    └── *.json        # Dữ liệu bài viết đã cào
```

---

## 🔄 Luồng xử lý
```
sites.json
    │
    ▼
[crawl.py] ──── Cào danh sách URL từ chuyên mục
    │               │
    │               ▼
    │           Cào nội dung từng bài
    │           (title, content, thumbnail, category, tags)
    │               │
    │               ▼
    │           Lọc bài theo keyword (vd: "Phú Quốc")
    │               │
    │               ▼
    │           Làm sạch HTML (clean_content)
    │               │
    │               ▼
    │           Lưu ra data/*.json
    │
    ▼
[media.py] ──── Tải thumbnail về data/images/
    │               │
    │               ▼
    │           Upload thumbnail lên WordPress → lấy media_id
    │               │
    │               ▼
    │           Tìm tất cả <img> trong nội dung
    │               │
    │               ▼
    │           Tải từng ảnh về local
    │               │
    │               ▼
    │           Upload lên WordPress → thay URL cũ bằng URL mới
    │
    ▼
[post.py] ───── Get hoặc Create danh mục (category)
    │               │
    │               ▼
    │           Get hoặc Create tags
    │               │
    │               ▼
    │           Thêm "Cre: Tên báo" vào cuối nội dung
    │               │
    │               ▼
    │           Đăng bài lên WordPress REST API
    │           (title, content, thumbnail, category, tags)
    │
    ▼
WordPress ✅
```

---

## ⚙️ Cài đặt

### 1. Cài thư viện
```bash
pip install -r requirements.txt
```

`requirements.txt`:
```
requests
beautifulsoup4
python-dotenv
urllib3
```

### 2. Tạo file `.env`
```env
WP_URL=https://news.phuquocandyou.com
WP_USERNAME=your_username
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

> Tạo Application Password tại: **WP Admin → Users → Profile → Application Passwords**

### 3. Cấu hình `sites.json`

Mỗi trang báo định nghĩa CSS selector riêng:
```json
{
  "vnexpress": {
    "base_url": "https://vnexpress.net",
    "categories": {
      "du-lich": "https://vnexpress.net/du-lich",
      "thoi-su": "https://vnexpress.net/thoi-su"
    },
    "selectors": {
      "article_links": "h3.title-news a, h2.title-news a",
      "title": "h1.title-detail",
      "description": "p.description",
      "content": "article.fck_detail",
      "thumbnail": "meta[property='og:image']",
      "category": "ul.breadcrumb li:nth-child(2) a",
      "tags": "div.tags-news a",
      "date": "span.date",
      "remove": "div.box-tinlienquan, script, style"
    }
  }
}
```

> Để thêm trang báo mới, chỉ cần thêm 1 block vào `sites.json` — không cần chỉnh code.

---

## 🚀 Chạy
```bash
python main.py
```

Hoặc tùy chỉnh trong `main.py`:
```python
run(
    site_name="vnexpress",       # Key trong sites.json
    category_name="du-lich",     # None = cào tất cả chuyên mục
    max_articles=50,             # Số bài tối đa mỗi chuyên mục
    keywords=["Phú Quốc",        # Chỉ lấy bài có chứa keyword
              "Phu Quoc",
              "phú quốc"],
    status="draft",              # "draft" | "publish"
)
```

---

## 📋 Mô tả từng file

### `crawl.py`
- Đọc config từ `sites.json`
- Lấy danh sách URL bài viết từ trang chuyên mục
- Cào nội dung từng bài: tiêu đề, mô tả, HTML, ảnh, danh mục, tags, ngày
- Lọc bài theo keyword
- Làm sạch HTML: xóa thẻ rác, chuẩn hóa `<figure>`, xóa `class/style/data-*`
- Lưu kết quả ra `data/<site>_<category>_<timestamp>.json`

### `media.py`
- Tải ảnh thumbnail về `data/images/`
- Upload ảnh lên WordPress Media Library
- Quét toàn bộ `<img>` trong nội dung (xử lý cả lazy load `data-src`)
- Thay URL ảnh cũ bằng URL mới trên WordPress
- Xóa `srcset` để tránh trỏ về nguồn cũ

### `post.py`
- Tự động get hoặc create **danh mục** trên WordPress theo tên
- Tự động get hoặc create **tags** trên WordPress (viết HOA)
- Cache danh mục & tag để tránh gọi API lặp lại
- Thêm `Cre: Tên báo` có link về bài gốc vào cuối nội dung
- Đăng bài qua WordPress REST API

### `main.py`
- Điều phối toàn bộ pipeline: crawl → media → post
- Báo cáo số bài thành công / thất bại

---

## 🔒 Bảo mật

- Không commit file `.env` lên Git
- Thêm vào `.gitignore`:
```
.env
data/
```

---

## 📝 Ghi chú

- Dùng `status="draft"` để kiểm tra bài trước khi publish
- Tăng `max_articles` để có nhiều bài lọc keyword hơn
- Mỗi request cách nhau 1 giây để tránh bị block IP
- SSL verify tắt (`verify=False`) nếu cert hết hạn — nên gia hạn SSL sớm