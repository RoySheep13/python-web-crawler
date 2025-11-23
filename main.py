import csv
import json
import os
import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://news.ltn.com.tw/list/breakingnews"
AJAX_URL = "https://news.ltn.com.tw/ajax/breakingnews/all/{}"

PATH_CATEGORY_MAP = {
    "politics": "政治",
    "society": "社會",
    "life": "生活",
    "world": "國際",
    "local": "地方",
    "business": "財經",
}


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
    data = json.loads(json_text)
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
for page in range(1, 4):
    if page == 1:
        res = requests.get(BASE_URL)
        res.encoding = "utf-8"
        news = parse_first_page(res.text)
    else:
        res = requests.get(AJAX_URL.format(page))
        news = parse_ajax_json(res.text)

    all_news.extend(news)

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

print(f"累計抓取 {len(all_news)} 筆新聞！")