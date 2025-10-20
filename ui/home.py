# ui/home.py
import streamlit as st
import pandas as pd
import psycopg2
import os
from datetime import datetime
import json

# Database connection to external Neon database
DB_URI = "postgresql://neondb_owner:npg_o6AY4XRynVZK@ep-wandering-grass-a1ha7u59-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"


def get_db_connection():
    """Get database connection to external Neon database"""
    try:
        return psycopg2.connect(DB_URI)
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

@st.cache_data(ttl=1800)
def fetch_summary_stats():
    """Fetches summary statistics for the dashboard."""
    stats = {"total_news": 0, "news_last_7_days": 0, "total_sources": 0}
    conn = get_db_connection()
    if not conn:
        return stats
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM epidemic_news;")
            stats["total_news"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM epidemic_news WHERE date >= NOW() - INTERVAL '7 days';")
            stats["news_last_7_days"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(DISTINCT source) FROM epidemic_news;")
            stats["total_sources"] = cursor.fetchone()[0]
    except Exception as e:
        print(f"Could not fetch summary stats: {e}")
    finally:
        if conn:
            conn.close()
    return stats


def parse_hashtags(value):
    if not value: return []
    if isinstance(value, (list, tuple)): return list(value)
    if isinstance(value, str):
        cleaned_value = value.strip('{}')
        tags = cleaned_value.split(',')
        return [tag.strip().lstrip('#') for tag in tags if tag.strip()]
    return []


@st.cache_data(ttl=3600)
def fetch_news(lang, limit=10, offset=0, sort_by='date_desc', search_query='', _force_refresh=False):
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    try:
        cursor = conn.cursor()
        title_col, summary_col, hashtags_col = f'title_{lang}', f'summary_{lang}', f'hashtags_{lang}'
        content_col = 'content_raw' if lang == 'th' else f'content_translated_{lang}'
        query = f"SELECT id, source, url, date, language, {title_col} AS title, {summary_col} AS summary, {hashtags_col} AS hashtags, {content_col} AS content FROM epidemic_news"
        params = []
        where_clauses = []
        if search_query:
            where_clauses.append(f"({title_col} ILIKE %s OR {summary_col} ILIKE %s OR {hashtags_col}::text ILIKE %s)")
            params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])
        if where_clauses: query += " WHERE " + " AND ".join(where_clauses)
        order_map = {'date_desc': 'date DESC', 'date_asc': 'date ASC', 'title_asc': 'title ASC', 'title_desc': 'title DESC'}
        query += f" ORDER BY {order_map.get(sort_by, 'date DESC')} LIMIT %s OFFSET %s;"
        params.extend([limit, offset])
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(rows, columns=columns)
        if 'hashtags' in df.columns:
            df['hashtags'] = df['hashtags'].apply(parse_hashtags)
        return df
    except Exception as e:
        st.error(f"Error fetching news: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()


def get_total_news_count(lang, search_query=''):
    conn = get_db_connection()
    if not conn: return 0
    try:
        cursor = conn.cursor()
        title_col, summary_col, hashtags_col = f'title_{lang}', f'summary_{lang}', f'hashtags_{lang}'
        query = "SELECT COUNT(*) FROM epidemic_news"
        params = []
        if search_query:
            query += f" WHERE ({title_col} ILIKE %s OR {summary_col} ILIKE %s OR {hashtags_col}::text ILIKE %s)"
            params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])
        cursor.execute(query, tuple(params))
        return cursor.fetchone()[0]
    except Exception as e:
        st.error(f"Error fetching total news count: {e}")
        return 0
    finally:
        if conn: conn.close()


# --- START: โค้ดที่นำกลับเข้ามา ---
def display_news_detail(container, news_item, lang):
    """Displays the full details of a single news item."""
    container.markdown(f"## {news_item.get('title', 'ไม่มีหัวข้อ')}")

    if container.button({"th": "⬅️ กลับไปที่ข่าว", "en": "⬅️ Back to News", "ko": "⬅️ 뉴스 목록으로", "jp": "⬅️ ニュースに戻る"}[lang], key="back_to_news_list"):
        st.session_state.view_news_id = None
        st.rerun()

    display_date = news_item['date'].strftime("%Y-%m-%d %H:%M") if isinstance(news_item['date'], datetime) else str(news_item['date'])
    container.markdown(
        f"<p style='font-size: 0.95em; color: #555; opacity: 0.8;'>📅 {display_date} | 📰 {news_item['source']} | 🌐 {news_item['language'].upper()}</p>",
        unsafe_allow_html=True
    )

    if news_item.get('url'):
        link_text = {"th": "เปิดลิงก์ข่าวต้นฉบับ", "en": "Open Original News Link", "ko": "원본 뉴스 링크 열기", "jp": "元のニュースリンクを開く"}[lang]
        container.markdown(
            f"<p><a href='{news_item['url']}' target='_blank' style='color: #007bff; text-decoration: none; font-weight: bold;'>🔗 {link_text}</a></p>",
            unsafe_allow_html=True
        )

    content_text = {"th": "เนื้อหาข่าว", "en": "News Content", "ko": "뉴스 내용", "jp": "뉴스 내용"}[lang]
    container.markdown(f"### {content_text}")
    container.markdown(f"<p>{news_item.get('content', 'Content not available.')}</p>", unsafe_allow_html=True)
# --- END: โค้ดที่นำกลับเข้ามา ---


def show():
    lang = st.session_state.get('language', 'th')
    if 'view_news_id' not in st.session_state: st.session_state.view_news_id = None
    if 'current_page' not in st.session_state: st.session_state.current_page = 1
    if 'items_per_page' not in st.session_state: st.session_state.items_per_page = 10
    if 'sort_order' not in st.session_state: st.session_state.sort_order = 'date_desc'
    if 'search_query' not in st.session_state: st.session_state.search_query = ''

    # --- START: โค้ดส่วนแสดงผลรายละเอียดข่าวที่นำกลับเข้ามา ---
    if st.session_state.view_news_id:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM epidemic_news WHERE id = %s", (st.session_state.view_news_id,))
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                if rows:
                    news_df_detail = pd.DataFrame(rows, columns=columns)
                    news_item_detail = news_df_detail.iloc[0].to_dict()
                    
                    lang_item = {
                        'id': news_item_detail['id'], 'source': news_item_detail['source'],
                        'url': news_item_detail['url'], 'date': news_item_detail['date'],
                        'language': news_item_detail['language'],
                        'title': news_item_detail.get(f'title_{lang}'),
                        'summary': news_item_detail.get(f'summary_{lang}'),
                        'hashtags': parse_hashtags(news_item_detail.get(f'hashtags_{lang}')),
                        'content': news_item_detail.get('content_raw') if lang == 'th' else news_item_detail.get(f'content_translated_{lang}')
                    }
                    display_news_detail(st, lang_item, lang)
                else:
                    st.warning("ไม่พบข่าวที่ต้องการ (ID: {st.session_state.view_news_id})")
                    st.session_state.view_news_id = None
            except Exception as e:
                st.error(f"Error fetching news detail: {e}")
            finally:
                conn.close()
        return # จบการทำงานของหน้า home ที่นี่เมื่อแสดงรายละเอียด
    # --- END: โค้ดส่วนแสดงผลรายละเอียดข่าว ---


    st.title({"th": "หน้าแรก - ข่าวโรคระบาด", "en": "Home - Epidemic News", "ko": "홈 - 전염병 뉴스", "jp": "ホーム - 感染症ニュース"}[lang])
    st.markdown({"th": "ภาพรวมข่าวสารล่าสุดเกี่ยวกับโรคระบาดที่รวบรวมจากหลายแหล่งข่าว", "en": "Latest epidemic news overview from various sources", "ko": "다양한 출처의 최신 전염병 뉴스 개요", "jp": "さまざまな情報源からの最新の感染症ニュースの概要"}[lang])

    with st.container():
        stats = fetch_summary_stats()
        metric_cols = st.columns(3)
        metric_cols[0].metric(label={"th": "ข่าวทั้งหมด", "en": "Total News", "ko": "총 뉴스", "jp": "全ニュース"}[lang], value=stats["total_news"])
        metric_cols[1].metric(label={"th": "ข่าวใน 7 วันล่าสุด", "en": "News Last 7 Days", "ko": "지난 7일간의 뉴스", "jp": "過去7日間のニュース"}[lang], value=stats["news_last_7_days"])
        metric_cols[2].metric(label={"th": "จำนวนแหล่งข่าว", "en": "Total Sources", "ko": "총 출처 수", "jp": "情報源の総数"}[lang], value=stats["total_sources"])
        
        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

        control_cols = st.columns([2, 1, 1])
        with control_cols[0]:
            search_query = st.text_input("Search", value=st.session_state.search_query, key="news_search", label_visibility="collapsed", placeholder={"th": "🔍 ค้นหาหัวข้อข่าว...", "en": "🔍 Search news headlines...", "ko": "🔍 뉴스 헤드라인 검색...", "jp": "🔍 ニュースの見出しを検索..."}[lang])
        with control_cols[1]:
            sort_order = st.selectbox("Sort", options=['date_desc', 'date_asc', 'title_asc', 'title_desc'], format_func=lambda x: {"date_desc": {"th": "วันที่ (ใหม่สุด)", "en": "Date (Newest)", "ko": "날짜 (최신)", "jp": "日付 (最新)"}[lang], "date_asc": {"th": "วันที่ (เก่าสุด)", "en": "Date (Oldest)", "ko": "날짜 (오래된)", "jp": "日付 (古い)"}[lang], "title_asc": {"th": "หัวข้อ (ก-ฮ)", "en": "Title (A-Z)", "ko": "제목 (가-하)", "jp": "タイトル (あ-ん)"}[lang], "title_desc": {"th": "หัวข้อ (ฮ-ก)", "en": "Title (Z-A)", "ko": "제목 (하-가)", "jp": "タイトル (ん-あ)"}[lang]}[x], index=0, key="news_sort", label_visibility="collapsed")
        with control_cols[2]:
            items_per_page = st.selectbox("Show", options=[10, 20, 50], index=[10, 20, 50].index(st.session_state.items_per_page) if st.session_state.items_per_page in [10, 20, 50] else 0, key="items_per_page_select", label_visibility="collapsed")

    if search_query != st.session_state.search_query or sort_order != st.session_state.sort_order or items_per_page != st.session_state.items_per_page:
        st.session_state.search_query, st.session_state.sort_order, st.session_state.items_per_page, st.session_state.current_page = search_query, sort_order, items_per_page, 1
        st.rerun()

    offset = (st.session_state.current_page - 1) * st.session_state.items_per_page
    news_df = fetch_news(lang=lang, limit=st.session_state.items_per_page, offset=offset, sort_by=st.session_state.sort_order, search_query=st.session_state.search_query)

    if news_df.empty:
        st.info({"th": "ไม่พบข่าวสาร", "en": "No news found", "ko": "뉴스를 찾을 수 없습니다", "jp": "ニュースが見つかりません"}[lang])
        return

    for idx, row in news_df.iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"### {row.get('title', 'ไม่มีหัวข้อ')}")
                st.markdown(f"<p style='font-size: 0.9em; color: #666;'>📅 {row['date'].strftime('%Y-%m-%d') if isinstance(row['date'], datetime) else row['date']} | 📰 {row['source']} | 🌐 {row['language'].upper()}</p>", unsafe_allow_html=True)
                hashtags = row.get("hashtags", [])
                if hashtags:
                    formatted_tags = "".join(f"<span class='tag-bubble'>#{tag}</span>" for tag in hashtags)
                    st.markdown(f"<div style='margin-top: 8px; margin-bottom: 12px;'>{formatted_tags}</div>", unsafe_allow_html=True)
                summary_content = row.get("summary")
                if summary_content: st.markdown(f"<p>{summary_content}</p>", unsafe_allow_html=True)
            with col2:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if st.button({"th": "อ่านเพิ่มเติม", "en": "Read More", "ko": "더 보기", "jp": "続きを読む"}[lang], key=f"read_more_{row['id']}", use_container_width=True):
                    st.session_state.view_news_id = row['id']
                    st.rerun()

    total_count = get_total_news_count(lang, st.session_state.search_query)
    total_pages = (total_count + st.session_state.items_per_page - 1) // st.session_state.items_per_page
    if total_pages > 1:
        st.markdown("---")
        p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
        prev_label, next_label = {"th": "ก่อนหน้า", "en": "Previous", "ko": "이전", "jp": "前へ"}[lang], {"th": "ถัดไป", "en": "Next", "ko": "다음", "jp": "次へ"}[lang]
        if p_col1.button(f"⬅️ {prev_label}", disabled=st.session_state.current_page <= 1):
            st.session_state.current_page -= 1
            st.rerun()
        p_col2.markdown(f"<div style='text-align: center; padding-top: 10px;'>{st.session_state.current_page} / {total_pages}</div>", unsafe_allow_html=True)
        if p_col3.button(f"{next_label} ➡️", disabled=st.session_state.current_page >= total_pages):
            st.session_state.current_page += 1
            st.rerun()