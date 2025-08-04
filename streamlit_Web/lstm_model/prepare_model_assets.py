
import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
import pickle
import os
import sys

# --- 설정 ---
# 이 스크립트는 streamlit_Web/lstm_model/ 디렉토리에 위치해야 합니다.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(CURRENT_DIR), 'data')
INPUT_CSV_PATH = os.path.join(DATA_DIR, 'data20230731_20250730.csv')
OUTPUT_DIR = CURRENT_DIR

SEQUENCE_LENGTH = 7  # lstm_improved.py와 동일한 시퀀스 길이

def prepare_and_save_assets():
    """
    모델 예측에 필요한 자산(LabelEncoder, MinMaxScaler, 최신 시퀀스)을
    생성하고 .pkl 파일로 저장합니다.
    """
    print(f"데이터 로딩 시작: {INPUT_CSV_PATH}")
    if not os.path.exists(INPUT_CSV_PATH):
        print(f"오류: 입력 CSV 파일을 찾을 수 없습니다. 경로를 확인하세요: {INPUT_CSV_PATH}")
        sys.exit(1)

    try:
        df = pd.read_csv(INPUT_CSV_PATH, encoding='utf-8', low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(INPUT_CSV_PATH, encoding='cp949', low_memory=False)
    print("데이터 로딩 완료.")

    # --- 1. 데이터 전처리 (lstm_improved.py와 동일한 로직) ---
    print("데이터 전처리를 시작합니다...")
    df['happenDt'] = pd.to_datetime(df['happenDt'], format='%Y%m%d')

    # LabelEncoder 생성 및 학습
    label_encoder = LabelEncoder()
    df['orgNm_encoded'] = label_encoder.fit_transform(df['orgNm'])
    all_org_encoded = df['orgNm_encoded'].unique()

    # 날짜-보호소 조합 생성
    min_date = df['happenDt'].min()
    max_date = df['happenDt'].max()
    date_range = pd.date_range(start=min_date, end=max_date, freq='D')
    all_combinations = pd.MultiIndex.from_product(
        [date_range, all_org_encoded], names=['happenDt', 'orgNm_encoded']
    ).to_frame(index=False)

    df_happen = df[['happenDt', 'orgNm_encoded']].copy()
    df_happen['is_happened'] = 1

    merged = pd.merge(all_combinations, df_happen, on=['happenDt', 'orgNm_encoded'], how='left')
    merged['is_happened'] = merged['is_happened'].fillna(0)
    merged['orgNm_encoded_original'] = merged['orgNm_encoded']

    # 파생변수 추가
    merged['weekday'] = merged['happenDt'].dt.weekday
    merged['is_weekend'] = merged['weekday'].apply(lambda x: 1 if x >= 5 else 0)
    merged['rolling_sum_7'] = merged.groupby('orgNm_encoded')['is_happened'].transform(
        lambda x: x.rolling(window=7, min_periods=1).sum()
    )

    # MinMaxScaler 생성 및 학습
    scaler = MinMaxScaler()
    feature_cols_to_scale = ['orgNm_encoded', 'weekday', 'is_weekend', 'rolling_sum_7']
    merged[feature_cols_to_scale] = scaler.fit_transform(merged[feature_cols_to_scale])
    
    merged_df = merged.sort_values(by=['happenDt', 'orgNm_encoded']).reset_index(drop=True)
    print("데이터 전처리 완료.")

    # --- 2. 최신 시퀀스 추출 ---
    print("예측 시작을 위한 최신 시퀀스를 추출합니다...")
    latest_sequences = {}
    feature_cols = ['is_happened', 'orgNm_encoded', 'weekday', 'is_weekend', 'rolling_sum_7']
    
    for org_id in all_org_encoded:
        # 원본 org_id (스케일링 전)를 사용해야 함
        org_data = merged_df[merged_df['orgNm_encoded_original'] == org_id].sort_values(by='happenDt')
        if len(org_data) >= SEQUENCE_LENGTH:
            # 마지막 N일치 데이터를 시퀀스로 저장
            sequence = org_data[feature_cols].tail(SEQUENCE_LENGTH).values
            latest_sequences[org_id] = sequence

    print(f"{len(latest_sequences)}개 지역의 시퀀스 추출 완료.")

    # --- 3. 자산 파일로 저장 ---
    print("생성된 자산을 파일로 저장합니다...")
    assets = {
        'label_encoder': label_encoder,
        'scaler': scaler,
        'latest_sequences': latest_sequences,
        'data_last_date': max_date  # 데이터의 마지막 날짜 추가
    }
    
    output_path = os.path.join(OUTPUT_DIR, 'model_assets.pkl')
    with open(output_path, 'wb') as f:
        pickle.dump(assets, f)
        
    print(f"성공! 모든 자산이 '{output_path}' 파일에 저장되었습니다.")
    print("이제 이 스크립트를 다시 실행할 필요 없이, 웹 앱에서 예측 기능을 사용할 수 있습니다.")

if __name__ == "__main__":
    prepare_and_save_assets()
