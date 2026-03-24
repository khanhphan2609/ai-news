import time
from crawl import crawl_site
from media import process_thumbnail, replace_images_in_content
from post import create_post

SITE_INFO = {
    "vnexpress":  {"name": "VnExpress",  "url": "https://vnexpress.net"},
    "tuoitre":    {"name": "Tuổi Trẻ",   "url": "https://tuoitre.vn"},
    "thanhnien":  {"name": "Thanh Niên", "url": "https://thanhnien.vn"},
    "tienphong":  {"name": "Tiền Phong", "url": "https://tienphong.vn"},
    "cafef":      {"name": "CafeF",      "url": "https://cafef.vn"},
    "dantri":     {"name": "Dân Trí",    "url": "https://dantri.com.vn"},
    "znews":      {"name": "Zing News",  "url": "https://znews.vn"},
}

KEYWORDS = ["Phú Quốc", "Phu Quoc", "phú quốc"]


def run(site_name, category_name=None, max_articles=50, keywords=None, status="publish", max_results=None):
    print(f"\n{'='*60}")
    print(f"🤖 Pipeline: {site_name}" + (f" / {category_name}" if category_name else ""))
    if max_results:
        print(f"🎯 Dừng sau khi đăng thành công: {max_results} bài")
    print(f"{'='*60}")

    articles = crawl_site(
        site_name=site_name,
        category_name=category_name,
        max_articles=max_articles,
        keywords=keywords,
    )

    if not articles:
        print("⚠️  Không có bài nào phù hợp")
        return 0

    site_info = SITE_INFO.get(site_name, {"name": site_name, "url": ""})
    success, failed = 0, 0

    for i, article in enumerate(articles, 1):
        if max_results and success >= max_results:
            print(f"\n🎯 Đã đăng đủ {max_results} bài, dừng lại!")
            break

        print(f"\n📌 [{i}/{len(articles)}] {article['title']}")
        print(f"  📂 Category: {article.get('category')}")
        print(f"  🏷️  Tags: {article.get('tags')}")

        # Bước 1: Upload thumbnail
        media_id = None
        if article.get("thumbnail"):
            print(f"  🖼️  Xử lý thumbnail...")
            media_id = process_thumbnail(article["thumbnail"], article["title"])

        # Bước 2: Thay ảnh trong nội dung
        print(f"  📝 Xử lý ảnh trong nội dung...")
        content_html = replace_images_in_content(article["content_html"])

        # Bước 3: Đăng bài
        post = create_post(
            title=article["title"],
            content_html=content_html,
            source_name=site_info["name"],
            source_url=article["url"],
            featured_media_id=media_id,
            category=article.get("category", ""),
            tags=article.get("tags", []),
            status=status,
        )

        if post:
            success += 1
        else:
            failed += 1

        time.sleep(1)

    print(f"\n{'='*60}")
    print(f"✅ Thành công: {success} | ❌ Thất bại: {failed}")
    print(f"{'='*60}")
    return success


def main():
    # ─── CẤU HÌNH CHẠY ────────────────────────────────────────
    STATUS      = "draft"   # "draft" để kiểm tra, "publish" để đăng thật
    MAX_RESULTS = 20         # Dừng sau N bài thành công (None = không giới hạn)
    MAX_ARTICLES = 50       # Số bài tối đa cào mỗi chuyên mục
    # ──────────────────────────────────────────────────────────

    # Danh sách các site + chuyên mục sẽ chạy
    # Format: (site_name, category_name)  — None = cào tất cả chuyên mục
    CRAWL_TARGETS = [
        ("vnexpress",  "du-lich"),
        ("vnexpress",  "kinh-doanh"),
        ("tuoitre",    "du-lich"),
        ("thanhnien",  "du-lich"),
        ("thanhnien",  "kinh-te"),
        ("tienphong",  "du-lich"),
        ("cafef",      "bat-dong-san"),
    ]

    total_success = 0
    for site_name, category_name in CRAWL_TARGETS:
        success = run(
            site_name=site_name,
            category_name=category_name,
            max_articles=MAX_ARTICLES,
            keywords=KEYWORDS,
            status=STATUS,
            max_results=MAX_RESULTS,
        )
        total_success += success
        time.sleep(2)  # Nghỉ giữa các site

    print(f"\n{'='*60}")
    print(f"🏁 TỔNG KẾT: Đã đăng {total_success} bài")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()