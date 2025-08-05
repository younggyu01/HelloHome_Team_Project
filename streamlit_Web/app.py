import streamlit as st
from datetime import datetime, timedelta
from data_manager import init_db, get_sido_list, get_filtered_data
from ui_components import (
    render_header, 
    render_sidebar, 
    render_kpi_cards, 
    render_tabs, 
    inject_custom_css,
    render_footer
)
from tabs import map_view, analysis_dashboard_view, detail_view, favorites_view, prediction_view, web_scraping_view

# --- 1. 탭 설정 ---
TABS = [
    {"label": "📍 지도 & 분석", "show_func": map_view.show},
    {"label": "📊 분석 대시보드", "show_func": analysis_dashboard_view.show},
    {"label": "📋 보호소 상세 현황", "show_func": detail_view.show},
    {"label": "🔮 예측", "show_func": prediction_view.show},
    {"label": "❤️ 찜한 동물", "show_func": favorites_view.show},
    {"label": "🏵️ PIMFYVIRUS", "show_func": web_scraping_view.show}
]

from datetime import datetime, timedelta

def init_session_state():
    """세션 상태를 초기화합니다."""
    # 탭 상태 초기화
    if "active_tab_label" not in st.session_state:
        st.session_state.active_tab_label = "📍 지도 & 분석"
    if 'favorites' not in st.session_state:
        st.session_state.favorites = []

    # 필터 상태 초기화
    if "start_date" not in st.session_state:
        st.session_state.start_date = (datetime.now() - timedelta(days=30)).date()
    if "end_date" not in st.session_state:
        st.session_state.end_date = datetime.now().date()
    if "species_filter" not in st.session_state:
        st.session_state.species_filter = []
    if "sido_filter" not in st.session_state:
        st.session_state.sido_filter = "전체"
    if "sigungu_filter" not in st.session_state:
        st.session_state.sigungu_filter = "전체"
    if "selected_shelter" not in st.session_state:
        st.session_state.selected_shelter = None

def main():
    """메인 애플리케이션 실행 함수"""
    st.set_page_config(page_title="입양 대기 동물 분석", layout="wide")
    
    # --- 탭 전환 처리 ---
    if st.session_state.get("next_tab"):
        st.session_state.active_tab_label = st.session_state.next_tab
        del st.session_state.next_tab

    # --- 초기화 ---
    inject_custom_css()
    init_db()
    init_session_state()

    # --- UI 렌더링 ---
    render_header()
    sido_list = get_sido_list()
    render_sidebar(sido_list)

    # --- 데이터 로딩 및 필터링 ---
    with st.spinner("🐾 데이터를 열심히 불러오고 있어요... 잠시만 기다려주세요!"):
        # 상세 뷰에서는 필터를 무시하여 항상 선택된 보호소를 찾을 수 있도록 함
        data_sido, data_sigungu = st.session_state.sido_filter, st.session_state.sigungu_filter
        if st.session_state.active_tab_label == "📋 보호소 상세 현황":
            data_sido, data_sigungu = "전체", "전체"
        
        data = get_filtered_data(
            st.session_state.start_date, 
            st.session_state.end_date, 
            data_sido, 
            data_sigungu, 
            st.session_state.species_filter
        )
        final_animals, filtered_shelters, shelter_count, animal_count, long_term_count, adopted_count = data

    # --- 메인 콘텐츠 ---
    if final_animals.empty:
        st.info("🐾 해당 조건에 맞는 동물이 없습니다. 필터 조건을 변경해 보세요!", icon="ℹ️")
    else:
        render_kpi_cards(shelter_count, animal_count, long_term_count, adopted_count)
        
        active_tab = render_tabs(TABS)
        
        # 선택된 탭에 따라 적절한 인자를 전달하여 show 함수 호출
        if active_tab["label"] == "📍 지도 & 분석":
            active_tab["show_func"](filtered_shelters, final_animals)
        elif active_tab["label"] == "📊 분석 대시보드":
            active_tab["show_func"](final_animals, filtered_shelters)
        elif active_tab["label"] == "📋 보호소 상세 현황":
            active_tab["show_func"](filtered_shelters)
        else:
            active_tab["show_func"]()

    # --- 푸터 ---
    render_footer()

if __name__ == "__main__":
    main()
