# crawl_data.py
import requests
import json
import time
import os


# =============================
# CONFIG
# =============================

BASE_URL = "https://news.phuquocandyou.com"
OUTPUT_FILE = "data/knowledge_base.json"

# True  -> dùng file categories.json
# False -> crawl category lại từ API
USE_SAVED_CATEGORY = False


class WordPressCrawler:
    def __init__(self, base_url):
        self.base_post_url = f"{base_url}/wp-json/wp/v2/posts"
        self.base_cat_url = f"{base_url}/wp-json/wp/v2/categories"
        self.per_page = 100
        self.category_file = "data/categories.json"
        self.categories = {}

    # -------------------------
    # Crawl category từ API
    # -------------------------
    def fetch_categories_from_api(self):

        print("Đang crawl category từ API...")

        page = 1

        while True:

            res = requests.get(
                self.base_cat_url,
                params={
                    "per_page": self.per_page,
                    "page": page
                }
            )

            if res.status_code != 200:
                print("Lỗi khi lấy category")
                break

            data = res.json()

            if not data:
                break

            for cat in data:
                self.categories[cat["id"]] = cat["name"]

            page += 1

        self.save_categories()

        print(f"Đã lưu {len(self.categories)} category vào categories.json")

    # -------------------------
    # Lưu category
    # -------------------------
    def save_categories(self):

        with open(self.category_file, "w", encoding="utf-8") as f:
            json.dump(self.categories, f, ensure_ascii=False, indent=2)

    # -------------------------
    # Load category
    # -------------------------
    def load_categories(self):

        global USE_SAVED_CATEGORY

        if USE_SAVED_CATEGORY and os.path.exists(self.category_file):

            print("Load category từ file...")

            with open(self.category_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # convert key string -> int
            self.categories = {int(k): v for k, v in data.items()}

            print(f"Loaded {len(self.categories)} categories")

        else:

            print("Không tìm thấy category file hoặc đang bật crawl lại")

            self.fetch_categories_from_api()

    # -------------------------
    # Crawl posts
    # -------------------------
    def fetch_posts(self):

        self.load_categories()

        all_posts = []
        page = 1

        while True:

            print(f"Đang lấy page {page}...")

            res = requests.get(
                self.base_post_url,
                params={
                    "status": "publish",
                    "per_page": self.per_page,
                    "page": page
                }
            )

            if res.status_code != 200:
                print("Dừng tại page", page)
                break

            posts = res.json()

            if not posts:
                break

            for post in posts:

                cat_names = [
                    self.categories.get(cid, "Unknown")
                    for cid in post["categories"]
                ]

                data = {
                    "id": post["id"],
                    "title": post["title"]["rendered"],
                    "slug": post["slug"],
                    "link": post["link"],
                    "category": cat_names,
                    "content": post["content"]["rendered"],
                    "published_date": post["date"],
                    "modified_date": post["modified"]
                }

                all_posts.append(data)

            page += 1
            time.sleep(0.3)

        return all_posts

    # -------------------------
    # Save JSON
    # -------------------------
    def save_posts(self, posts):

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)

        print(f"Đã lưu {len(posts)} bài viết vào {OUTPUT_FILE}")


# =============================
# RUN
# =============================
def main():
    crawler = WordPressCrawler(BASE_URL)
    posts = crawler.fetch_posts()
    crawler.save_posts(posts)

if __name__ == "__main__":
    main()