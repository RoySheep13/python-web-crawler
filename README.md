# 自由時報即時新聞爬蟲 (LTN News Crawler) 📰

這是我的 Python 自主學習 / 小專題作品！主要目的是自動化抓取「自由時報 (LTN)」即時新聞的標題、發布時間、新聞分類與文章網址，並將結果整理存成 CSV 檔案，方便後續進行簡易的文字分析或資料統計。

---

## 💡 專案動機與目標

在學習 Python 的過程中，我對網絡爬蟲（Web Crawler）很感興趣。希望透過這個實作專題：
1. 練習使用 `requests` 與 `BeautifulSoup4` 進行網頁解析。
2. 了解動態網頁（AJAX/JSON）與一般靜態 HTML 的差異。
3. 學習將非結構化的網頁資料清洗後，儲存成標準 CSV 格式。
4. 建立基礎的防封鎖概念（User-Agent 輪替、隨機延遲、連線重試）。

---

## 🛠️ 技術棧與套件 (Tech Stack)

* **語言**：Python 3.10+
* **主要套件**：
  * `requests`：發送 HTTP 請求取得網頁內容或 API 資料。
  * `beautifulsoup4` (bs4)：解析 HTML 結構並擷取指定標籤。
  * `json` / `csv` / `re` / `datetime` / `random` / `time`：標準庫，用於資料處理、時序控制與檔案寫入。

---

## 🏗️ 程式架構與流程 (Architecture)

整個專案由一個模組化的 `main.py` 構成，流程如下：

```
[ 開始執行 start_crawler() ]
         │
         ├─── 第 1 頁 (靜態 HTML) ───> get_web_content() ───> parse_first_page() ──┐
         │                                                                       │
         └─── 第 2+ 頁 (AJAX JSON) ──> get_web_content() ───> parse_ajax_json()  ──┼─> [ 資料去重 & 整合 ]
                                                                                 │          │
┌────────────────────────────────────────────────────────────────────────────────┘          ▼
│                                                                                    find_category() (網址轉分類)
│                                                                                    clean_time_string() (整理時間)
│                                                                                           │
└───────────────────────────────────────────────────────────────────────────────────────────┼─> [ 存檔 & 統計 ]
                                                                                            │
                                                                                            ├──> save_to_csv()
                                                                                            └──> 終端機顯示分類統計結果
```

### 主要功能函式說明：
| 函式名稱 | 功能說明 |
| :--- | :--- |
| `get_headers()` | 隨機挑選 User-Agent，降低被伺服器識別為爬蟲的風險 |
| `get_web_content()` | 發送 Request 並具備自動重試（Max Retries）與異常處理機制 |
| `find_category()` | 利用正則表達式解析 URL，將英文網址路徑或子網域轉換為中文分類 |
| `clean_time_string()` | 補齊與格式化時間字串（例如將僅有 `HH:MM` 的時間加上當天日期） |
| `parse_first_page()` | 使用 BeautifulSoup 解析首頁 HTML 結構 |
| `parse_ajax_json()` | 解析第 2 頁之後由 AJAX 介面回傳的 JSON 格式資料 |
| `start_crawler()` | 主控流程，負責頁數循環、資料去重與停頓控制 |
| `save_to_csv()` | 將爬取結果匯出為帶有 BOM (`utf-8-sig`) 的 CSV 檔 |

---

## 🐞 開發與除錯歷程 (Development & Debugging Journey)

在開發這個爬蟲的過程中遇到了不少問題，紀錄如下：

### 階段 1：初試身手 (2025/11/04)
* **嘗試**：寫了第一個版本，嘗試用 `requests.get()` 抓取自由時報首頁。
* **遇到問題**：印出來的中文標題全部變成亂碼。
* **解決方式**：發現是編碼問題，加上 `res.encoding = 'utf-8'` 後恢復正常。

### 階段 2：資料儲存與網址解析 (2025/11/12)
* **嘗試**：匯出 CSV 檔並寫了正則表達式（`re`）嘗試判斷新聞分類。
* **遇到問題**：用 Excel 打開產出的 `news_data.csv` 時，所有中文標題又變成亂碼了！
* **解決方式**：上網查資料發現 Windows 版的 Excel 需要 BOM 才能識別 UTF-8，把檔案開啟模式改成 `encoding='utf-8-sig'` 後順利解決。

### 階段 3：遇到大魔王——AJAX 翻頁失敗 (2025/11/23)
* **嘗試**：嘗試抓取第 2 頁與第 3 頁新聞。
* **遇到問題**：修改網址為 `.../breakingnews/2` 後，發現抓下來的 HTML 裡面完全沒有新聞內容，列表是空的！
* **除錯過程**：按下 F12 打開瀏覽器開發者工具（Network 頁籤），觀察手動點擊「看更多」時網頁發出的請求，發現第 2 頁以後網站是發送 AJAX 請求到 API：`https://news.ltn.com.tw/ajax/breakingnews/all/2`，且回傳的是 JSON 資料而非 HTML。
* **解決方式**：新增 `parse_ajax_json()` 函式，專門處理 JSON 格式的回傳值，解決了無法爬取後續頁面的問題。

### 階段 4：反爬蟲機制與穩健度調優 (2025/12/03)
* **嘗試**：連續快速爬取多頁資料。
* **遇到問題**：偶爾會跳出 `ConnectionResetError` 或 Request 失敗。
* **解決方式**：
  1. 建立 `USER_AGENTS` 清單，每次 Request 隨機切換。
  2. 加入 `time.sleep(random.uniform(1.5, 3.5))`，模擬真人瀏覽行為，減輕伺服器負擔。
  3. 包裹 `try-except` 並加上連線失敗自動重試機制。

### 階段 5：程式碼重構與專題完工 (2025/12/16)
* **優化**：將原本散落的程式碼重構成模組化的函式結構，補齊全部新聞子網域（如 `sports`、`3c` 等）的分類對照表，並在控制台加入精美的執行過程與統計輸出。

---

## 🚀 如何執行 (How to Run)

1. **複製專案庫**：
   ```bash
   git clone https://github.com/你的帳號/python-web-crawler.git
   cd python-web-crawler/ltn-news-crawler
   ```

2. **安裝所需套件**：
   ```bash
   pip install requests beautifulsoup4
   ```

3. **執行爬蟲**：
   ```bash
   python main.py
   ```

4. **查看結果**：
   執行完成後，資料會存入同目錄下的 `news_data.csv` 檔案中，終端機也會顯示統計數據：
   ```text
   ========================================
         自由時報即時新聞爬蟲 (小專題)     
   ========================================
   正在爬取第 1 頁：https://news.ltn.com.tw/list/breakingnews
     -> 第 1 頁抓到 20 則新新聞 (目前累計: 20 則)
     等待 2.3 秒後繼續...

   成功！已經把 60 筆資料儲存到: .../news_data.csv

   --- 分類統計結果 ---
     社會: 18 篇
     生活: 15 篇
     政治: 12 篇
     國際: 8 篇
     ...
   ```

---

## 📝 心得與未來展望
這個小專題讓我真正體會到網頁開發與爬蟲攻防的樂趣！未來有時間的話，希望能加上：
* SQLite 資料庫整合
* 自動發送 Email 每日頭條新聞摘要
* 文字雲（WordCloud）文字探勘與熱門關鍵字統計