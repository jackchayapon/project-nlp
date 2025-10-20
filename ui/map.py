# ui/map.py
import streamlit as st
import folium
from streamlit_folium import st_folium
import psycopg2
import pandas as pd
import os
from datetime import datetime
import json
from .location_data import LOCATION_COORDINATES # Relative import for module within the same package
from folium.plugins import MarkerCluster, MiniMap
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection to external Neon database
DB_URI = "postgresql://neondb_owner:npg_o6AY4XRynVZK@ep-wandering-grass-a1ha7u59-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

def get_db_connection():
    """Get database connection to external Neon database"""
    try:
        return psycopg2.connect(DB_URI)
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อฐานข้อมูล: {e}")
        return None

@st.cache_data(ttl=1800)
def fetch_all_news_for_risk_assessment():
    """ดึงข้อมูลข่าวทั้งหมดที่จำเป็นสำหรับการประเมินความเสี่ยง"""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()

    try:
        cursor = conn.cursor()
        query = """
            SELECT
                id,
                title_th, title_en, title_ko, title_jp,
                content_raw,
                content_translated_th, content_translated_en, content_translated_ko, content_translated_jp,
                date,
                source,
                url,
                summary_th, summary_en, summary_ko, summary_jp,
                hashtags_th, hashtags_en, hashtags_ko, hashtags_jp
            FROM epidemic_news
            ORDER BY date DESC;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        news_df = pd.DataFrame(rows, columns=columns)
        return news_df
    except Exception as e:
        logger.error(f"Error fetching all news data for risk assessment: {e}")
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลข่าวสำหรับการประเมินความเสี่ยง: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            cursor.close()
            conn.close()

def parse_hashtags(value):
    """Parses hashtag strings from various formats into a list."""
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            if value.startswith('{') and value.endswith('}'):
                tags = value.strip('{}').split(',')
                return [tag.strip().strip('"') for tag in tags if tag.strip()]
    return []

def extract_province_risk_from_content(news_df, current_lang='th'):
    """ดึงระดับความเสี่ยงตามจังหวัดในประเทศไทยโดยอิงจากการวิเคราะห์เนื้อหาและแฮชแท็ก"""
    province_risk = {}

    all_content_fields = ['content_raw', 'content_translated_th', 'content_translated_en', 'content_translated_ko', 'content_translated_jp']
    all_hashtag_fields = ['hashtags_th', 'hashtags_en', 'hashtags_ko', 'hashtags_jp']

    for _, row in news_df.iterrows():
        matched_provinces = set()
        
        full_text_to_search = " ".join([str(row.get(field, '')) for field in all_content_fields]).lower()

        for location_name in LOCATION_COORDINATES:
            if location_name.lower() in full_text_to_search:
                matched_provinces.add(location_name)

        for hashtag_field in all_hashtag_fields:
            hashtags = parse_hashtags(row.get(hashtag_field))
            for tag in hashtags:
                tag_clean = str(tag).lower().strip()
                for location_name in LOCATION_COORDINATES:
                    if tag_clean == location_name.lower():
                        matched_provinces.add(location_name)

        for matched_province in matched_provinces:
            if matched_province not in province_risk:
                province_risk[matched_province] = {
                    'lat': LOCATION_COORDINATES[matched_province]['lat'],
                    'lng': LOCATION_COORDINATES[matched_province]['lng'],
                    'news_count': 0,
                    'news_items': [],
                    'risk_keywords': set()
                }

            province_risk[matched_province]['news_count'] += 1
            
            news_item_for_popup = {
                'id': row.get('id'),
                'title': row.get(f'title_{current_lang}') or row.get('title_th'),
                'summary': row.get(f'summary_{current_lang}') or row.get('summary_th'),
                'date': row.get('date'),
                'source': row.get('source'),
                'url': row.get('url')
            }
            if not any(d['id'] == news_item_for_popup['id'] for d in province_risk[matched_province]['news_items']):
                province_risk[matched_province]['news_items'].append(news_item_for_popup)

            for hashtag_field in all_hashtag_fields:
                hashtags_list = parse_hashtags(row.get(hashtag_field))
                if hashtags_list:
                    province_risk[matched_province]['risk_keywords'].update(hashtags_list)

    for province, data in province_risk.items():
        data['news_items'].sort(key=lambda x: x['date'], reverse=True)

    return province_risk

def create_enhanced_risk_map(province_risk_data, lang='th'):
    """สร้างแผนที่แบบโต้ตอบพร้อมตัวบ่งชี้ความเสี่ยงตามการวิเคราะห์ตำแหน่ง"""
    center_lat, center_lng = 13.7563, 100.5018
    m = folium.Map(location=[center_lat, center_lng], zoom_start=6, tiles='CartoDB positron')

    labels = {
        'th': {'risk_level': 'ระดับความเสี่ยง', 'news_count': 'จำนวนข่าว', 'latest_news': 'ข่าวล่าสุด', 'related_hashtags': 'Hashtag ที่เกี่ยวข้อง', 'high': 'สูง', 'medium': 'ปานกลาง', 'low': 'ต่ำ'},
        'en': {'risk_level': 'Risk Level', 'news_count': 'News Count', 'latest_news': 'Latest News', 'related_hashtags': 'Related Hashtags', 'high': 'High', 'medium': 'Medium', 'low': 'Low'},
        'ko': {'risk_level': '위험 수준', 'news_count': '뉴스 수', 'latest_news': '최신 뉴스', 'related_hashtags': '관련 해시태그', 'high': '높음', 'medium': '중간', 'low': '낮음'},
        'jp': {'risk_level': 'リスクレベル', 'news_count': 'ニュース数', 'latest_news': '最新ニュース', 'related_hashtags': '関連ハッシュタグ', 'high': '高', 'medium': '中', 'low': '低'}
    }
    current_labels = labels.get(lang, labels['th'])

    marker_cluster = MarkerCluster().add_to(m)

    for province, risk_data in province_risk_data.items():
        news_count = risk_data['news_count']
        if news_count >= 5:
            risk_level, marker_color = 'high', '#dc3545'
        elif news_count >= 2:
            risk_level, marker_color = 'medium', '#ffc107'
        else:
            risk_level, marker_color = 'low', '#28a745'

        latest_news = risk_data['news_items'][:3]
        news_html = ""
        for news in latest_news:
            title = news.get('title', 'N/A')
            summary = news.get('summary', '')
            date_str = news['date'].strftime('%Y-%m-%d') if hasattr(news['date'], 'strftime') else 'N/A'
            source_link = f"<a href='{news['url']}' target='_blank' style='color: #007bff;'>{news.get('source', 'N/A')}</a>" if news.get('url') else news.get('source', 'N/A')
            news_html += f"<b>{title}</b><br><small>{summary[:100]}...</small><br><small>({date_str} | {source_link})</small><hr style='margin: 5px 0;'>"
        
        if not news_html:
            news_html = "<p>ไม่พบข้อมูลข่าว</p>"

        hashtags = list(risk_data.get('risk_keywords', set()))[:7]
        hashtags_html = "".join(f"<span style='display: inline-block; background-color: #e0f2f7; color: #007bff; padding: 3px 8px; border-radius: 12px; font-size: 0.8em; margin: 2px;'>#{tag}</span>" for tag in hashtags if tag)
        if not hashtags_html:
            hashtags_html = "<p>ไม่มี Hashtag</p>"

        popup_content = f"""
        <div style="width: 300px; font-family: 'Inter', sans-serif;">
            <h4>{province}</h4>
            <p><strong>{current_labels['risk_level']}:</strong> {current_labels[risk_level]} ({news_count} {current_labels['news_count']})</p>
            <hr>
            <p><strong>{current_labels['latest_news']}:</strong></p>
            <div style="font-size: 0.9em; max-height: 150px; overflow-y: auto;">{news_html}</div>
            <hr>
            <p><strong>{current_labels['related_hashtags']}:</strong></p>
            <div style="max-height: 80px; overflow-y: auto;">{hashtags_html}</div>
        </div>
        """
        tooltip_text = f"{province} - {current_labels['risk_level']}: {current_labels[risk_level]}"

        folium.CircleMarker(
            location=[risk_data['lat'], risk_data['lng']],
            radius=6 + (news_count * 1.5),
            popup=folium.Popup(popup_content, max_width=350),
            color=marker_color,
            fill=True,
            fillColor=marker_color,
            fillOpacity=0.7,
            weight=1,
            tooltip=tooltip_text
        ).add_to(marker_cluster)

    MiniMap().add_to(m)
    folium.LayerControl().add_to(m)
    return m

def show():
    """แสดงหน้าแผนที่พร้อมการแสดงภาพความเสี่ยงที่ได้รับการปรับปรุง"""
    lang = st.session_state.get('language', 'th')

    st.title({"th": "🗺️ แผนที่ความเสี่ยง", "en": "🗺️ Risk Map", "ko": "🗺️ 위험 지도", "jp": "🗺️ リスクマップ"}[lang])
    st.markdown({"th": "แผนที่แสดงระดับความเสี่ยงของการระบาดโรคในแต่ละจังหวัดของประเทศไทย", "en": "Map showing epidemic risk levels in each province of Thailand", "ko": "태국 각 주의 전염병 위험 수준을 보여주는 지도", "jp": "タイの各県の感染症リスクレベルを示すマップ"}[lang])

    news_df_for_risk = fetch_all_news_for_risk_assessment()

    if news_df_for_risk.empty:
        st.warning({"th": "ไม่พบข้อมูลข่าวสารสำหรับประเมินความเสี่ยง", "en": "No news data found for risk assessment", "ko": "위험 평가를 위한 뉴스 데이터를 찾을 수 없습니다", "jp": "リスク評価のためのニュースデータが見つかりません"}[lang])
        return

    province_risk_data = extract_province_risk_from_content(news_df_for_risk, lang)

    if not province_risk_data:
        st.info({"th": "ไม่พบข้อมูลความเสี่ยงจากข่าวสารที่ระบุตำแหน่ง", "en": "No risk data found from location mentions in news", "ko": "뉴스에서 위치 언급으로 인한 위험 데이터를 찾을 수 없습니다", "jp": "ニュース内の位置情報からリスクデータが見つかりません"}[lang])
        return

    risk_map = create_enhanced_risk_map(province_risk_data, lang)
    
    # --- START: โค้ดที่แก้ไข ---
    # เปลี่ยนจาก width=700 เป็น use_container_width=True เพื่อให้แผนที่ขยายเต็มความกว้าง
    st_folium(risk_map, use_container_width=True, height=500)
    # --- END: โค้ดที่แก้ไข ---

    st.markdown("---")
    st.subheader({"th": "📊 สถิติความเสี่ยง", "en": "📊 Risk Statistics", "ko": "📊 위험 통계", "jp": "📊 リスク統計"}[lang])

    col1, col2, col3 = st.columns(3)
    high_risk = sum(1 for data in province_risk_data.values() if data['news_count'] >= 5)
    medium_risk = sum(1 for data in province_risk_data.values() if 2 <= data['news_count'] < 5)
    low_risk = sum(1 for data in province_risk_data.values() if data['news_count'] < 2)

    with col1:
        st.metric({"th": "ความเสี่ยงสูง", "en": "High Risk", "ko": "높은 위험", "jp": "高リスク"}[lang], high_risk)
    with col2:
        st.metric({"th": "ความเสี่ยงปานกลาง", "en": "Medium Risk", "ko": "중간 위험", "jp": "中リスク"}[lang], medium_risk)
    with col3:
        st.metric({"th": "ความเสี่ยงต่ำ", "en": "Low Risk", "ko": "낮은 위험", "jp": "低リスク"}[lang], low_risk)