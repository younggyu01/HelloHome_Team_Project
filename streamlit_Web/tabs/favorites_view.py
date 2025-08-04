
import streamlit as st
import pandas as pd
from data_manager import load_data
from ui_components import render_animal_card

@st.cache_data
def get_favorite_animals(favorite_ids: list) -> pd.DataFrame:
    """찜 목록에 있는 동물들의 상세 정보를 데이터베이스에서 조회합니다."""
    if not favorite_ids:
        return pd.DataFrame()
    
    all_animals = load_data("animals")
    if all_animals.empty:
        return pd.DataFrame()
        
    return all_animals[all_animals["desertion_no"].isin(favorite_ids)]

def show():
    """'찜한 동물' 탭의 전체 UI를 그리고 로직을 처리하는 메인 함수입니다."""
    favorite_ids = st.session_state.get('favorites', [])
    st.subheader(f"❤️ 찜한 동물 ({len(favorite_ids)})마리")

    if not favorite_ids:
        st.info("아직 찜한 동물이 없습니다. 상세 정보 탭에서 하트 버튼을 눌러 추가해보세요!")
        return

    favorite_animals = get_favorite_animals(favorite_ids)

    if favorite_animals.empty:
        st.warning("찜한 동물을 찾을 수 없습니다. 데이터가 변경되었을 수 있습니다.")
        return

    for _, animal in favorite_animals.iterrows():
        render_animal_card(animal, context="favorites", show_shelter=True)
