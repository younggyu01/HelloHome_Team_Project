

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from utils import get_db_config
import math
import json
import plotly.express as px

# --- 데이터 로딩 ---
@st.cache_data
def load_scraped_data(table_name: str) -> pd.DataFrame:
    try:
        db_config = get_db_config()
        engine = create_engine(f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@"
                               f"{db_config['host']}:{db_config['port']}/{db_config['database']}?charset=utf8mb4")
        return pd.read_sql(f"SELECT * FROM {table_name}", engine)
    except Exception as e:
        st.error(f"{table_name} 데이터 로딩 중 오류 발생: {e}")
        return pd.DataFrame()

# --- 데이터 처리 ---
def safe_json_loads(s):
    try:
        return json.loads(s) if isinstance(s, str) else []
    except (json.JSONDecodeError, TypeError):
        return []

def filter_data(data: pd.DataFrame, search_name: str, selected_tag: str) -> pd.DataFrame:
    if search_name:
        data = data[data["이름"].str.contains(search_name, case=False, na=False)]
    if selected_tag and selected_tag != "전체":
        data = data[data["태그"].apply(lambda x: selected_tag in safe_json_loads(x))]
    return data

# --- UI 렌더링 함수 ---
def render_status_description():
    st.markdown("### 🟥 임보가능 | 🟧 임보중 | 🟠 입양전제 | 🟤 릴레이임보")
    st.caption("임보가능: 임보/입양 문의 가능 | 임보중: 입양 문의만 가능 | 입양전제: 입양으로 전환 예정 | 릴레이임보: 현 임보처에서 곧 임보 종료")
    st.markdown("---")

def render_animal_card(row: pd.Series):
    st.image(row.get("이미지", "https://via.placeholder.com/200"), width=200)
    st.subheader(f"{row.get('이름', '정보 없음')} ({row.get('성별', '정보 없음')})")
    
    출생 = row.get('출생시기', '정보 없음')
    몸무게 = row.get('몸무게', '정보 없음')
    st.markdown(f"**출생:** {출생}   |   **몸무게:** {몸무게}")

    tags = safe_json_loads(row.get("태그", "[]"))
    st.markdown(f"**임보 상태:** {', '.join(tags) if tags else '정보 없음'}")

    st.markdown("### 🏠 임보 조건")
    conditions = safe_json_loads(row.get("임보 조건", "{}"))
    if isinstance(conditions, dict) and conditions:
        st.markdown(f"- 지역: {conditions.get('지역', '정보 없음')}")
        st.markdown(f"- 임보 기간: {conditions.get('임보 기간', '정보 없음')}")
    else:
        st.markdown("- 정보 없음")

    st.markdown("### 🐾 성격 및 특징")
    features = row.get("성격 및 특징", "")
    if features:
        for line in features.split("\n"):
            if line.strip():
                st.markdown(f"- {line.strip()}")
    else:
        st.markdown("- 정보 없음")

    st.markdown("### 📜 구조 이력")
    history = safe_json_loads(row.get("히스토리", "{}"))
    if isinstance(history, dict) and history:
        for date, event in history.items():
            st.markdown(f"- {date}: {event}")
    else:
        st.markdown("- 정보 없음")

    st.markdown("### 🩺 건강 정보")
    health = safe_json_loads(row.get("건강 정보", "{}"))
    if isinstance(health, dict) and health:
        st.markdown(f"- 접종 현황: {health.get('접종 현황', '정보 없음')}")
        st.markdown(f"- 검사 현황: {health.get('검사 현황', '정보 없음')}")
        st.markdown(f"- 병력 사항: {health.get('병력 사항', '정보 없음')}")
        st.markdown(f"- 기타 사항: {health.get('기타 사항', '정보 없음')}")
    else:
        st.markdown("- 정보 없음")

    st.markdown(f"### 📅 공고 날짜: {row.get('공고날짜', '정보 없음')}")
    if row.get("사이트링크"):
        st.markdown(f"[🔗 입양 정보 보러가기]({row.get('사이트링크')})")

    st.divider()

def render_animal_info_tab(animal_type: str, data: pd.DataFrame):
    st.sidebar.subheader(f"🔍 {animal_type} 검색 / 필터")
    search_name = st.sidebar.text_input(f"이름으로 검색", key=f"{animal_type}_search")
    tag_options = ["전체", "임보가능", "입양전제", "임보중", "일반임보"]
    selected_tag = st.sidebar.selectbox(f"태그 필터", tag_options, key=f"{animal_type}_tag")

    filtered = filter_data(data, search_name, selected_tag)
    if filtered.empty:
        st.warning("검색 결과가 없습니다.")
        return

    total_pages = math.ceil(len(filtered) / 10)
    page = st.selectbox(f"{animal_type} 페이지 선택", options=list(range(1, total_pages + 1)), key=f"{animal_type}_page")
    
    start = (page - 1) * 10
    end = start + 10
    for _, row in filtered.iloc[start:end].iterrows():
        render_animal_card(row)

def render_visualization_tab(animal_type: str, data: pd.DataFrame):
    st.subheader(f"{animal_type} 데이터 시각화")
    if data.empty:
        st.info(f"{animal_type} 데이터가 없습니다.")
        return

    def classify_status(tag_str):
        tags = safe_json_loads(tag_str)
        if '공고종료' in tags: return '공고종료'
        if '입양완료' in tags: return '입양완료'
        if '임보중' in tags: return '임보중'
        return '임보가능'

    data['현재 상태'] = data['태그'].apply(classify_status)
    status_counts = data['현재 상태'].value_counts()

    color_map = {
        '임보가능': '#1f77b4',  # Muted Blue
        '임보중': '#ff7f0e',   # Safety Orange
        '입양완료': '#2ca02c',  # Cooked Asparagus Green
        '공고종료': '#d62728'   # Brick Red
    }

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(status_counts, x=status_counts.index, y=status_counts.values, 
                     labels={'x': '현재 상태', 'y': '개체 수'}, title=f'{animal_type} 임보 상태 분포',
                     color=status_counts.index, color_discrete_map=color_map)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.pie(status_counts, names=status_counts.index, values=status_counts.values, 
                      title=f'{animal_type} 임보 상태 비율', hole=0.3,
                      color=status_counts.index, color_discrete_map=color_map)
        st.plotly_chart(fig2, use_container_width=True)

# --- 메인 함수 ---
def show():
    st.title("🏵️ PIMFYVIRUS 입양 정보")
    render_status_description()

    main_tab1, main_tab2 = st.tabs(["📋 입양 정보", "📊 시각화"])

    with main_tab1:
        cat_tab, dog_tab = st.tabs(["🐱 고양이", "🐶 강아지"])
        with cat_tab:
            cats_data = load_scraped_data("web_cats")
            render_animal_info_tab("고양이", cats_data)
        with dog_tab:
            dogs_data = load_scraped_data("web_dogs")
            render_animal_info_tab("강아지", dogs_data)

    with main_tab2:
        cat_viz_tab, dog_viz_tab = st.tabs(["🐱 고양이", "🐶 강아지"])
        with cat_viz_tab:
            cats_data = load_scraped_data("web_cats")
            render_visualization_tab("고양이", cats_data)
        with dog_viz_tab:
            dogs_data = load_scraped_data("web_dogs")
            render_visualization_tab("강아지", dogs_data)
