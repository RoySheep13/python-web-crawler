import requests
from bs4 import BeautifulSoup
import time
import random
import csv
import os
from urllib.parse import urljoin


BASE_URL = "https://books.toscrape.com/catalogue/page-{}.html"

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

RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

DELAY_RANGE = (1.5, 3.5)

MAX_RETRIES = 3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    }


def fetch_page(url, retries=MAX_RETRIES):
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


def parse_book_list(html, page_url):
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
    soup = BeautifulSoup(html, "html.parser")
    return soup.select_one("li.next a") is not None


def scrape_books(max_pages=5):
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

        delay = random.uniform(*DELAY_RANGE)
        print(f"  等待 {delay:.1f} 秒後繼續...\n")
        time.sleep(delay)

        page += 1

    return all_books


def save_to_csv(books, filename="books_data.csv"):
    if not books:
        print("沒有資料可以儲存")
        return

    filepath = os.path.join(SCRIPT_DIR, filename)
    fieldnames = ["title", "price", "rating", "stock", "detail_url"]
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(books)

    print(f"\n已將 {len(books)} 筆資料儲存至 {filepath}")


if __name__ == "__main__":
    print("=" * 50)
    print("Python 網路爬蟲 - 書籍資訊擷取")
    print("=" * 50)

    results = scrape_books(max_pages=5)

    save_to_csv(results, "books_data.csv")

    if results:
        avg_price = sum(float(b["price"].replace("£", "")) for b in results) / len(results)
        print(f"\n共擷取 {len(results)} 本書籍資料")
        print(f"平均價格：£{avg_price:.2f}")