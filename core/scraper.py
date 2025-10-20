import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os
import re

# ───────────────────── helper ─────────────────────
TH_MONTH = {
    'มกราคม': '01', 'กุมภาพันธ์': '02', 'มีนาคม': '03',
    'เมษายน': '04', 'พฤษภาคม': '05', 'มิถุนายน': '06',
    'กรกฎาคม': '07', 'สิงหาคม': '08', 'กันยายน': '09',
    'ตุลาคม': '10', 'พฤศจิกายน': '11', 'ธันวาคม': '12'
}

def parse_thai_date(text: str) -> str:
    """แปลง '17 พฤษภาคม 2025' ➜ '2025-05-17'"""
    parts = text.strip().split()
    if len(parts) == 3 and parts[1] in TH_MONTH:
        day, month_th, year = parts
        return f"{year}-{TH_MONTH[month_th]}-{int(day):02d}"
    return text.strip()

def fetch_article_body(url: str) -> str:
    """ดึงเนื้อหาเต็มจากเพจข่าว"""
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        body = soup.select_one("div.entry-content")
        if not body:
            return ""
        paras = [p.get_text(" ", strip=True) for p in body.find_all(["p", "li", "blockquote"])]
        return "\n\n".join([re.sub(r'\s+', ' ', p) for p in paras if p])
    except Exception:
        return ""

def load_existing_urls(path: str) -> set:
    """โหลด URL ที่เคยเก็บแล้ว เพื่อตรวจสอบซ้ำ"""
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(article["url"] for article in data)
    except Exception:
        return set()

# ───────────────────── main scraper ─────────────────────
def scrape_standard(max_pages: int = 24, existing_urls: set = set()) -> list[dict]:
    base = "https://thestandard.co/tag/โรคระบาด/page/{}/"
    out = []

    for page in range(1, max_pages + 1):
        url = base.format(page)
        print(f"📄 page {page}: {url}")
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.select("div.news-item")
            if not cards:
                break

            for card in cards:
                a = card.select_one("h3.news-title a")
                if not a:
                    continue
                art_url = a["href"]

                if art_url in existing_urls:
                    print(f"   🔁 ข้ามข่าวซ้ำ: {art_url}")
                    continue

                title = a.get_text(strip=True)
                date_raw = card.select_one("div.date")
                date = parse_thai_date(date_raw.get_text(strip=True)) if date_raw else ""
                content_raw = fetch_article_body(art_url)

                out.append({
                    "source": "thestandard",
                    "title": title,
                    "url": art_url,
                    "date": date,
                    "content_raw": content_raw,  # ✅ ใช้ content_raw แทน content
                    "language": "th",
                    "is_translated": False,
                    "is_summarized": False
                })
        except Exception as e:
            print(f"⚠️ Error page {page}: {e}")
            continue

    return out

# ───────────────────── runner ─────────────────────
if __name__ == "__main__":
    save_path = "data/raw_news/thestandard_news.json"
    existing_urls = load_existing_urls(save_path)

    print("🚀 เริ่มดึงข่าวจาก The Standard …")
    new_articles = scrape_standard(max_pages=24, existing_urls=existing_urls)

    if os.path.exists(save_path):
        with open(save_path, "r", encoding="utf-8") as f:
            old_articles = json.load(f)
    else:
        old_articles = []

    all_articles = old_articles + new_articles
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    print(f"\n✅ ข่าวใหม่: {len(new_articles)} ข่าว")
    print(f"📦 รวมทั้งหมด: {len(all_articles)} ข่าว")
    print(f"📝 บันทึกไว้ที่: {save_path}")
