
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import plotly.express as px

# --- 모듈 경로 설정 및 임포트 ---
# 현재 파일 위치를 기준으로 lstm_model 디렉토리의 경로를 시스템 경로에 추가합니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
streamlit_web_dir = os.path.dirname(current_dir)
lstm_model_path = os.path.join(streamlit_web_dir, 'lstm_model')
if lstm_model_path not in sys.path:
    sys.path.append(lstm_model_path)

# 수정된 AnimalShelterPredictor 클래스를 임포트합니다.
from lstm_improved import AnimalShelterPredictor

# --- 모델 로더 ---
@st.cache_resource
def load_predictor():
    """
    예측 모델과 관련 자산(.pkl)을 로드합니다.
    이 함수는 앱 세션 동안 단 한 번만 실행됩니다.
    """
    model_path = os.path.join(lstm_model_path, 'lstm_model_animal_shelter_improved.h5')
    assets_path = os.path.join(lstm_model_path, 'model_assets.pkl')
    
    predictor = AnimalShelterPredictor(model_path=model_path, assets_path=assets_path)
    
    if not predictor.load_assets():
        st.error("예측에 필요한 모델 또는 자산 파일 로딩에 실패했습니다. model_assets.pkl 파일이 존재하는지 확인하세요.")
        return None
        
    return predictor

# --- UI 렌더링 함수 ---
def render_prediction_form():
    """사용자로부터 예측에 필요한 입력을 받는 UI 폼을 렌더링합니다."""
    display_option = st.selectbox(
        "표시할 결과 범위",
        options=['상위 5개', '상위 10개', '상위 20개', '전체 보기'],
        index=0
    )
    period_option = st.selectbox(
        "예측 기간 선택",
        options=['7일', '14일', '30일'],
        index=2
    )
    return display_option, period_option

def display_prediction_results(predictions, display_option, start_date, end_date):
    """예측 결과를 테이블로 시각화합니다."""
    top_n_map = {'상위 5개': 5, '상위 10개': 10, '상위 20개': 20, '전체 보기': len(predictions)}
    top_n = top_n_map[display_option]
    display_text = f"{display_option} ({top_n}개)" if display_option == '전체 보기' else display_option

    # 날짜 포맷팅
    start_date_str = start_date.strftime("%Y년 %m월 %d일")
    end_date_str = end_date.strftime("%Y년 %m월 %d일")

    st.success(f"**{start_date_str} ~ {end_date_str}** 기간의 유기동물 발생 예측 {display_text} 결과입니다.")

    pred_df = pd.DataFrame(predictions[:top_n])
    pred_df.rename(columns={'org_name': '지역', 'predicted_probability_percent': '평균 발생 확률 (%)'}, inplace=True)
    pred_df['순위'] = range(1, len(pred_df) + 1)
    pred_df['예측 이유'] = "과거 2년간의 시계열 패턴 기반"
    pred_df = pred_df[['순위', '지역', '평균 발생 확률 (%)', '예측 이유']]

    st.table(pred_df.style.format({'평균 발생 확률 (%)': '{:.2f}%'}))

# --- 메인 함수 ---
def show():
    st.header("🔮 미래 유기동물 발생 예측")
    
    predictor = load_predictor()
    if predictor is None:
        return

    # 데이터 마지막 날짜를 가져와 설명에 포함
    if predictor.is_loaded and hasattr(predictor, 'data_last_date'):
        last_date_str = predictor.data_last_date.strftime("%Y년 %m월 %d일")
        st.write(f"선택한 예측 기간 동안 유기동물 발생 가능성이 높은 지역을 예측합니다. (데이터 기준: ~{last_date_str})")
    else:
        st.write("선택한 예측 기간 동안 유기동물 발생 가능성이 높은 지역을 예측합니다.")

    display_option, period_option = render_prediction_form()

    if st.button("예측 실행", key="predict_button"):
        days_map = {'7일': 7, '14일': 14, '30일': 30}
        days = days_map[period_option]
        
        # .pkl 파일에서 로드한 마지막 날짜를 기준으로 예측 기간 설정
        prediction_start_date = predictor.data_last_date + timedelta(days=1)
        prediction_end_date = prediction_start_date + timedelta(days=days - 1)

        progress_bar = st.progress(0, text="LSTM 모델을 이용하여 예측 중입니다...")
        
        try:
            predictions = predictor.predict_all_orgs(
                start_date_str=prediction_start_date.strftime('%Y-%m-%d'),
                end_date_str=prediction_end_date.strftime('%Y-%m-%d'),
                progress_callback=lambda p: progress_bar.progress(p, text=f"예측 진행률: {p:.0%}")
            )
            if predictions:
                display_prediction_results(predictions, display_option, prediction_start_date, prediction_end_date)
            else:
                st.warning("예측 결과를 생성하지 못했습니다. 모델 자산 파일을 확인해주세요.")
        except Exception as e:
            st.error(f"예측 중 오류가 발생했습니다: {e}")
        finally:
            progress_bar.empty()
