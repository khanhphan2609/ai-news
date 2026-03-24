import requests
from bs4 import BeautifulSoup
import re
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

SELECTORS_TO_TEST = {
    "title": [
        "h1.title-detail", "h1.article-title", "h1.title-page", "h1.detail-title",
        "h1.article__title", "h1.cms-title", "h1.post-title", "h1.entry-title",
        "h1.headline", "h1.title", "h1.article-title--detail",
        "h1.singular-title", "h1.news-title", "h1",
    ],
    "description": [
        "p.description", "div.sapo", "div.singular-sapo", "p.sapo", "h2.detail-sapo",
        "p.article__sapo", "div.article__sapo", "p.cms-desc", "div.post-excerpt",
        "p.lead", "div.lead", "p.intro", "div.intro",
        # Thêm mới
        "div.singular-sapo", "p.article-sapo", "div.article-sapo",
        "h2.article__sapo", "p.news-sapo", "div.news-sapo",
        "div.article__excerpt", "p.excerpt",
        "p[class*='sapo']", "div[class*='sapo']", "p[class*='lead']",
    ],
    "content": [
        "article.fck_detail", "div#main-detail-body", "div.singular-content",
        "div.detail-content", "div.article__body", "div.cms-body", "div.post-content",
        "div.entry-content", "div.content-detail", "div#article-body",
        "div.article-content", "div.news-content",
        # Thêm mới
        "div.singular-content", "div.article__content", "section.article__body",
        "div[class*='article-body']", "div[class*='article-content']",
        "div.body-content", "div.main-content", "div#content-body",
        "div.maincontent", "div.article__detail",
    ],
    "category": [
        "ul.breadcrumb li:nth-child(2) a", "nav.detail-cate a",
        "div.breadcrumb a:nth-child(2)", "div.detail-cate a",
        "a.category-name", "span.category", "div.article__category a",
        "div.cms-category a", "nav.breadcrumb a:nth-child(2)",
        "ol.breadcrumb li:nth-child(2) a", "div.tag-category a",
        # Thêm mới
        "div.article__zone a", "span.article__zone a",
        "a.article__category", "div.breadcrumbs a:nth-child(2)",
        "nav.breadcrumbs li:nth-child(2) a", "div.zone-name a",
        "span.zone a", "div.cat-name a", "a.cat-link",
        "div[class*='category'] a", "span[class*='category'] a",
        "meta[property='article:section']",
    ],
    "tags": [
        "div.tags-news a", "ul.tags-news a", "div.tag-news a", "div.detail-tab a",
        "div.article__tags a", "ul.article-tags a", "div.cms-tags a",
        "div.post-tags a", "div.tags a", "ul.tags a", "div.tag-list a",
        "div.entry-tags a", "div.keyword a", "ul.keywords a",
        # Thêm mới
        "div.article__keyword a", "ul.article__keyword a",
        "div.news-tags a", "div.tag-box a", "ul.tag-box a",
        "div[class*='tags'] a", "ul[class*='tags'] a",
        "div[class*='keyword'] a", "ul[class*='keyword'] a",
    ],
    "date": [
        "span.date", "div.date-time", "time.author-time", "span.time-main",
        "div[data-role='publishdate']", "time.article__time", "span.cms-date",
        "span.post-date", "div.publish-date", "time[datetime]",
        "span.created-date", "div.article-date",
        # Thêm mới
        "span.article__time", "div.article__time",
        "span[class*='date']", "div[class*='date']", "time[class*='date']",
        "span.time", "div.time", "span.pubdate", "div.pubdate",
        "meta[property='article:published_time']",
        "span.article-date", "p.article-date",
    ],
    "article_links": [
        "h3.title-news a", "h2.title-news a",
        "h3.title-name a", "a.title-name",
        "h3.article-title a", "h2.article-title a",
        "h3.cms-title a", "h2.cms-title a",
        "h3.post-title a", "h2.post-title a",
        "article h3 a", "article h2 a",
        "div.item-title a", "div.news-title a",
        # Thêm mới
        "h3.article__title a", "h2.article__title a",
        "h3[class*='title'] a", "h2[class*='title'] a",
        "div[class*='title'] h3 a", "div[class*='title'] h2 a",
        "li.article-item h3 a", "li.news-item h3 a",
        "div.item h3 a", "div.news-item h3 a",
        "h3.item__title a", "h2.item__title a",
    ],
    "thumbnail": [
        "meta[property='og:image']",
        "meta[name='thumbnail']",
        "meta[itemprop='image']",
    ],
}


def extract_tags_from_js(html):
    """Lấy tags từ JavaScript"""
    # Cách 1: articleTags trong dataLayer
    match = re.search(r"'articleTags'\s*:\s*'([^']+)'", html)
    if match:
        tags_raw = match.group(1)
        tags = [t.strip() for t in tags_raw.split(';') if t.strip()]
        if tags:
            return tags, "dataLayer['articleTags']"

    # Cách 2: tagparam array
    match = re.search(r'var tagparam\s*=\s*(\[.*?\])', html)
    if match:
        try:
            tags_raw = json.loads(match.group(1))
            seen = set()
            result = []
            for t in tags_raw:
                clean = t.replace('_', ' ')
                if clean.lower() not in seen:
                    seen.add(clean.lower())
                    result.append(clean)
            if result:
                return result, "JS tagparam"
        except:
            pass

    # Cách 3: keywords meta tag
    match = re.search(r'<meta[^>]+name=["\']keywords["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if not match:
        match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']keywords["\']', html, re.IGNORECASE)
    if match:
        tags = [t.strip() for t in match.group(1).split(',') if t.strip()]
        if tags:
            return tags, "meta[keywords]"

    # Cách 4: article:tag meta
    matches = re.findall(r'<meta[^>]+property=["\']article:tag["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if matches:
        return matches, "meta[article:tag]"

    return [], ""


def find_selectors(url):
    print(f"\n🔍 Đang test: {url}\n")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        print(f"  ❌ Không thể kết nối: {e}\n")
        return

    results = {}

    for field, selectors in SELECTORS_TO_TEST.items():
        print(f"  [{field}]")

        # Tags: thử JS trước
        if field == "tags":
            tags, source = extract_tags_from_js(html)
            if tags:
                print(f"    ✅ '{source}' → {tags[:5]}")
                results[field] = f"__js__{source}"
            else:
                found = False
                for selector in selectors:
                    items = soup.select(selector)
                    if items:
                        value = [t.get_text(strip=True) for t in items[:5]]
                        print(f"    ✅ '{selector}' → {value}")
                        if not found:
                            results[field] = selector
                            found = True
                    else:
                        print(f"    ❌ '{selector}'")
                if not found:
                    print(f"    ⚠️  Không tìm thấy selector nào cho [{field}]")
            print()
            continue

        # Thumbnail: lấy attr content
        if field == "thumbnail":
            for selector in selectors:
                tag = soup.select_one(selector)
                if tag and tag.get("content"):
                    print(f"    ✅ '{selector}' → {tag['content'][:80]}...")
                    results[field] = selector
                    break
                else:
                    print(f"    ❌ '{selector}'")
            print()
            continue

        # Category: thử meta nếu không có CSS selector
        if field == "category":
            found = False
            for selector in selectors:
                if selector.startswith("meta"):
                    tag = soup.select_one(selector)
                    if tag and tag.get("content"):
                        value = tag["content"]
                        print(f"    ✅ '{selector}' → [{value}]")
                        if not found:
                            results[field] = selector
                            found = True
                    else:
                        print(f"    ❌ '{selector}'")
                else:
                    items = soup.select(selector)
                    if items:
                        value = [t.get_text(strip=True)[:80] for t in items[:3]]
                        print(f"    ✅ '{selector}' → {value}")
                        if not found:
                            results[field] = selector
                            found = True
                    else:
                        print(f"    ❌ '{selector}'")
            if not found:
                print(f"    ⚠️  Không tìm thấy selector nào cho [{field}]")
            print()
            continue

        # Date: thử meta nếu không có CSS selector
        if field == "date":
            found = False
            for selector in selectors:
                if selector.startswith("meta"):
                    tag = soup.select_one(selector)
                    if tag and tag.get("content"):
                        value = tag["content"]
                        print(f"    ✅ '{selector}' → [{value}]")
                        if not found:
                            results[field] = selector
                            found = True
                    else:
                        print(f"    ❌ '{selector}'")
                else:
                    items = soup.select(selector)
                    if items:
                        value = [t.get_text(strip=True)[:80] for t in items[:3]]
                        print(f"    ✅ '{selector}' → {value}")
                        if not found:
                            results[field] = selector
                            found = True
                    else:
                        print(f"    ❌ '{selector}'")
            if not found:
                print(f"    ⚠️  Không tìm thấy selector nào cho [{field}]")
            print()
            continue

        found = False
        for selector in selectors:
            items = soup.select(selector)
            if items:
                value = [t.get_text(strip=True)[:80] for t in items[:3]]
                print(f"    ✅ '{selector}' → {value}")
                if not found:
                    results[field] = selector
                    found = True
            else:
                print(f"    ❌ '{selector}'")
        if not found:
            print(f"    ⚠️  Không tìm thấy selector nào cho [{field}]")
        print()

    print("─" * 50)
    print("📋 Kết quả gợi ý cho sites.json:\n")
    for field, selector in results.items():
        if selector.startswith("__js__"):
            print(f'  "{field}": "",  ← tags_js: true')
        else:
            print(f'  "{field}": "{selector}",')
    print()


def dump_html(url, output="debug.html"):
    soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, "html.parser")
    with open(output, "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    print(f"💾 Đã lưu HTML → {output}")


if __name__ == "__main__":
    URLS_TO_TEST = [
        # Đã có config — kiểm tra lại
        # ("VnExpress",   "https://vnexpress.net/nhieu-hang-hang-khong-quoc-te-den-viet-nam-tang-gia-ve-phu-thu-nhien-lieu-5053138.html"),
        # ("Tuổi Trẻ",    "https://tuoitre.vn/xem-hai-quan-viet-nam-trung-quoc-lan-dau-ban-dan-that-chong-cuop-bien-20260322210846559.htm"),
        # ("Thanh Niên",  "https://thanhnien.vn/tinh-hinh-iran-trung-dong-moi-nhat-sang-223-185260321210653576.htm"),
        ("Tiền Phong",  "https://tienphong.vn/ly-do-thai-lan-tuyen-bo-mien-thi-thuc-30-ngay-la-du-post1829370.tpo"),

        # Thiếu selector — thêm URL mới để test lại
        ("Dân Trí",     "https://dantri.com.vn/the-gioi/iran-canh-bao-pha-huy-toan-bo-ha-tang-nang-luong-dau-mo-trung-dong-20260322210621342.htm"),
        ("Dân Trí 2",   "https://dantri.com.vn/du-lich/kham-pha-phu-quoc-diem-den-ly-tuong-cho-ky-nghi-he-20240601070000000.htm"),
        ("Zing News",   "https://znews.vn/vu-minh-khang-va-tai-xe-grab-tra-gia-vi-lo-hong-du-lieu-post1637050.html"),
        ("Zing News 2", "https://znews.vn/du-lich-phu-quoc-post1620000.html"),
        ("CafeF",       "https://cafef.vn/cuu-chu-tich-trinh-van-quyet-tai-xuat-flc-group-bat-ngo-tuyen-800-moi-gioi-bat-dong-san-muc-luong-tu-12-trieu-dong-thang-tro-len-18826032207084867.chn"),
        ("CafeF 2",     "https://cafef.vn/bat-dong-san/phu-quoc-bat-dong-san.chn"),
        ("VnEconomy",   "https://vneconomy.vn/giu-vai-tro-mo-duong-cong-binh-phai-tinh-gon-manh.htm"),
        ("VnEconomy 2", "https://vneconomy.vn/bat-dong-san/phu-quoc.htm"),
        ("Lao Động",    "https://laodong.vn/du-lich/tin-tuc/vuon-quoc-gia-xuan-thuy-don-nhan-danh-hieu-vuon-di-san-asean-1673071.html"),
        ("Lao Động 2",  "https://laodong.vn/du-lich"),
    ]

    for name, url in URLS_TO_TEST:
        print(f"\n{'='*60}")
        print(f"📰 {name}")
        print(f"{'='*60}")
        find_selectors(url)