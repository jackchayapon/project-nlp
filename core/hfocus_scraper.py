import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
from datetime import datetime

# ─────────────────────────────
# 🔹 ฟังก์ชันช่วย
# ─────────────────────────────
def clean(text: str) -> str:
    """ลบช่องว่างเกินและตัดช่องว่างหัว–ท้าย"""
    return re.sub(r'\s+', ' ', text).strip()

def load_existing_urls(path: str) -> set:
    """อ่านไฟล์ JSON ที­­่เคยเซฟไว้ แล้วดึง URL เพื่อป้องกันข่าวซ้ำ"""
    if not os.path.exists(path):
        return set()
    try:
        with open(path, encoding="utf-8") as f:
            return {art["url"] for art in json.load(f)}
    except Exception:
        return set()

# ─────────────────────────────
# 🔹 ดึงเนื้อหา/วันที่จากหน้าเดี่ยว
# ─────────────────────────────
def get_article_content_and_date(article_url: str) -> tuple[str, str]:
    try:
        print(f"    • ดึง: {article_url}")
        res = requests.get(article_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # วันที่
        date_tag = soup.select_one("span.field-content")
        date = clean(date_tag.text) if date_tag else ""

        # เนื้อหา
        content_div = soup.select_one("article div.field--name-body")
        if content_div:
            raw = content_div.get_text(" ", strip=True)
            content = clean(raw)
            print(f"      ✅ เนื้อหา {len(content)} ตัวอักษร")
        else:
            content = ""
            print("      • ไม่พบเนื้อหา")

        return date, content
    except Exception as err:
        print(f"❌ Error @ {article_url} : {err}")
        return "", ""

# ─────────────────────────────
# 🔹 ดึงข่าวจากหน้า list
# ─────────────────────────────
def scrape_hfocus_articles(pages: int = 1, *, existing_urls: set = set()) -> list[dict]:
    base = "https://www.hfocus.org/topics/โรคอุบัติใหม่อุบัติซ้ำ?page={}"
    articles = []

    for page in range(pages):
        url = base.format(page)
        print(f"\n🔍 หน้า {page+1}: {url}")
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            links = soup.select("div.views-field-title h3.field-content a")
            if not links:
                print("    • ไม่พบข่าวหรือ selector เปลี่ยน")
                break

            for a in links:
                link = "https://www.hfocus.org" + a["href"]
                if link in existing_urls:
                    print(f"      • ข้ามข่าวซ้ำ: {link}")
                    continue

                title = clean(a.get_text())
                date, content_raw = get_article_content_and_date(link)

                articles.append({
                    "source": "hfocus",
                    "title": title,
                    "url": link,
                    "date": date,
                    "content_raw": content_raw,   # ✅ ใช้ content_raw
                    "content_translated": None,
                    "summary": None,
                    "language": "th",
                    "is_translated": False,
                    "is_summarized": False
                })

                time.sleep(0.5)  # ถนอมเซิร์ฟเวอร์

        except requests.exceptions.RequestException as http_err:
            print(f"⚠️ HTTP Error: {http_err}")
        except Exception as err:
            print(f"⚠️ Error: {err}")

        time.sleep(2)

    return articles

# ─────────────────────────────
# 🔹 Main: ใช้ดึงแล้วเซฟเป็นไฟล์ JSON
# ─────────────────────────────
if __name__ == "__main__":
    print("🚀 เริ่มดึงข่าวจาก Hfocus.org …")

    today = datetime.now().strftime("%Y%m%d")
    save_dir = "data/raw_news"
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"hfocus_news_{today}.json")

    existing = load_existing_urls(save_path)
    new_articles = scrape_hfocus_articles(pages=20, existing_urls=existing)

    print(f"\n✅ ข่าวใหม่ {len(new_articles)} รายการ")

    # รวมกับข่าวเก่าถ้ามี
    all_articles = new_articles
    if os.path.exists(save_path):
        with open(save_path, encoding="utf-8") as f:
            all_articles = json.load(f) + new_articles

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    print(f"📝 บันทึกทั้งหมด {len(all_articles)} ข่าว → {save_path}")
