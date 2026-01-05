# core/database.py

import psycopg2
from typing import List, Dict
from dateutil import parser

# ──────────────────────────────────────
# DATABASE CONFIG (Neon PostgreSQL)
# ──────────────────────────────────────
DB_URI = "your database api"

def connect_db():
    return psycopg2.connect(DB_URI)

def safe_parse_date(date_str):
    try:
        return parser.parse(date_str).date()
    except:
        return None

# ──────────────────────────────────────
# FETCH ALL NEWS
# ──────────────────────────────────────
def fetch_existing_news() -> List[Dict]:
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM epidemic_news")
    rows = cursor.fetchall()
    result = [dict(zip([desc[0] for desc in cursor.description], row)) for row in rows]
    cursor.close()
    conn.close()
    return result

# ──────────────────────────────────────
# INSERT OR UPDATE NEWS
# ──────────────────────────────────────
def insert_or_update_news(news_list: List[Dict]):
    conn = connect_db()
    cursor = conn.cursor()

    # ดึงข่าวเดิมมาเทียบ url
    cursor.execute("SELECT url FROM epidemic_news")
    existing_urls = set(row[0] for row in cursor.fetchall())

    for news in news_list:
        url = news.get("url")
        if url in existing_urls:
            # UPDATE
            cursor.execute("""
                UPDATE epidemic_news SET
                    content_translated_en = %s,
                    content_translated_th = %s,
                    content_translated_ko = %s,
                    summary_en = %s,
                    summary_th = %s,
                    summary_ko = %s,
                    hashtags = %s,
                    hashtags_en = %s,
                    hashtags_th = %s,
                    hashtags_ko = %s,
                    is_translated = %s,
                    is_summarized = %s
                WHERE url = %s
            """, (
                news.get('content_translated_en'),
                news.get('content_translated_th'),
                news.get('content_translated_ko'),
                news.get('summary_en'),
                news.get('summary_th'),
                news.get('summary_ko'),
                news.get('hashtags'),
                news.get('hashtags_en'),
                news.get('hashtags_th'),
                news.get('hashtags_ko'),
                news.get('is_translated', False),
                news.get('is_summarized', False),
                url
            ))
        else:
            # INSERT
            cursor.execute("""
                INSERT INTO epidemic_news 
                (source, title, url, date, content_raw,
                content_translated_en, content_translated_th, content_translated_ko,
                summary_en, summary_th, summary_ko,
                hashtags, hashtags_en, hashtags_th, hashtags_ko,
                language, is_translated, is_summarized)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                news.get('source'),
                news.get('title'),
                news.get('url'),
                safe_parse_date(news.get('date')),
                news.get('content_raw', news.get('content', '')),
                news.get('content_translated_en'),
                news.get('content_translated_th'),
                news.get('content_translated_ko'),
                news.get('summary_en'),
                news.get('summary_th'),
                news.get('summary_ko'),
                news.get('hashtags'),
                news.get('hashtags_en'),
                news.get('hashtags_th'),
                news.get('hashtags_ko'),
                news.get('language'),
                news.get('is_translated', False),
                news.get('is_summarized', False)
            ))

    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ Insert/Update สำเร็จ {len(news_list)} ข่าว")

# ──────────────────────────────────────
# DELETE IRRELEVANT NEWS
# ──────────────────────────────────────
def delete_irrelevant_news(urls_to_delete: List[str]):
    if not urls_to_delete:
        return
    conn = connect_db()
    cursor = conn.cursor()
    cursor.executemany("DELETE FROM epidemic_news WHERE url = %s", [(url,) for url in urls_to_delete])
    conn.commit()
    cursor.close()
    conn.close()
    print(f"🗑️ ลบข่าวที่ไม่เกี่ยวกับโรคระบาดจำนวน {len(urls_to_delete)} ข่าวแล้ว")

# ──────────────────────────────────────
# WRAP ALL IN CLASS FOR UI USE
# ──────────────────────────────────────
class DatabaseManager:
    def get_latest_news(self, limit: int = 50) -> List[Dict]:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM epidemic_news ORDER BY date DESC LIMIT %s", (limit,))
        rows = cursor.fetchall()
        result = [dict(zip([desc[0] for desc in cursor.description], row)) for row in rows]
        cursor.close()
        conn.close()
        return result

    def search_news(self, keyword: str) -> List[Dict]:
        conn = connect_db()
        cursor = conn.cursor()
        query = """
            SELECT * FROM epidemic_news 
            WHERE title ILIKE %s OR content_raw ILIKE %s 
            ORDER BY date DESC
        """
        cursor.execute(query, (f"%{keyword}%", f"%{keyword}%"))
        rows = cursor.fetchall()
        result = [dict(zip([desc[0] for desc in cursor.description], row)) for row in rows]
        cursor.close()
        conn.close()
        return result

# 👇 Create a shared instance
db_manager = DatabaseManager()
