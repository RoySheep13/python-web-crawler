import csv
import os
import re
import requests
from bs4 import BeautifulSoup

# 網址轉分類對照
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


url = "https://news.ltn.com.tw/list/breakingnews"
res = requests.get(url)
res.encoding = "utf-8"

soup = BeautifulSoup(res.text, "html.parser")
items = soup.select("ul.list li a[href]")

news_list = []
for a in items:
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

# 儲存 CSV (加 utf-8-sig 防止 Excel 亂碼)
file_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "news_data.csv"
)
headers = ["title", "category", "publish_time", "url"]

with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    writer.writerows(news_list)

print(f"成功儲存 {len(news_list)} 筆資料到 CSV！")