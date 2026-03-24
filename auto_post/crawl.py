import requests
from bs4 import BeautifulSoup, Comment
import time
import json
import re
import os
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

KEYWORD_TAG_MAP = {
    "phú quốc":         "PHÚ QUỐC",
    "phu quoc":         "PHÚ QUỐC",
    "du lịch":          "DU LỊCH",
    "khách sạn":        "KHÁCH SẠN",
    "resort":           "RESORT",
    "biển":             "BIỂN ĐẢO",
    "đảo":              "BIỂN ĐẢO",
    "hàng không":       "HÀNG KHÔNG",
    "máy bay":          "HÀNG KHÔNG",
    "sân bay":          "SÂN BAY",
    "bất động sản":     "BẤT ĐỘNG SẢN",
    "đầu tư":           "ĐẦU TƯ",
    "kinh tế":          "KINH TẾ",
    "ẩm thực":          "ẨM THỰC",
    "nhà hàng":         "ẨM THỰC",
    "lễ hội":           "LỄ HỘI",
    "vinpearl":         "VINPEARL",
    "sun world":        "SUN WORLD",
    "cáp treo":         "CÁP TREO",
    "san hô":           "LẶN BIỂN",
    "lặn biển":         "LẶN BIỂN",
    "câu cá":           "CÂU CÁ",
    "giá vé":           "GIÁ VÉ",
    "phụ thu":          "HÀNG KHÔNG",
    "nhiên liệu":       "NĂNG LƯỢNG",
    "thời sự":          "THỜI SỰ",
    "kinh doanh":       "KINH DOANH",
    "doanh nghiệp":     "DOANH NGHIỆP",
    "du khách":         "DU KHÁCH",
    "tour":             "TOUR DU LỊCH",
    "giao thông":       "GIAO THÔNG",
}


def load_sites_config(config_path="sites.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_relevant(article, keywords):
    if not keywords:
        return True
    text = " ".join([
        article.get("title", ""),
        article.get("description", ""),
        article.get("content_text", ""),
        " ".join(article.get("tags", [])),
    ]).lower()
    return any(kw.lower() in text for kw in keywords)


def extract_tags_from_js(html):
    """Lấy tags từ JavaScript (dành cho VnExpress, Tuổi Trẻ...)"""
    # Cách 1: articleTags trong dataLayer
    match = re.search(r"'articleTags'\s*:\s*'([^']+)'", html)
    if match:
        tags_raw = match.group(1)
        tags = [t.strip() for t in tags_raw.split(';') if t.strip()]
        if tags:
            return tags

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
            return result
        except:
            pass

    return []


def extract_tags_from_content(article):
    """Tự động sinh tags từ nội dung bài viết dựa trên KEYWORD_TAG_MAP"""
    text = " ".join([
        article.get("title", ""),
        article.get("description", ""),
        article.get("content_text", ""),
    ]).lower()

    tags = set()
    for keyword, tag in KEYWORD_TAG_MAP.items():
        if keyword.lower() in text:
            tags.add(tag)

    result = sorted(list(tags))
    if result:
        print(f"     🏷️  Tags tự sinh: {result}")
    return result


def get_article_urls(category_url, selector, base_url, max_articles=10):
    response = requests.get(category_url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    urls = []
    for a in soup.select(selector):
        href = a.get("href", "")
        if href.startswith("http"):
            full_url = href
        elif href.startswith("/"):
            full_url = base_url.rstrip("/") + href
        else:
            continue
        if full_url not in urls:
            urls.append(full_url)
        if len(urls) >= max_articles:
            break

    print(f"🔍 Tìm thấy {len(urls)} bài viết")
    return urls


def clean_content(content_html):
    """Làm sạch HTML về format chuẩn"""
    soup = BeautifulSoup(content_html, "html.parser")

    # 1. Xóa comment HTML
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # 2. Xóa thẻ rác
    REMOVE_SELECTORS = [
        "script", "style", "source", "picture", "meta",
        "span#article-end", "[data-component]",
        "div.box-tinlienquan", "div.relate-news",
    ]
    for selector in REMOVE_SELECTORS:
        for tag in soup.select(selector):
            tag.decompose()

    # 3. Chuẩn hóa <figure>
    for figure in soup.find_all("figure"):
        img_tag = figure.find("img")
        caption_tag = figure.find("figcaption")

        img_url = ""
        img_alt = ""
        if img_tag:
            img_url = img_tag.get("data-src") or img_tag.get("src", "")
            img_alt = img_tag.get("alt", "")

        caption_text = ""
        if caption_tag:
            caption_text = caption_tag.get_text(strip=True)

        new_figure = soup.new_tag("figure")
        if img_url:
            new_img = soup.new_tag("img", src=img_url, alt=img_alt)
            new_figure.append(new_img)
        if caption_text:
            new_caption = soup.new_tag("figcaption")
            new_caption.string = caption_text
            new_figure.append(new_caption)

        figure.replace_with(new_figure)

    # 4. Xóa attr không cần thiết
    ALLOWED_ATTRS = {"href", "src", "alt", "target", "rel"}
    for tag in soup.find_all(True):
        attrs_to_remove = [k for k in tag.attrs if k not in ALLOWED_ATTRS]
        for attr in attrs_to_remove:
            del tag[attr]

    # 5. Unwrap <div> và <span>
    for div in soup.find_all("div"):
        div.unwrap()
    for span in soup.find_all("span"):
        span.unwrap()

    # 6. Xóa <p> rỗng
    for p in soup.find_all("p"):
        if not p.get_text(strip=True) and not p.find("img"):
            p.decompose()

    # 7. Chuẩn hóa <a>
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if href.startswith("http"):
            a["target"] = "_blank"
            a["rel"] = "nofollow"

    return str(soup)


def crawl_article(url, selectors, use_js_tags=False):
    """Cào nội dung chi tiết 1 bài viết"""
    response = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    def get_text(selector):
        tag = soup.select_one(selector) if selector else None
        return tag.get_text(strip=True) if tag else ""

    def get_attr(selector, attr):
        tag = soup.select_one(selector) if selector else None
        return tag.get(attr, "") if tag else ""

    def get_list(selector):
        return [t.get_text(strip=True) for t in soup.select(selector)] if selector else []

    content_html = ""
    content_text = ""
    content_tag = soup.select_one(selectors.get("content", ""))
    if content_tag:
        for tag in content_tag.select(selectors.get("remove", "")):
            tag.decompose()
        content_html = clean_content(str(content_tag))
        content_text = BeautifulSoup(content_html, "html.parser").get_text(separator="\n", strip=True)

    # Lấy tags
    if use_js_tags:
        tags = extract_tags_from_js(response.text)
    else:
        tags = get_list(selectors.get("tags", ""))

    return {
        "url": url,
        "title": get_text(selectors.get("title")),
        "description": get_text(selectors.get("description")),
        "content_html": content_html,
        "content_text": content_text,
        "thumbnail": get_attr(selectors.get("thumbnail"), "content"),
        "category": get_text(selectors.get("category")),
        "tags": tags,
        "date": get_text(selectors.get("date")),
    }


def save_to_json(articles, site_name, category_name):
    os.makedirs("data", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"data/{site_name}_{category_name}_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"💾 Đã lưu {len(articles)} bài → {filename}")
    return filename


def crawl_site(site_name, category_name=None, max_articles=50, keywords=None, config_path="sites.json"):
    config = load_sites_config(config_path)

    if site_name not in config:
        print(f"❌ Không tìm thấy site '{site_name}' trong config")
        return []

    site = config[site_name]
    selectors = site["selectors"]
    base_url = site["base_url"]
    categories = site["categories"]
    use_js_tags = site.get("tags_js", False)

    targets = {category_name: categories[category_name]} if category_name else categories

    all_articles = []
    for cat_name, cat_url in targets.items():
        print(f"\n🚀 [{site_name}] Đang cào: {cat_name} → {cat_url}")
        if keywords:
            print(f"🔎 Lọc theo từ khóa: {', '.join(keywords)}")

        urls = get_article_urls(cat_url, selectors["article_links"], base_url, max_articles)

        articles = []
        skipped = 0
        for i, url in enumerate(urls, 1):
            print(f"  📰 [{i}/{len(urls)}] {url}")
            try:
                article = crawl_article(url, selectors, use_js_tags)

                # Tự động sinh tags nếu không có
                if not article["tags"]:
                    article["tags"] = extract_tags_from_content(article)

                if is_relevant(article, keywords):
                    articles.append(article)
                    print(f"     ✅ {article['title']}")
                    if article["tags"]:
                        print(f"     🏷️  Tags: {article['tags']}")
                else:
                    skipped += 1
                    print(f"     ⏭️  Bỏ qua (không liên quan)")
            except Exception as e:
                print(f"     ❌ Lỗi: {e}")
            time.sleep(1)

        print(f"\n📊 Kết quả: {len(articles)} bài liên quan / {skipped} bỏ qua")
        if articles:
            save_to_json(articles, site_name, cat_name)
        all_articles.extend(articles)

    return all_articles


def main():
    keywords = ["Phú Quốc", "Phu Quoc", "phú quốc"]

    crawl_site(
        site_name="vnexpress",
        max_articles=50,
        keywords=keywords,
    )

    # crawl_site("tuoitre", max_articles=50, keywords=keywords)


if __name__ == "__main__":
    main()