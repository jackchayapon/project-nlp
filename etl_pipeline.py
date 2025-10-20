# ✅ etl_pipeline.py เวอร์ชันสมบูรณ์ 
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from core.scraper import scrape_standard
from core.hfocus_scraper import scrape_hfocus_articles, load_existing_urls
from core.filter import is_epidemic_related
from core.translator import translate
from core.summarizer import summarize
from core.database import fetch_existing_news, insert_or_update_news, delete_irrelevant_news
from core.nlp_utils import generate_hashtags

# 📁 เตรียมโฟลเดอร์เก็บข่าวดิบ
RAW_DIR = "data/raw_news"
os.makedirs(RAW_DIR, exist_ok=True)

# 🗓️ ตั้งชื่อไฟล์ตามวัน
today = datetime.now().strftime("%Y%m%d")
existing_path = os.path.join(RAW_DIR, f"hfocus_news_{today}.json")
existing_urls = load_existing_urls(existing_path)

HFOCUS_PAGES = 20
MAX_WORKERS = 8

# ────────────────────────────────
print("📅 กำลังดึงข่าวจาก Hfocus และ The Standard…")
hfocus = scrape_hfocus_articles(pages=HFOCUS_PAGES, existing_urls=existing_urls)
standard = scrape_standard()
all_news = hfocus + standard
print(f"📄 ดึงมา {len(all_news)} ข่าว")

# ────────────────────────────────
print("🔍 คัดกรองข่าวโรคระบาด…")
filtered = [a for a in all_news if is_epidemic_related(a)]
print(f"✅ คัดกรองเหลือ {len(filtered)} ข่าว")

# ────────────────────────────────
print("📥 ดึงข่าวที่เคยมีใน Database…")
existing_by_url = {a['url']: a for a in fetch_existing_news()}

# ────────────────────────────────
def process_article(article):
    url = article['url']
    lang = article.get("language", "th")
    raw = article.get("content_raw") or article.get("content", "")

    try:
        en = translate(raw, src=lang, tgt="en")
        ko = translate(raw, src=lang, tgt="ko")
        th = translate(raw, src=lang, tgt="th")

        sum_en = summarize(en, lang="en")
        sum_ko = translate(sum_en, src="en", tgt="ko")
        sum_th = translate(sum_en, src="en", tgt="th")

        hashtags_th = generate_hashtags(raw)
        hashtags_en = [translate(tag, src="th", tgt="en") for tag in hashtags_th]
        hashtags_ko = [translate(tag, src="th", tgt="ko") for tag in hashtags_th]

        article.update({
            "content_translated_en": en,
            "content_translated_ko": ko,
            "content_translated_th": th,
            "summary_en": sum_en,
            "summary_ko": sum_ko,
            "summary_th": sum_th,
            "hashtags_th": ", ".join(hashtags_th),
            "hashtags_en": ", ".join(hashtags_en),
            "hashtags_ko": ", ".join(hashtags_ko),
            "is_translated": True,
            "is_summarized": True
        })
        return article

    except Exception as e:
        print(f"[❌] Error: {url} | {e}")
        return None

# ────────────────────────────────
print(f"🧠 ประมวลผล {len(filtered)} ข่าวด้วย {MAX_WORKERS} threads…")
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    processed = list(executor.map(process_article, filtered))

results = [r for r in processed if r is not None]

# ────────────────────────────────
print("💾 บันทึกข่าวลงฐานข้อมูล…")
insert_or_update_news(results)

# ────────────────────────────────
print("🧹 ลบข่าวที่ไม่เกี่ยวกับโรคระบาดออกจาก DB…")
delete_irrelevant_news()
print("✅ เสร็จสิ้นการอัปเดตข่าวทั้งหมด")
