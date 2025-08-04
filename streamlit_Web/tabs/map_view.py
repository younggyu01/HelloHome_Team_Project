
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from folium.plugins import MarkerCluster

def create_map(filtered_shelters: pd.DataFrame, filtered_animals: pd.DataFrame) -> folium.Map:
    """Folium 지도를 생성하고 마커를 추가합니다."""
    if filtered_shelters.empty:
        return folium.Map(location=[36.5, 127.5], zoom_start=7)

    shelter_image_map = {}
    if not filtered_animals.empty and 'image_url' in filtered_animals.columns:
        shelter_image_map = filtered_animals.groupby('shelter_name')['image_url'].first().to_dict()

    valid_lat = filtered_shelters['lat'].dropna()
    valid_lon = filtered_shelters['lon'].dropna()
    map_center = [valid_lat.mean(), valid_lon.mean()] if not valid_lat.empty else [37.5665, 126.9780]

    map_obj = folium.Map(location=map_center, zoom_start=7)
    marker_cluster = MarkerCluster().add_to(map_obj)

    for _, row in filtered_shelters.iterrows():
        if pd.notna(row['lat']) and pd.notna(row['lon']):
            image_url = shelter_image_map.get(row['shelter_name'], "https://via.placeholder.com/150?text=사진+없음")
            popup_html = f"""
                <b>{row['shelter_name']}</b><br>
                <img src='{image_url}' width='150'><br>
                지역: {row.get('region', '정보 없음')}<br>
                주요 품종: {row.get('kind_name', '정보 없음')}<br>
                보호 중: {int(row.get('count', 0))} 마리
            """
            folium.Marker(
                [row['lat'], row['lon']],
                popup=popup_html,
                tooltip=row['shelter_name'],
                icon=folium.Icon(color="blue", icon="paw", prefix='fa')
            ).add_to(marker_cluster)
            
    return map_obj

def render_shelter_table(filtered_shelters: pd.DataFrame):
    """보호소 현황 테이블을 렌더링합니다."""
    st.subheader("📊 보호소별 동물 현황")
    base_cols = ['shelter_name', 'region']
    optional_cols = ['kind_name', 'count', 'long_term', 'adopted']
    display_cols = base_cols + [col for col in optional_cols if col in filtered_shelters.columns]

    st.dataframe(
        filtered_shelters[display_cols],
        use_container_width=True,
        column_config={
            "shelter_name": "보호소명",
            "region": "지역",
            "kind_name": "주요 품종",
            "count": "보호 중",
            "long_term": "장기 보호",
            "adopted": "입양 완료"
        }
    )

def handle_map_click(map_event, tab_labels):
    """지도 클릭 이벤트를 처리하고 탭을 전환합니다."""
    if map_event and map_event.get("last_object_clicked_tooltip"):
        clicked_shelter = map_event["last_object_clicked_tooltip"]
        if st.session_state.get("selected_shelter") != clicked_shelter:
            st.session_state.selected_shelter = clicked_shelter
            try:
                detail_tab_idx = tab_labels.index("📋 보호소 상세 현황")
                st.session_state.active_tab_idx = detail_tab_idx
                st.rerun()
            except (ValueError, IndexError):
                st.error("상세 현황 탭을 찾을 수 없습니다.")
            except Exception:
                # st.rerun() can sometimes cause a harmless exception.
                pass

def show(filtered_shelters: pd.DataFrame, filtered_animals: pd.DataFrame, tab_labels: list):
    """지도 및 분석 탭의 전체 UI를 표시합니다."""
    st.subheader("🗺️ 보호소 지도")

    if filtered_shelters.empty:
        st.warning("표시할 데이터가 없습니다. 필터 조건을 변경해보세요.")
        return

    map_obj = create_map(filtered_shelters, filtered_animals)
    
    map_event = None
    try:
        map_event = st_folium(map_obj, width='100%', height=500)
    except Exception:
        # This can happen on fast re-runs, safe to ignore.
        pass

    handle_map_click(map_event, tab_labels)
    render_shelter_table(filtered_shelters)
