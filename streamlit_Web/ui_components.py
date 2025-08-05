import streamlit as st
from datetime import datetime, timedelta
from utils import get_image_as_base64
import os
import pandas as pd
import requests
import base64

def fetch_image_as_base64(url):
    """이미지 URL을 요청해 base64로 인코딩된 문자열 반환"""
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode()
    except:
        return None

def render_header():
    """
    애플리케이션의 헤더(로고와 제목)를 렌더링합니다.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(current_dir, "data", "HelloHome_ICON_투명.png")
    logo_base64 = get_image_as_base64(logo_path)

    st.markdown(f"""
    <div style="text-align: center; padding: 2rem 0 2.5rem 0;">
        <div style='display: flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;'>
            {f'<img src="data:image/png;base64,{logo_base64}" style="height: 4.1rem; margin-right: 15px;">' if logo_base64 else ''}
            <h1 style='color: #212529; font-weight: 800; font-size: 4.1rem; margin: 0;'>Hello Home</h1>
        </div>
        <p style='color: #495057; font-size: 1.25rem; margin: 0;'>
            전국 보호소의 유기동물 정보를 확인하고, 따뜻한 가족이 되어주세요.
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar(sido_list):
    """
    사이드바 필터를 렌더링합니다. 필터 값은 st.session_state를 통해 관리됩니다.
    """
    st.sidebar.header("🔍 검색 및 필터")

    # 시도 변경 시 시군구 선택을 초기화하는 콜백 함수
    def on_sido_change():
        st.session_state.sigungu_filter = "전체"

    with st.sidebar.expander("🗓️ 공고일 기준 검색", expanded=True):
        st.date_input("시작일", key="start_date")
        st.date_input("종료일", key="end_date")

    with st.sidebar.expander("🐾 축종 선택", expanded=True):
        st.multiselect(
            "축종 선택",
            options=["개", "고양이", "기타"],
            key="species_filter",
            help="선택하지 않으면 전체 축종이 포함됩니다."
        )

    sido_names = ["전체"] + [s['name'] for s in sido_list]
    with st.sidebar.expander("📍 지역 선택", expanded=True):
        st.selectbox("시도 선택", sido_names, key="sido_filter", on_change=on_sido_change)
        
        if st.session_state.sido_filter != "전체":
            selected_sido_code = next((s['code'] for s in sido_list if s['name'] == st.session_state.sido_filter), None)
            if selected_sido_code:
                from data_manager import get_sigungu_list
                sigungu_list = get_sigungu_list(selected_sido_code)
                sigungu_names = ["전체"] + [s['name'] for s in sigungu_list]
                st.selectbox("시군구 선택", sigungu_names, key="sigungu_filter")

def render_kpi_cards(shelter_count, animal_count, long_term_count, adopted_count):
    """
    KPI 카드를 렌더링합니다.
    """
    st.write("""<div style="height: 1.5rem;"></div>""", unsafe_allow_html=True)
    kpi_cols = st.columns(4)
    kpi_data = [
        ("🏠", "보호소 수", shelter_count),
        ("🐾", "보호 동물 수", animal_count),
        ("⏳", "장기 보호 동물", long_term_count),
        ("❤️", "입양 완료", adopted_count)
    ]

    for col, (icon, title, number) in zip(kpi_cols, kpi_data):
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="icon">{icon}</div>
                <div class="title">{title}</div>
                <div class="number">{number}</div>
            </div>
            """, unsafe_allow_html=True)
    st.write("""<div style="height: 1rem;"></div>""", unsafe_allow_html=True)

def render_tabs(tabs):
    """
    애플리케이션의 메인 탭을 렌더링하고 현재 활성화된 탭을 반환합니다.
    """
    original_labels = [tab["label"] for tab in tabs]
    favorites_count = len(st.session_state.get('favorites', []))

    def format_label(label):
        if "찜한 동물" in label:
            return f"❤️ 찜한 동물 ({favorites_count})"
        return label

    # st.radio가 직접 상태를 관리하도록 key를 사용합니다.
    # active_tab_label 세션 상태는 선택된 탭의 "고정된" 이름을 저장합니다.
    if 'active_tab_label' not in st.session_state:
        st.session_state.active_tab_label = original_labels[0]

    selected_label = st.radio(
        "탭 선택",
        options=original_labels,      # 내부적으로는 고정된 라벨 목록을 사용
        key='active_tab_label',         # 상태 저장을 위해 고유 키를 사용
        format_func=format_label,       # 사용자에게 보여줄 형식을 지정
        horizontal=True,
        label_visibility="collapsed"
    )
    
    # st.radio는 선택된 옵션의 실제 값(고정된 라벨)을 반환합니다.
    active_tab_idx = original_labels.index(selected_label)
    return tabs[active_tab_idx]

def handle_favorite_button(animal: pd.Series, context: str):
    """찜하기 버튼의 상태를 관리하고 로직을 처리합니다."""
    if 'desertion_no' in animal and pd.notna(animal['desertion_no']):
        is_favorited = animal['desertion_no'] in st.session_state.favorites
        button_text = "❤️ 찜 취소" if is_favorited else "🤍 찜하기"
        if st.button(button_text, key=f"fav_{context}_{animal['desertion_no']}"):
            if is_favorited:
                st.session_state.favorites.remove(animal['desertion_no'])
            else:
                st.session_state.favorites.append(animal['desertion_no'])
            st.rerun()

def render_animal_card(animal: pd.Series, context: str, show_shelter: bool = False):
    """개별 동물 정보를 카드 형태로 렌더링합니다. (base64 프록시 렌더링 방식)"""
    cols = st.columns([1, 3])
    with cols[0]:
        display_name = animal.get('kind_name', animal.get('notice_no', '이름 없음'))
        image_url = animal.get("image_url")

        if pd.isna(image_url):
            st.image("https://via.placeholder.com/150?text=사진+없음", width=150)
        else:
            img_b64 = fetch_image_as_base64(image_url)
            if img_b64:
                st.image(f"data:image/jpeg;base64,{img_b64}", width=150, caption=display_name)
            else:
                st.image("https://via.placeholder.com/150?text=사진+없음", width=150)

    with cols[1]:
        handle_favorite_button(animal, context)
        
        age_info = animal.get('age', '정보 없음')
        weight_info = animal.get('weight', '정보 없음')
        sex_info = animal.get('sex', 'U')

        st.markdown(f"**{display_name}** ({age_info}, {weight_info})")
        if show_shelter:
            st.markdown(f"**🏠 보호소:** {animal.get('shelter_name', '정보 없음')}")
        sex_display = {'F': "♀️ 암컷", 'M': "♂️ 수컷"}.get(sex_info, "성별 미상")
        st.markdown(f"**성별:** {sex_display}")
        st.markdown(f"**🐾 특징:** {animal.get('special_mark', '정보 없음')}")
        st.markdown(f"**📍 발견 장소:** {animal.get('happen_place', '정보 없음')}")

    st.markdown("---")

def render_download_button(df: pd.DataFrame, shelter_name: str):
    """데이터 다운로드 버튼을 렌더링합니다."""
    st.download_button(
        label="📥 선택된 보호소 동물 목록 다운로드 (CSV)",
        data=df.to_csv(index=False).encode('utf-8-sig'),
        file_name=f"{shelter_name}_animals.csv",
        mime="text/csv"
    )

def inject_custom_css():
    """
    애플리케이션에 적용할 커스텀 CSS를 주입합니다.
    """
    st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
    
    /* --- General & Body --- */
    .stApp {
        background-color: #FAF8F0; /* Warm Ivory Background */
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* --- Main Content Area --- */
    .block-container {
        padding: 2rem 3rem 3rem 3rem !important;
    }

    /* --- Sidebar --- */
    [data-testid="stSidebar"] {
        background-color: #F5F1E9; /* Soft Beige Sidebar */
        border-right: 1px solid #E0DBCF;
    }
    [data-testid="stSidebar"] h2 {
        color: #B58A60; /* Warm Brown Accent */
        font-weight: 700;
    }
    [data-testid="stExpander"] summary {
        font-weight: 600;
        color: #B58A60;
    }
    
    /* --- MultiSelect (축종 선택) & General Input Accent --- */
    span[data-baseweb="tag"] {
        background-color: #B58A60 !important;
        color: #FFFFFF !important;
        border-radius: 0.75rem;
    }
    /* This targets the native radio button dot/check */
    input[type="radio"] {
        accent-color: #B58A60 !important;
    }

    /* --- KPI Cards --- */
    .kpi-card {
        background-color: #FFFFFF;
        padding: 1.75rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.06);
        text-align: center;
        transition: all 0.3s ease-in-out;
        border-bottom: 4px solid #B58A60;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .kpi-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 12px 25px rgba(0, 0, 0, 0.1);
    }
    .kpi-card .icon { font-size: 2.8rem; line-height: 1; margin-bottom: 0.75rem; }
    .kpi-card .title { font-size: 1.05rem; font-weight: 500; color: #6C757D; margin-bottom: 0.5rem; }
    .kpi-card .number { font-size: 2.2rem; font-weight: 700; color: #343A40; }

    /* --- Tab Navigation (stRadio) --- */
    div[role="radiogroup"] {
        display: flex;
        justify-content: center;
        margin: 2.5rem 0 2rem 0;
        gap: 1rem;
    }
    div[role="radiogroup"] > label {
        display: inline-block;
        padding: 0.75rem 1.75rem;
        background: #FFFFFF;
        color: #495057;
        border-radius: 30px;
        cursor: pointer;
        transition: all 0.3s ease;
        border: 1px solid #DEE2E6;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        font-weight: 600;
    }
    /* Tab Hover */
    div[role="radiogroup"] > label:hover {
        background-color: #F5F1E9;
        border-color: #B58A60;
        color: #B58A60;
    }
    /* Selected tab style */
    div[role="radiogroup"] > label:has(input:checked) {
        background-color: #F5F1E9; /* Soft Beige, same as hover */
        color: #B58A60; /* Warm Brown Text */
        border: 2px solid #B58A60; /* Thicker Warm Brown Border */
        box-shadow: 0 5px 15px rgba(181, 138, 96, 0.4);
        padding: calc(0.75rem - 1px) calc(1.75rem - 1px); /* Adjust padding to keep size consistent */
    }
    /* Hide the actual radio button and its focus ring */
    div[role="radiogroup"] input[type="radio"] {
        display: none; /* This is the key to the button look */
    }
    /* Custom focus ring to override browser default (which can be red/blue) */
    div[role="radiogroup"] label:focus-within {
        outline: none;
        box-shadow: 0 0 0 2px #F5F1E9, 0 0 0 4px #B58A60;
    }
    
    /* --- Footer --- */
    .footer {
        text-align: center;
        margin-top: 4rem;
        color: #868E96;
        font-size: 0.9rem;
    }
    .footer a {
        color: #B58A60;
        text-decoration: none;
    }
    .footer a:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

def render_footer():
    """
    애플리케이션의 푸터를 렌더링합니다.
    """
    st.markdown("""
<hr style="margin-top: 3rem; border-top: 1px solid #E9ECEF;">
<div class="footer">
    Data provided by <a href="https://www.data.go.kr/" target="_blank">공공데이터포털</a> | Designed by Gemini
</div>
""", unsafe_allow_html=True)