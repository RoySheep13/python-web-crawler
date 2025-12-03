import csv
import json
import os
import random
import re
import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://news.ltn.com.tw/list/breakingnews"
AJAX_URL = "https://news.ltn.com.tw/ajax/breakingnews/all/{}"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Chrome/124.0.0.0 Safari/537.36",
]

PATH_CATEGORY_MAP = {
    "politics": "政治",
    "society": "社會",
    "life": "生活",
    "world": "國際",
    "local": "地方",
    "business": "財經",
}


def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Connection": "keep-alive",
    }


def get_web_content(url, max_retry=3):
    for i in range(1, max_retry + 1):
        try:
            res = requests.get(url, headers=get_headers(), timeout=10)
            if res.status_code == 200:
                res.encoding = "utf-8"
                return res.text
        except Exception as e:
            print(f"第 {i} 次失敗: {e}")
            time.sleep(random.uniform(1.5, 3.5))
    return None


def find_category(url):
    match = re.search(r"/news/([^/]+)/breakingnews/", url)
    if match:
        cat_key = match.group(1)
        return PATH_CATEGORY_MAP.get(cat_key, cat_key)
    return "其他"


def parse_first_page(html):
    soup = BeautifulSoup(html, "html.parser")
    news_list = []
    for a in soup.select("ul.list li a[href]"):
        title_tag = a.select_one("h3.title")
        title = title_tag.get_text().strip() if title_tag else ""
        link = a["href"].strip()
        time_tag = a.select_one("span.time")
        raw_time = time_tag.get_text().strip() if time_tag else ""

        if title and link:
            news_list.append(
                {
                    "title": title,
                    "category": find_category(link),
                    "publish_time": raw_time,
                    "url": link,
                }
            )
    return news_list


def parse_ajax_json(json_text):
    try:
        data = json.loads(json_text)
    except Exception:
        return []

    if data.get("code") != 200 or not data.get("data"):
        return []

    items = data["data"]
    if isinstance(items, dict):
        items = list(items.values())

    news_list = []
    for item in items:
        title = item.get("title", "").strip()
        link = item.get("url", "").replace("http://", "https://")
        if title and link:
            news_list.append(
                {
                    "title": title,
                    "category": find_category(link),
                    "publish_time": item.get("time", ""),
                    "url": link,
                }
            )
    return news_list


all_news = []
visited_urls = set()

for page in range(1, 4):
    target_url = BASE_URL if page == 1 else AJAX_URL.format(page)
    print(f"正在爬取第 {page} 頁...")

    html_or_json = get_web_content(target_url)
    if not html_or_json:
        break

    page_news = (
        parse_first_page(html_or_json)
        if page == 1
        else parse_ajax_json(html_or_json)
    )

    for item in page_news:
        if item["url"] not in visited_urls:
            visited_urls.add(item["url"])
            all_news.append(item)

    time.sleep(random.uniform(1.5, 3.5))

# 儲存 CSV
file_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "news_data.csv"
)
with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(
        f, fieldnames=["title", "category", "publish_time", "url"]
    )
    writer.writeheader()
    writer.writerows(all_news)

print(f"成功儲存 {len(all_news)} 筆新聞！")