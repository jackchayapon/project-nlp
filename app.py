# app.py
import streamlit as st
from streamlit_option_menu import option_menu
from ui.home import show as home_show
from ui.map import show as map_show
from ui.setting import show as setting_show
from ui.chatbot import show as chat_show  

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(page_title="Epidemic News", page_icon="🦠", layout="wide", initial_sidebar_state="expanded")

    if 'language' not in st.session_state:
        st.session_state.language = 'th'

    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+Thai&family=Noto+Sans+JP&family=Noto+Sans+KR&display=swap');
            html, body, [class*="st-emotion"] { font-family: 'Inter', 'Noto Sans Thai', 'Noto Sans JP', 'Noto Sans KR', sans-serif; }
            @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
            .main [data-testid="stVerticalBlockBorderWrapper"] { opacity: 0; animation: fadeInUp 0.6s ease-out forwards; animation-delay: 0.1s; }
            [data-testid="stAppViewContainer"] { background-color: #EAF2FA; }
            [data-testid="stButton"] > button {
                background-color: #1976D2; color: white; border: 1px solid #1976D2;
                border-radius: 8px; transition: all 0.2s;
            }
            [data-testid="stButton"] > button:hover { background-color: #FFFFFF; color: #1976D2; border: 1px solid #1976D2; }
            [data-testid="stButton"] > button:disabled { background-color: #B0BEC5; color: #F5F5F5; border: 1px solid #B0BEC5; }
            .st-emotion-cache-z5fcl4 { padding: 2rem; }
            .tag-bubble {
                display: inline-block; background-color: #e0f7fa; color: #00796b; border-radius: 15px;
                padding: 5px 10px; margin-right: 5px; margin-bottom: 5px; font-size: 0.8em; white-space: nowrap;
            }
            h1 { color: #0D47A1; }
            .main .st-emotion-cache-z5fcl4 > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"]:first-child > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"]:first-child {
                background-color: #FFFFFF; border: 1px solid #D1E1FF; border-radius: 12px; padding: 1.5rem;
            }
            [data-testid="stHorizontalBlock"] { border-top: 1px solid #D1E1FF !important; }
        </style>
        """,
        unsafe_allow_html=True)

    with st.sidebar:
        # ✅ เพิ่ม "Chatbot" เข้าไปใน options
        selected = option_menu(
            menu_title="Epidemic News",
            options=[
                {"th": "หน้าแรก", "en": "Home", "ko": "홈", "jp": "ホーム"}[st.session_state.language],
                {"th": "แผนที่", "en": "Map", "ko": "지도", "jp": "マップ"}[st.session_state.language],
                {"th": "แชทบอท", "en": "Chatbot", "ko": "챗봇", "jp": "チャットボット"}[st.session_state.language],
                {"th": "ตั้งค่า", "en": "Settings", "ko": "설정", "jp": "設定"}[st.session_state.language],
            ],
            icons=["house", "map", "chat-dots", "gear"],  # ✅ ไอคอนครบ 4 รายการ
            menu_icon=None, default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#FFFFFF"},
                "icon": {"color": "#0D47A1", "font-size": "20px"},
                "nav-link": {"font-size": "16px", "font-weight": "500", "text-align": "left", "margin": "0px", "--hover-color": "#E3F2FD", "color": "#374151"},
                "nav-link-selected": {"background-color": "#1976D2", "color": "white", "font-weight": "600"},
                "menu-title": {"color": "#FFFFFF", "font-size": "24px", "font-weight": "600", "background-color": "#0D47A1", "padding": "1rem 1.5rem", "margin": "0"}
            }
        )

        st.markdown("---")
        language_options = {'th': '🇹🇭 ไทย', 'en': '🇺🇸 English', 'ko': '🇰🇷 한국어', 'jp': '🇯🇵 日本語'}
        display_options = list(language_options.values())
        default_index = list(language_options.keys()).index(st.session_state.language)
        selected_language_display = st.selectbox(
            label={"th": "เลือกภาษา", "en": "Select Language", "ko": "언어 선택", "jp": "言語選択"}[st.session_state.language],
            options=display_options, index=default_index, key="language_selector"
        )
        for lang_code, display_name in language_options.items():
            if display_name == selected_language_display and st.session_state.language != lang_code:
                st.session_state.language = lang_code
                st.rerun()

        st.markdown("---")
        with st.sidebar.expander("📞 เบอร์โทรศัพท์ฉุกเฉิน", expanded=True):
            st.markdown(
                """
                <ul style="font-size: 14px; list-style-position: inside; padding-left: 0; margin: 0;">
                    <li style="margin-bottom: 5px;"><strong>1669:</strong> เจ็บป่วยฉุกเฉิน (ทั่วประเทศ)</li>
                    <li style="margin-bottom: 5px;"><strong>1422:</strong> กรมควบคุมโรค (ปรึกษาโรคติดต่อ)</li>
                    <li style="margin-bottom: 5px;"><strong>1330:</strong> สายด่วน สปสช. (สิทธิบัตรทอง)</li>
                    <li><strong>191:</strong> แจ้งเหตุด่วน-เหตุร้าย</li>
                </ul>
                """, unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("**App Version:** 1.0.0")
        st.markdown(f"**Current Language:** {st.session_state.language.upper()}")

    # ✅ เส้นทางไปแต่ละหน้า (สังเกต indent ของแต่ละบล็อก)
    if selected == {"th": "หน้าแรก", "en": "Home", "ko": "홈", "jp": "ホーム"}[st.session_state.language]:
        home_show()
    elif selected == {"th": "แผนที่", "en": "Map", "ko": "지도", "jp": "マップ"}[st.session_state.language]:
        map_show()
    elif selected == {"th": "แชทบอท", "en": "Chatbot", "ko": "챗봇", "jp": "チャットボット"}[st.session_state.language]:
        chat_show()  # ✅ ต้อง indent ใต้ elif เสมอ
    elif selected == {"th": "ตั้งค่า", "en": "Settings", "ko": "설정", "jp": "設定"}[st.session_state.language]:
        setting_show()

if __name__ == "__main__":
    main()
