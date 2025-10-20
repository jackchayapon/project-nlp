# ui/setting.py
import streamlit as st

def show():
    """Display the settings page with HealthWatch light theme."""
    
    # Get language from session state
    lang = st.session_state.get('language', 'th')
    
    # Page title based on language
    st.title({
        "th": "⚙️ ตั้งค่าแอปพลิเคชัน",
        "en": "⚙️ Application Settings",
        "ko": "⚙️ 애플리케이션 설정",
        "jp": "⚙️ アプリケーション設定"
    }[lang])
    
    st.markdown({
        "th": "ปรับแต่งการตั้งค่าต่างๆ ของแอปพลิเคชัน",
        "en": "Customize various application settings.",
        "ko": "다양한 애플리케이션 설정을 사용자 정의하세요.",
        "jp": "さまざまなアプリケーション設定をカスタマイズします。"
    }[lang])
    
    # Language Settings Section
    with st.container(border=True):
        st.markdown("### 🌐 " + {
            "th": "การตั้งค่าภาษา",
            "en": "Language Settings",
            "ko": "언어 설정",
            "jp": "言語設定"
        }[lang])
        
        # Language selector
        language_options = {
            'th': '🇹🇭 ไทย (Thai)',
            'en': '🇺🇸 English',
            'ko': '🇰🇷 한국어 (Korean)',
            'jp': '🇯🇵 日本語 (Japanese)'
        }
        
        selected_language = st.selectbox(
            {
                'th': "เลือกภาษาหลักของแอปพลิเคชัน:",
                'en': "Select application language:",
                'ko': "애플리케이션 언어 선택:",
                "jp": "アプリケーション言語を選択:"
            }[lang],
            options=list(language_options.keys()),
            format_func=lambda x: language_options[x],
            index=list(language_options.keys()).index(st.session_state.language),
            key="settings_language"
        )
        
        # Apply language change
        if selected_language != st.session_state.language:
            st.session_state.language = selected_language
            st.success("✅ " + (
                "ภาษาถูกเปลี่ยนแล้ว! หน้าจะรีโหลดอัตโนมัติ" if selected_language == 'th' else
                "Language changed! Page will reload automatically" if selected_language == 'en' else
                "언어가 변경되었습니다! 페이지가 자동으로 새로고침됩니다" if selected_language == 'ko' else
                "言語が変更されました！ページが自動的に再読み込みされます"
            ))
            st.rerun() # Changed from st.experimental_rerun()
    
    # Display Settings Section
    with st.container(border=True):
        st.markdown("### 📱 " + {
            "th": "การตั้งค่าการแสดงผล",
            "en": "Display Settings",
            "ko": "디스플레이 설정",
            "jp": "表示設定"
        }[lang])
        
        col1, col2 = st.columns(2)
        
        with col1:
            news_per_page = st.slider(
                {
                    'th': "จำนวนข่าวต่อหน้า:",
                    'en': "News per page:",
                    'ko': "페이지당 뉴스 수:",
                    'jp': "ページあたりのニュース数:"
                }[lang],
                min_value=10,
                max_value=100,
                value=st.session_state.get('items_per_page', 20), # Use session state for initial value
                step=10,
                key="news_per_page"
            )
            # Store in session state if it changes
            if 'items_per_page' not in st.session_state or st.session_state.items_per_page != news_per_page:
                st.session_state.items_per_page = news_per_page
        
        with col2:
            auto_expand_content = st.checkbox(
                {
                    'th': "ขยายเนื้อหาข่าวอัตโนมัติ",
                    "en": "Auto expand news content",
                    "ko": "뉴스 내용 자동 확장",
                    "jp": "ニュースコンテンツを自動展開"
                }[lang],
                value=st.session_state.get('auto_expand_content', False), # Use session state for initial value
                key="auto_expand"
            )
            # You might want to store this in session state too if it affects other pages
            if 'auto_expand_content' not in st.session_state or st.session_state.auto_expand_content != auto_expand_content:
                st.session_state.auto_expand_content = auto_expand_content
    
    # Map Settings Section
    with st.container(border=True):
        st.markdown("### 🗺️ " + {
            "th": "การตั้งค่าแผนที่",
            "en": "Map Settings",
            "ko": "지도 설정",
            "jp": "マップ設定"
        }[lang])
        
        col1, col2 = st.columns(2)
        
        with col1:
            default_map_center = st.selectbox(
                {
                    'th': "จุดกึ่งกลางแผนที่เริ่มต้น:",
                    'en': "Default map center:",
                    'ko': "기본 지도 중심:",
                    'jp': "デフォルトの地図の中心:"
                }[lang],
                options=["thailand", "global", "asia"],
                format_func=lambda x: {
                    "thailand": {"th": "ประเทศไทย", "en": "Thailand", "ko": "태국", "jp": "タイ"}[lang],
                    "global": {"th": "ทั่วโลก", "en": "Global", "ko": "전 세계", "jp": "世界"}[lang],
                    "asia": {"th": "ทวีปเอเชีย", "en": "Asia", "ko": "아시아", "jp": "아시아"}[lang]
                }[x],
                index=["thailand", "global", "asia"].index(st.session_state.get('default_map_center', 'thailand')), # Use session state for initial value
                key="map_center"
            )
            # Store in session state
            if 'default_map_center' not in st.session_state or st.session_state.default_map_center != default_map_center:
                st.session_state.default_map_center = default_map_center
        
        with col2:
            map_style = st.selectbox(
                {
                    'th': "รูปแบบแผนที่:",
                    'en': "Map style:",
                    'ko': "지도 스타일:",
                    'jp': "マップスタイル:"
                }[lang],
                options=["OpenStreetMap", "Stamen Terrain", "Stamen Toner"],
                index=["OpenStreetMap", "Stamen Terrain", "Stamen Toner"].index(st.session_state.get('map_style', 'OpenStreetMap')), # Use session state for initial value
                key="map_style"
            )
            # Store in session state
            if 'map_style' not in st.session_state or st.session_state.map_style != map_style:
                st.session_state.map_style = map_style
    
    # Notification Settings Section
    with st.container(border=True):
        st.markdown("### 🔔 " + {
            "th": "การตั้งค่าการแจ้งเตือน",
            "en": "Notification Settings",
            "ko": "알림 설정",
            "jp": "通知設定"
        }[lang])
        
        col1, col2 = st.columns(2)
        
        with col1:
            enable_alerts = st.checkbox(
                {
                    'th': "เปิดการแจ้งเตือนข่าวด่วน",
                    'en': "Enable breaking news alerts",
                    'ko': "속보 알림 활성화",
                    'jp': "速報アラートを有効にする"
                }[lang],
                value=st.session_state.get('enable_alerts', True), # Use session state for initial value
                key="enable_alerts"
            )
            # Store in session state
            if 'enable_alerts' not in st.session_state or st.session_state.enable_alerts != enable_alerts:
                st.session_state.enable_alerts = enable_alerts
        
        with col2:
            alert_keywords_options = ["ไข้หวัดนก", "โควิด-19", "มาลาเรีย", "ไข้เลือดออก", "วัณโรค"] if lang == 'th' else \
                                     ["Bird Flu", "COVID-19", "Malaria", "Dengue", "Tuberculosis"] if lang == 'en' else \
                                     ["조류독감", "코로나19", "말라리아", "뎅기열", "결핵"] if lang == 'ko' else \
                                     ["鳥インフルエンザ", "COVID-19", "マラリア", "デング熱", "結核"]
            alert_keywords_default = ["โควิด-19", "ไข้เลือดออก"] if lang == 'th' else \
                                     ["COVID-19", "Dengue"] if lang == 'en' else \
                                     ["코로나19", "뎅기열"] if lang == 'ko' else \
                                     ["COVID-19", "Dengue"]

            alert_keywords = st.multiselect(
                {
                    'th': "คำสำคัญสำหรับการแจ้งเตือน:",
                    'en': "Keywords for alerts:",
                    'ko': "알림 키워드:",
                    'jp': "アラートのキーワード:"
                }[lang],
                options=alert_keywords_options,
                default=st.session_state.get('alert_keywords', alert_keywords_default), # Use session state for initial value
                key="alert_keywords"
            )
            # Store in session state
            if 'alert_keywords' not in st.session_state or st.session_state.alert_keywords != alert_keywords:
                st.session_state.alert_keywords = alert_keywords
    
    # Data Settings Section
    with st.container(border=True):
        st.markdown("### 💾 " + {
            "th": "การตั้งค่าข้อมูล",
            "en": "Data Settings",
            "ko": "데이터 설정",
            "jp": "データ設定"
        }[lang])
        
        col1, col2 = st.columns(2)
        
        with col1:
            cache_duration = st.selectbox(
                {
                    'th': "ระยะเวลาแคชข้อมูล:",
                    'en': "Data cache duration:",
                    'ko': "데이터 캐시 지속 시간:",
                    'jp': "データキャッシュ期間:"
                }[lang],
                options=[30, 60, 180, 360],
                format_func=lambda x: f"{x} " + {
                    'th': "นาที",
                    'en': "minutes",
                    'ko': "분",
                    'jp': "분"
                }[lang],
                index=[30, 60, 180, 360].index(st.session_state.get('cache_duration', 60)), # Use session state for initial value
                key="cache_duration"
            )
            # Store in session state
            if 'cache_duration' not in st.session_state or st.session_state.cache_duration != cache_duration:
                st.session_state.cache_duration = cache_duration
        
        with col2:
            auto_refresh = st.checkbox(
                {
                    'th': "รีเฟรชข้อมูลอัตโนมัติ",
                    'en': "Auto-refresh data",
                    'ko': "데이터 자동 새로고침",
                    'jp': "データの自動更新"
                }[lang],
                value=st.session_state.get('auto_refresh', True), # Use session state for initial value
                key="auto_refresh"
            )
            # Store in session state
            if 'auto_refresh' not in st.session_state or st.session_state.auto_refresh != auto_refresh:
                st.session_state.auto_refresh = auto_refresh
    
    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button({
            "th": "💾 บันทึกการตั้งค่า",
            "en": "💾 Save Settings",
            "ko": "💾 설정 저장",
            "jp": "💾 設定を保存"
        }[lang], use_container_width=True):
            st.success("✅ " + (
                "การตั้งค่าถูกบันทึกแล้ว" if lang == 'th' else
                "Settings saved successfully" if lang == 'en' else
                "설정이 성공적으로 저장되었습니다" if lang == 'ko' else
                "設定が正常に保存されました"
            ))
            # You might want to save these settings to a database or file here
    
    with col2:
        if st.button({
            "th": "🔄 รีเซ็ตเป็นค่าเริ่มต้น",
            "en": "🔄 Reset to Default",
            "ko": "🔄 기본값으로 재설정",
            "jp": "🔄 デフォルトにリセット"
        }[lang], use_container_width=True):
            # Resetting session state variables to their default values
            if 'items_per_page' in st.session_state:
                del st.session_state.items_per_page
            if 'auto_expand_content' in st.session_state:
                del st.session_state.auto_expand_content
            if 'default_map_center' in st.session_state:
                del st.session_state.default_map_center
            if 'map_style' in st.session_state:
                del st.session_state.map_style
            if 'enable_alerts' in st.session_state:
                del st.session_state.enable_alerts
            if 'alert_keywords' in st.session_state:
                del st.session_state.alert_keywords
            if 'cache_duration' in st.session_state:
                del st.session_state.cache_duration
            if 'auto_refresh' in st.session_state:
                del st.session_state.auto_refresh
            
            st.info("🔄 " + (
                "การตั้งค่าถูกรีเซ็ตแล้ว" if lang == 'th' else
                "Settings reset to default" if lang == 'en' else
                "설정이 기본값으로 재설정되었습니다" if lang == 'ko' else
                "設定がデフォルトにリセットされました"
            ))
            st.rerun() # Changed from st.experimental_rerun()
    
    with col3:
        if st.button({
            "th": "📊 ส่งออกการตั้งค่า",
            "en": "📊 Export Settings",
            "ko": "📊 설정 내보내기",
            "jp": "📊 設定をエクスポート"
        }[lang], use_container_width=True):
            st.info("📊 " + (
                "ฟีเจอร์นี้จะพร้อมใช้งานในเร็วๆ นี้" if lang == 'th' else
                "This feature will be available soon" if lang == 'en' else
                "이 기능은 곧 사용할 수 있습니다" if lang == 'ko' else
                "この機能は近日中に利用可能になります"
            ))
    
    # System Information
    st.markdown("---")
    st.subheader({
        "th": "🔧 ข้อมูลระบบ",
        "en": "🔧 System Information",
        "ko": "🔧 시스템 정보",
        "jp": "🔧 システム情報"
    }[lang])
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            **{{"แอปพลิเคชัน" if lang == 'th' else "Application" if lang == 'en' else "애플리케이션" if lang == 'ko' else "アプリケーション"}}:** Epidemic News AI  
            **{{"เวอร์ชัน" if lang == 'th' else "Version" if lang == 'en' else "버전" if lang == 'ko' else "バージョン"}}:** v1.0.0  
            **{{"ภาษาปัจจุบัน" if lang == 'th' else "Current Language" if lang == 'en' else "현재 언어" if lang == 'ko' else "現在の言語"}}:** {language_options[lang]}
            """)
        
        with col2:
            st.markdown(f"""
            **{{"สถานะฐานข้อมูล" if lang == 'th' else "Database Status" if lang == 'en' else "데이터베이스 상태" if lang == 'ko' else "データベースステータス"}}:** <span style="color: #28a745; font-weight: bold;">{{"เชื่อมต่อ" if lang == 'th' else "Connected" if lang == 'en' else "연결됨" if lang == 'ko' else "接続済み"}}</span>  
            **{{"เซิร์ฟเวอร์" if lang == 'th' else "Server" if lang == 'en' else "서버" if lang == 'ko' else "サーバー"}}:** Streamlit  
            **{{"พอร์ต" if lang == 'th' else "Port" if lang == 'en' else "포트" if lang == 'ko' else "ポート"}}:** 5000
            """, unsafe_allow_html=True)
