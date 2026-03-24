import requests
from requests.auth import HTTPBasicAuth
import os
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

WP_URL = os.getenv("WP_URL")
USERNAME = os.getenv("WP_USERNAME")
APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
auth = HTTPBasicAuth(USERNAME, APP_PASSWORD)

# Cache tránh gọi API lặp lại
_category_cache = {}
_tag_cache = {}


def get_or_create_category(name):
    """Lấy ID danh mục theo tên, nếu chưa có thì tạo mới"""
    if not name:
        return None
    name = name.strip()
    if name in _category_cache:
        return _category_cache[name]

    # Tìm category đã có
    response = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories",
        params={"search": name, "per_page": 10},
        auth=auth,
        verify=False,
    )
    if response.status_code == 200:
        for cat in response.json():
            if cat["name"].lower() == name.lower():
                _category_cache[name] = cat["id"]
                print(f"  📂 Danh mục tìm thấy: {name} (ID: {cat['id']})")
                return cat["id"]

    # Chưa có → tạo mới
    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/categories",
        json={"name": name},
        auth=auth,
        verify=False,
    )
    if response.status_code == 201:
        cat_id = response.json()["id"]
        _category_cache[name] = cat_id
        print(f"  📂 Danh mục tạo mới: {name} (ID: {cat_id})")
        return cat_id

    print(f"  ❌ Lỗi tạo danh mục '{name}': {response.text}")
    return None


def get_or_create_tag(name):
    """Lấy ID tag theo tên, nếu chưa có thì tạo mới"""
    if not name:
        return None
    name = name.strip().upper()  # Tag viết HOA theo format trong ảnh
    if name in _tag_cache:
        return _tag_cache[name]

    # Tìm tag đã có
    response = requests.get(
        f"{WP_URL}/wp-json/wp/v2/tags",
        params={"search": name, "per_page": 10},
        auth=auth,
        verify=False,
    )
    if response.status_code == 200:
        for tag in response.json():
            if tag["name"].upper() == name.upper():
                _tag_cache[name] = tag["id"]
                return tag["id"]

    # Chưa có → tạo mới
    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/tags",
        json={"name": name},
        auth=auth,
        verify=False,
    )
    if response.status_code == 201:
        tag_id = response.json()["id"]
        _tag_cache[name] = tag_id
        print(f"  🏷️  Tag tạo mới: {name} (ID: {tag_id})")
        return tag_id

    print(f"  ❌ Lỗi tạo tag '{name}': {response.text}")
    return None


def build_content(content_html, source_name, source_url):
    """Thêm dòng Cre vào cuối nội dung"""
    cre = (
        f'<p style="text-align:right">'
        f'<em>Cre: <a href="{source_url}" target="_blank" rel="nofollow">{source_name}</a></em>'
        f'</p>'
    )
    return content_html + cre


def create_post(title, content_html, source_name, source_url,
                featured_media_id=None, category=None, tags=None, status="publish"):
    """
    Tạo bài viết với:
    - Ảnh đại diện
    - Danh mục (tự động get/create)
    - Tags (tự động get/create, viết HOA)
    - Cre ở cuối bài
    """
    endpoint = f"{WP_URL}/wp-json/wp/v2/posts"
    content = build_content(content_html, source_name, source_url)

    # Xử lý danh mục
    # category có thể là "Du lịch, Điểm đến" → tách ra
    category_ids = []
    if category:
        for cat_name in category.split(","):
            cat_id = get_or_create_category(cat_name.strip())
            if cat_id:
                category_ids.append(cat_id)

    # Xử lý tags
    tag_ids = []
    if tags:
        for tag_name in tags:
            tag_id = get_or_create_tag(tag_name.strip())
            if tag_id:
                tag_ids.append(tag_id)

    data = {
        "title": title,
        "content": content,
        "status": status,
    }
    if featured_media_id:
        data["featured_media"] = featured_media_id
    if category_ids:
        data["categories"] = category_ids
    if tag_ids:
        data["tags"] = tag_ids

    response = requests.post(endpoint, json=data, auth=auth, verify=False)
    if response.status_code == 201:
        post = response.json()
        print(f"  ✅ Đăng thành công: {post['link']} (ID: {post['id']})")
        return post
    else:
        print(f"  ❌ Lỗi đăng {response.status_code}: {response.text}")
        return None


def delete_post(post_id, force=True):
    endpoint = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
    response = requests.delete(endpoint, params={"force": force}, auth=auth, verify=False)
    if response.status_code == 200:
        print(f"✅ Xóa thành công bài ID: {post_id}")
        return True
    else:
        print(f"❌ Lỗi xóa {response.status_code}: {response.text}")
        return False


def get_post_by_slug(slug):
    endpoint = f"{WP_URL}/wp-json/wp/v2/posts"
    response = requests.get(endpoint, params={"slug": slug}, auth=auth, verify=False)
    if response.status_code == 200:
        posts = response.json()
        if posts:
            print(f"✅ Tìm thấy: ID {posts[0]['id']} | {posts[0]['title']['rendered']}")
            return posts[0]
        print(f"❌ Không tìm thấy slug: {slug}")
    return None


def delete_post_by_slug(slug, force=True):
    post = get_post_by_slug(slug)
    if post:
        return delete_post(post["id"], force=force)
    return False


def update_post(post_id, title=None, content=None, status=None):
    endpoint = f"{WP_URL}/wp-json/wp/v2/posts/{post_id}"
    data = {}
    if title:   data["title"] = title
    if content: data["content"] = content
    if status:  data["status"] = status
    response = requests.post(endpoint, json=data, auth=auth, verify=False)
    if response.status_code == 200:
        print(f"✅ Cập nhật thành công bài ID: {post_id}")
        return response.json()
    else:
        print(f"❌ Lỗi cập nhật {response.status_code}: {response.text}")
        return None


def get_posts(per_page=10):
    endpoint = f"{WP_URL}/wp-json/wp/v2/posts"
    response = requests.get(endpoint, params={"per_page": per_page}, auth=auth, verify=False)
    if response.status_code == 200:
        posts = response.json()
        print(f"📋 Danh sách {len(posts)} bài viết:")
        for p in posts:
            print(f"  - ID: {p['id']} | {p['title']['rendered']} | {p['status']}")
        return posts
    else:
        print(f"❌ Lỗi {response.status_code}: {response.text}")
        return []


def main():
    create_post(
        title="Tiêu đề thử nghiệm",
        content_html="<p>Nội dung thử nghiệm</p>",
        source_name="VnExpress",
        source_url="https://vnexpress.net",
        category="Du lịch, Điểm đến",
        tags=["PHÚ QUỐC", "ĐÀ NẴNG"],
    )


if __name__ == "__main__":
    main()