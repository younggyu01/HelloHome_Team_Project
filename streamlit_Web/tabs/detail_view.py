
import streamlit as st
import pandas as pd
from data_manager import load_data
from ui_components import render_animal_card, render_download_button

@st.cache_data
def get_animal_details(shelter_name: str) -> pd.DataFrame:
    """특정 보호소의 동물 데이터를 필터링하여 반환합니다."""
    animals_df = load_data("animals")
    if animals_df.empty or shelter_name is None:
        return pd.DataFrame()
    return animals_df[animals_df['shelter_name'] == shelter_name]

def show(filtered_shelters: pd.DataFrame):
    st.subheader("📋 보호소 상세 현황")

    shelter_name = st.session_state.get("selected_shelter")

    if not shelter_name:
        st.info("지도에서 보호소 마커를 클릭하여 상세 정보를 확인하세요.")
        return

    st.markdown(f"### 🏠 {shelter_name}")
    animal_details = get_animal_details(shelter_name)

    if animal_details.empty:
        st.warning("이 보호소에 등록된 동물 정보가 없습니다.")
        return

    # 연락처 정보를 animal_details에서 직접 가져오도록 수정
    shelter_tel = animal_details.iloc[0].get('care_tel', '정보 없음')
    st.markdown(f"**📞 연락처:** {shelter_tel}")
    st.markdown("---")

    for _, animal in animal_details.iterrows():
        render_animal_card(animal, context="details")

    if not animal_details.empty:
        render_download_button(animal_details, shelter_name)
