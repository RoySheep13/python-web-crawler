import csv
import json
import os
import random
import re
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# ===== 基本設定 =====
# 自由時報即時新聞網址
BASE_URL = "https://news.ltn.com.tw/list/breakingnews"
AJAX_URL = "https://news.ltn.com.tw/ajax/breakingnews/all/{}"

# 模擬瀏覽器 Header，防止被網站鎖 IP
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# 網址對應分類 (網址裡面的英文轉中文)
PATH_CATEGORY_MAP = {
    "politics": "政治",
    "society": "社會",
    "life": "生活",
    "world": "國際",
    "local": "地方",
    "novelty": "蒐奇",
    "art": "藝文",
    "opinion": "評論",
    "business": "財經",
    "china": "中國",
}

SUBDOMAIN_CATEGORY_MAP = {
    "ent": "娛樂",
    "sports": "體育",
    "talk": "評論",
    "ec": "財經",
    "3c": "3C",
    "auto": "汽車",
    "health": "健康",
    "food": "食尚",
    "istyle": "時尚",
    "def": "軍事",
}


# 隨機產生 Header 避免被擋
def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }


# 抓取網頁原始碼 (有加簡單的重試機制)
def get_web_content(url, max_retry=3):
    for i in range(1, max_retry + 1):
        try:
            res = requests.get(url, headers=get_headers(), timeout=10)
            if res.status_code == 200:
                res.encoding = "utf-8"
                return res.text
        except Exception as e:
            print(f"  [警告] 第 {i} 次連線失敗... 錯誤: {e}")
            if i < max_retry:
                sleep_time = random.uniform(1.5, 3.5)
                time.sleep(sleep_time)

    print(f"  [錯誤] 試了 {max_retry} 次都失敗，放棄這個網址: {url}")
    return None


# 從網址解析分類
def find_category(url):
    # 先找主站新聞路徑
    match = re.search(r"/news/([^/]+)/breakingnews/", url)
    if match:
        cat_key = match.group(1)
        return PATH_CATEGORY_MAP.get(cat_key, cat_key)

    # 再找子網域 (例如 sports.ltn.com.tw)
    match_sub = re.search(r"//([^./]+)\.ltn\.com\.tw/", url)
    if match_sub:
        sub_name = match_sub.group(1)
        if sub_name != "news":
            return SUBDOMAIN_CATEGORY_MAP.get(sub_name, sub_name)

    return "其他"


# 整理發布時間格式
def clean_time_string(raw_time_str):
    if not raw_time_str:
        return "未知時間"

    raw_time_str = raw_time_str.strip()

    # 如果已經是完整時間格式 (YYYY-MM-DD HH:MM)
    if re.search(r"\d{4}-\d{2}-\d{2}", raw_time_str):
        return raw_time_str

    # 如果只有時間 (HH:MM)，前面補上今天的日期
    match_time = re.search(r"(\d{1,2}):(\d{2})", raw_time_str)
    if match_time:
        today_str = datetime.now().strftime("%Y-%m-%d")
        return f"{today_str} {match_time.group(1)}:{match_time.group(2)}"

    return raw_time_str


# 解析 HTML 網頁 (第一頁專用)
def parse_first_page(html_code):
    soup = BeautifulSoup(html_code, "html.parser")
    news_list = []

    # 抓取列表項目
    items = soup.select("ul.list li a[href]")
    for a in items:
        link = a["href"].strip()

        # 抓標題
        title_tag = a.select_one("h3.title")
        title = a.get("title") or (
            title_tag.get_text().strip() if title_tag else ""
        )

        if not title or not link:
            continue

        # 抓時間
        time_tag = a.select_one("span.time")
        raw_time = time_tag.get_text().strip() if time_tag else ""

        news_item = {
            "title": title.strip(),
            "category": find_category(link),
            "publish_time": clean_time_string(raw_time),
            "url": link,
        }
        news_list.append(news_item)

    return news_list


# 解析 JSON 資料 (第二頁以後都是 AJAX 回傳 JSON)
def parse_ajax_json(json_text):
    try:
        data = json.loads(json_text)
    except Exception:
        print("  [警告] 解析 JSON 失敗")
        return []

    if data.get("code") != 200 or not data.get("data"):
        return []

    items = data["data"]
    # 轉成 list 方便走訪
    if isinstance(items, dict):
        items = list(items.values())

    news_list = []
    for item in items:
        title = item.get("title", "").strip()
        link = item.get("url", "").replace("http://", "https://")

        if not title or not link:
            continue

        news_item = {
            "title": title,
            "category": find_category(link),
            "publish_time": clean_time_string(item.get("time", "")),
            "url": link,
        }
        news_list.append(news_item)

    return news_list


# 主要爬蟲流程
def start_crawler(max_pages=3):
    all_news = []
    visited_urls = set()

    for page in range(1, max_pages + 1):
        if page == 1:
            target_url = BASE_URL
        else:
            target_url = AJAX_URL.format(page)

        print(f"正在爬取第 {page} 頁：{target_url}")

        html_or_json = get_web_content(target_url)
        if not html_or_json:
            print("無法讀取網頁，停止爬取")
            break

        if page == 1:
            page_news = parse_first_page(html_or_json)
        else:
            page_news = parse_ajax_json(html_or_json)

        if not page_news:
            print("沒有抓到任何新聞，可能已經到最後一頁了")
            break

        # 去重並加入總列表
        new_count = 0
        for item in page_news:
            if item["url"] not in visited_urls:
                visited_urls.add(item["url"])
                all_news.append(item)
                new_count += 1

        print(
            f"  -> 第 {page} 頁抓到 {new_count} 則新新聞 (目前累計: {len(all_news)} 則)"
        )

        # 隨機停頓一下，不要給伺服器太高壓力
        if page < max_pages:
            delay = random.uniform(1.5, 3.5)
            print(f"  等待 {delay:.1f} 秒後繼續...\n")
            time.sleep(delay)

    return all_news


# 存檔成 CSV
def save_to_csv(data_list, output_file="news_data.csv"):
    if not data_list:
        print("沒有資料可以儲存！")
        return

    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, output_file)

    headers = ["title", "category", "publish_time", "url"]

    # 加上 encoding='utf-8-sig' Excel 打開才不會亂碼
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data_list)

    print(f"\n成功！已經把 {len(data_list)} 筆資料儲存到: {file_path}")


# 主程式進入點
if __name__ == "__main__":
    print("========================================")
    print("      自由時報即時新聞爬蟲 (小專題)     ")
    print("========================================")

    # 預設抓 3 頁
    result_data = start_crawler(max_pages=3)

    # 寫入檔案
    save_to_csv(result_data, "news_data.csv")

    # 簡單統計每個分類有幾篇
    if result_data:
        category_stats = {}
        for item in result_data:
            cat = item["category"]
            category_stats[cat] = category_stats.get(cat, 0) + 1

        print("\n--- 分類統計結果 ---")
        for cat, count in sorted(
            category_stats.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {cat}: {count} 篇")