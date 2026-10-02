import requests
from bs4 import BeautifulSoup
import time
import random
import csv
import os
import re
import json
from datetime import datetime, timedelta


# 自由時報「即時新聞」列表
# 第1頁是一般網頁(HTML)，第2頁以後網站是用 AJAX 載入的(回傳 JSON)
LIST_URL = "https://news.ltn.com.tw/list/breakingnews"
AJAX_URL = "https://news.ltn.com.tw/ajax/breakingnews/all/{}"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
]

# 網址裡的代號 -> 中文分類（列表上沒有分類文字，所以從網址判斷）
PATH_CATEGORY = {
    "politics": "政治", "society": "社會", "life": "生活", "world": "國際",
    "local": "地方", "novelty": "蒐奇", "art": "藝文", "opinion": "評論",
    "business": "財經", "china": "中國",
}
# 有些新聞在子網域，例如 ent.ltn.com.tw 是娛樂
SUBDOMAIN_CATEGORY = {
    "ent": "娛樂", "sports": "體育", "talk": "評論", "ec": "財經",
    "3c": "3C", "auto": "汽車", "health": "健康", "food": "食尚",
    "istyle": "時尚", "def": "軍事",
}

DELAY_RANGE = (1.5, 3.5)

MAX_RETRIES = 3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_random_headers():
    # 隨機換 User-Agent，假裝不是機器人
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    }


def fetch_page(url, retries=MAX_RETRIES):
    # 失敗就重試，每次等比較久（backoff）
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=get_random_headers(), timeout=10)
            response.raise_for_status()
            response.encoding = "utf-8"
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"  [警告] 第 {attempt} 次請求失敗：{e}")
            if attempt < retries:
                wait = random.uniform(*DELAY_RANGE) * attempt
                print(f"  → {wait:.1f} 秒後重試...")
                time.sleep(wait)
            else:
                print(f"  [錯誤] 已達最大重試次數，放棄此頁面：{url}")
                return None


def get_category(url):
    # 例如 https://news.ltn.com.tw/news/life/breakingnews/5593527 -> 生活
    m = re.search(r"/news/([^/]+)/breakingnews/", url)
    if m:
        slug = m.group(1)
        return PATH_CATEGORY.get(slug, slug)

    # 沒有分類代號的話，看子網域 (ent / sports / talk ...)
    m = re.search(r"//([^./]+)\.ltn\.com\.tw/", url)
    if m and m.group(1) != "news":
        return SUBDOMAIN_CATEGORY.get(m.group(1), m.group(1))

    return "其他"


def normalize_time(raw, now, prev):
    # 把時間字串變成 datetime
    # 列表上通常只有 "21:00"（沒有日期），所以要自己補上日期
    # 新聞是新->舊排列，如果某則時間比前一則還晚，代表跨過午夜了，要減一天
    raw = (raw or "").strip()

    m = re.search(r"(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})", raw)
    if m:
        y, mo, d, h, mi = map(int, m.groups())
        return datetime(y, mo, d, h, mi)

    m = re.search(r"(\d{1,2}):(\d{2})", raw)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        dt = now.replace(hour=h, minute=mi, second=0, microsecond=0)
        if dt > prev:
            dt -= timedelta(days=1)
        return dt

    return None


def make_row(title, url, raw_time, now, prev):
    # 把一則新聞整理成一筆 dict，順便回傳這則的時間給下一則比較用
    dt = normalize_time(raw_time, now, prev)
    row = {
        "title": re.sub(r"\s+", " ", title).strip(),
        "category": get_category(url),
        "publish_time": dt.strftime("%Y-%m-%d %H:%M") if dt else "未知時間",
        "url": url,
    }
    return row, (dt if dt else prev)


def parse_news_list(html, now=None):
    # 解析第1頁的 HTML
    now = now or datetime.now()
    soup = BeautifulSoup(html, "html.parser")
    news = []
    prev = now

    for a in soup.select("ul.list li a[href]"):
        url = a["href"].strip()

        h3 = a.select_one("h3.title")
        title = a.get("title") or (h3.get_text(strip=True) if h3 else "")
        if not title or not url:
            continue

        time_tag = a.select_one("span.time")
        raw_time = time_tag.get_text(strip=True) if time_tag else ""

        row, prev = make_row(title, url, raw_time, now, prev)
        news.append(row)

    return news


def parse_news_json(text, now=None):
    # 解析第2頁以後的 JSON
    # 回傳 None 代表沒有更多資料（要停止），回傳 list 代表正常
    now = now or datetime.now()
    try:
        data = json.loads(text)
    except ValueError:
        print("  [警告] 回傳的不是 JSON")
        return None

    if data.get("code") != 200 or not data.get("data"):
        return None

    items = data["data"]
    if isinstance(items, dict):
        items = list(items.values())

    news = []
    prev = now
    for item in items:
        title = item.get("title", "")
        url = item.get("url", "").replace("http://", "https://")
        if not title or not url:
            continue
        row, prev = make_row(title, url, item.get("time", ""), now, prev)
        news.append(row)

    return news


def scrape_news(max_pages=3):
    all_news = []
    seen = set()  # 用網址去重複
    page = 1

    while page <= max_pages:
        if page == 1:
            url = LIST_URL
        else:
            url = AJAX_URL.format(page)
        print(f"[擷取中] 第 {page} 頁：{url}")

        text = fetch_page(url)
        if text is None:
            break

        if page == 1:
            news = parse_news_list(text)
        else:
            news = parse_news_json(text)

        if not news:
            print("  沒有擷取到任何資料，停止爬取")
            break

        new_count = 0
        for n in news:
            if n["url"] in seen:
                continue
            seen.add(n["url"])
            all_news.append(n)
            new_count += 1

        print(f"  → 本頁擷取到 {new_count} 筆新資料，累計 {len(all_news)} 筆")

        if page < max_pages:
            delay = random.uniform(*DELAY_RANGE)
            print(f"  等待 {delay:.1f} 秒後繼續...\n")
            time.sleep(delay)

        page += 1

    return all_news


def save_to_csv(rows, filename="news_data.csv"):
    if not rows:
        print("沒有資料可以儲存")
        return

    filepath = os.path.join(SCRIPT_DIR, filename)
    fieldnames = ["title", "category", "publish_time", "url"]
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n已將 {len(rows)} 筆資料儲存至 {filepath}")


if __name__ == "__main__":
    print("=" * 50)
    print("Python 網路爬蟲 - 自由時報即時新聞")
    print("=" * 50)

    results = scrape_news(max_pages=3)

    save_to_csv(results, "news_data.csv")

    if results:
        # 算每個分類各有幾則
        count = {}
        for r in results:
            count[r["category"]] = count.get(r["category"], 0) + 1

        print(f"\n共擷取 {len(results)} 則新聞")
        for cat, n in sorted(count.items(), key=lambda x: -x[1]):
            print(f"  {cat}：{n} 則")