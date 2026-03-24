import requests
from requests.auth import HTTPBasicAuth
import os
import urllib3
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

WP_URL = os.getenv("WP_URL")
USERNAME = os.getenv("WP_USERNAME")
APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
auth = HTTPBasicAuth(USERNAME, APP_PASSWORD)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}


def download_image(url, save_dir="data/images"):
    """Tải ảnh về local"""
    os.makedirs(save_dir, exist_ok=True)

    filename = url.split("/")[-1].split("?")[0]
    if "." not in filename:
        filename += ".jpg"
    filepath = os.path.join(save_dir, filename)

    if os.path.exists(filepath):
        print(f"    📁 Ảnh đã tồn tại: {filename}")
        return filepath

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"    ⬇️  Tải ảnh: {filename}")
            return filepath
        else:
            print(f"    ❌ Không tải được ảnh ({response.status_code}): {url}")
            return None
    except Exception as e:
        print(f"    ❌ Lỗi tải ảnh: {e}")
        return None


def upload_image_to_wp(filepath, alt_text=""):
    """Upload ảnh lên WordPress, trả về (media_id, media_url)"""
    if not filepath or not os.path.exists(filepath):
        return None, None

    filename = os.path.basename(filepath)
    ext = filename.rsplit(".", 1)[-1].lower()
    content_types = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png",  "gif": "image/gif",
        "webp": "image/webp",
    }
    content_type = content_types.get(ext, "image/jpeg")

    try:
        with open(filepath, "rb") as img:
            response = requests.post(
                f"{WP_URL}/wp-json/wp/v2/media",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Content-Type": content_type,
                },
                data=img,
                auth=auth,
                verify=False,
            )

        if response.status_code == 201:
            media = response.json()
            media_url = media["source_url"]
            if alt_text:
                requests.post(
                    f"{WP_URL}/wp-json/wp/v2/media/{media['id']}",
                    json={"alt_text": alt_text},
                    auth=auth,
                    verify=False,
                )
            print(f"    ☁️  Upload OK: {filename} → {media_url}")
            return media["id"], media_url
        else:
            print(f"    ❌ Lỗi upload: {response.status_code}")
            return None, None
    except Exception as e:
        print(f"    ❌ Lỗi upload: {e}")
        return None, None


def process_thumbnail(thumbnail_url, alt_text=""):
    """Download + Upload ảnh thumbnail, trả về WP media ID"""
    if not thumbnail_url:
        return None
    filepath = download_image(thumbnail_url)
    if filepath:
        media_id, _ = upload_image_to_wp(filepath, alt_text)
        return media_id
    return None


def replace_images_in_content(content_html):
    """
    Tìm tất cả ảnh trong nội dung HTML,
    tải về + upload lên WP, thay URL cũ bằng URL mới
    """
    soup = BeautifulSoup(content_html, "html.parser")
    imgs = soup.find_all("img")

    if not imgs:
        return content_html

    print(f"  🖼️  Tìm thấy {len(imgs)} ảnh trong nội dung")

    for img in imgs:
        # Lấy URL ảnh — ưu tiên data-src (lazy load) rồi mới src
        original_url = img.get("data-src") or img.get("src", "")

        if not original_url or not original_url.startswith("http"):
            continue

        alt = img.get("alt", "")
        filepath = download_image(original_url)

        if filepath:
            _, new_url = upload_image_to_wp(filepath, alt)
            if new_url:
                # Thay src và data-src bằng URL mới
                img["src"] = new_url
                if img.get("data-src"):
                    img["data-src"] = new_url
                # Xóa srcset để tránh trỏ về URL cũ
                if img.get("srcset"):
                    del img["srcset"]
                if img.get("data-srcset"):
                    del img["data-srcset"]

    return str(soup)