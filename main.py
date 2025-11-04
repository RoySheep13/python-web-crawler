import requests
from bs4 import BeautifulSoup

# 抓自由時報即時新聞首頁
url = "https://news.ltn.com.tw/list/breakingnews"
res = requests.get(url)
res.encoding = "utf-8"

soup = BeautifulSoup(res.text, "html.parser")

# 抓取新聞標題與網址
items = soup.select("ul.list li a[href]")
for a in items:
    title_tag = a.select_one("h3.title")
    title = title_tag.get_text().strip() if title_tag else ""
    link = a["href"].strip()

    if title and link:
        print(f"標題: {title}")
        print(f"連結: {link}")
        print("-" * 30)