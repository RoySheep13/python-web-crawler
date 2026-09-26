"""
Python 網路爬蟲 - 線上書店書籍資訊擷取
==========================================
自主學習專案：Python 爬蟲研究與開發

技術重點：
1. User-Agent 偽裝：從多組瀏覽器 User-Agent 中隨機挑選，
   降低被伺服器辨識為機器人程式的機率
2. 隨機請求延遲：每次發送請求之間加入隨機秒數的等待，
   避免對伺服器造成過大負擔（伺服器禮儀），
   同時降低因請求頻率異常而被判定、封鎖 IP 的風險
3. 例外處理與重試機制：面對逾時、連線失敗等狀況，
   自動重試並延長等待時間，提升程式穩定性
4. 資料整理與輸出：將擷取結果整理成 CSV 檔，方便後續分析

目標網站：https://books.toscrape.com
（此網站專門提供給學習者練習網頁爬蟲技術，內容為示範用虛構書籍資料，
 允許程式化存取，適合作為技術學習與展示用途）
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import csv
from urllib.parse import urljoin


# ------------------------- 基本設定 -------------------------

BASE_URL = "https://books.toscrape.com/catalogue/page-{}.html"

# User-Agent 池：每次請求隨機挑選一組，模擬不同瀏覽器/裝置的真實使用者
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

# 星等文字轉換成數字，方便後續統計分析
RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

# 每次請求之間的延遲區間（秒）。隨機取值可避免請求節奏過於規律而被偵測
DELAY_RANGE = (1.5, 3.5)

# 請求失敗時的最大重試次數
MAX_RETRIES = 3


def get_random_headers():
    """隨機組合一組 request headers，模擬真實瀏覽器行為"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    }


def fetch_page(url, retries=MAX_RETRIES):
    """
    發送 HTTP 請求並取得網頁原始碼。
    包含錯誤處理與重試機制，避免單次網路異常導致整個程式中斷。
    """
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=get_random_headers(), timeout=10)
            response.raise_for_status()
            response.encoding = "utf-8"
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"  [警告] 第 {attempt} 次請求失敗：{e}")
            if attempt < retries:
                wait = random.uniform(*DELAY_RANGE) * attempt  # 失敗越多次，等待越久
                print(f"  → {wait:.1f} 秒後重試...")
                time.sleep(wait)
            else:
                print(f"  [錯誤] 已達最大重試次數，放棄此頁面：{url}")
                return None


def parse_book_list(html, page_url):
    """從書籍列表頁面中解析出每一本書的基本資訊"""
    soup = BeautifulSoup(html, "html.parser")
    books = []

    for item in soup.select("article.product_pod"):
        title_tag = item.select_one("h3 a")
        title = title_tag["title"] if title_tag else "未知書名"
        detail_link = urljoin(page_url, title_tag["href"]) if title_tag else None

        price_tag = item.select_one("p.price_color")
        price = price_tag.get_text(strip=True) if price_tag else "未知價格"

        rating_tag = item.select_one("p.star-rating")
        rating_word = rating_tag["class"][1] if rating_tag else None
        rating = RATING_MAP.get(rating_word, 0)

        stock_tag = item.select_one("p.instock.availability")
        stock = stock_tag.get_text(strip=True) if stock_tag else "未知"

        books.append({
            "title": title,
            "price": price,
            "rating": rating,
            "stock": stock,
            "detail_url": detail_link,
        })

    return books


def has_next_page(html):
    """判斷目前頁面是否還有下一頁"""
    soup = BeautifulSoup(html, "html.parser")
    return soup.select_one("li.next a") is not None


def scrape_books(max_pages=5):
    """
    主要爬蟲流程：
    依序造訪每一頁書籍列表，直到達到 max_pages 或沒有下一頁為止。
    """
    all_books = []
    page = 1

    while page <= max_pages:
        url = BASE_URL.format(page)
        print(f"[擷取中] 第 {page} 頁：{url}")

        html = fetch_page(url)
        if html is None:
            break

        books = parse_book_list(html, url)
        if not books:
            print("  沒有擷取到任何資料，停止爬取")
            break

        all_books.extend(books)
        print(f"  → 本頁擷取到 {len(books)} 筆資料，累計 {len(all_books)} 筆")

        if not has_next_page(html):
            print("  已到達最後一頁")
            break

        # 隨機延遲：兼顧程式穩定性與伺服器禮儀，避免造成過大流量負擔
        delay = random.uniform(*DELAY_RANGE)
        print(f"  等待 {delay:.1f} 秒後繼續...\n")
        time.sleep(delay)

        page += 1

    return all_books


def save_to_csv(books, filename="books_data.csv"):
    """將擷取到的資料儲存為 CSV 檔案（utf-8-sig 方便用 Excel 開啟不亂碼）"""
    if not books:
        print("沒有資料可以儲存")
        return

    fieldnames = ["title", "price", "rating", "stock", "detail_url"]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(books)

    print(f"\n已將 {len(books)} 筆資料儲存至 {filename}")


if __name__ == "__main__":
    print("=" * 50)
    print("Python 網路爬蟲 - 書籍資訊擷取")
    print("=" * 50)

    # 可自行調整想擷取的頁數（此網站共有 50 頁書籍列表）
    results = scrape_books(max_pages=5)

    save_to_csv(results, "books_data.csv")

    if results:
        avg_price = sum(float(b["price"].replace("£", "")) for b in results) / len(results)
        print(f"\n共擷取 {len(results)} 本書籍資料")
        print(f"平均價格：£{avg_price:.2f}")
