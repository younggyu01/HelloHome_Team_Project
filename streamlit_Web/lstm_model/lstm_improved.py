
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from datetime import datetime, timedelta
import os
import pickle

class AnimalShelterPredictor:
    def __init__(self, model_path, assets_path, sequence_length=7):
        self.model_path = model_path
        self.assets_path = assets_path
        self.sequence_length = sequence_length
        self.model = None
        self.label_encoder = None
        self.scaler = None
        self.latest_sequences = None
        self.data_last_date = None
        self.is_loaded = False

    def load_assets(self):
        """모델과 전처리 자산을 로드합니다."""
        if not os.path.exists(self.model_path):
            print(f"오류: 모델 파일을 찾을 수 없습니다 - {self.model_path}")
            return False
        if not os.path.exists(self.assets_path):
            print(f"오류: 자산 파일을 찾을 수 없습니다 - {self.assets_path}")
            return False

        try:
            self.model = load_model(self.model_path)
            with open(self.assets_path, 'rb') as f:
                assets = pickle.load(f)
            self.label_encoder = assets['label_encoder']
            self.scaler = assets['scaler']
            self.latest_sequences = assets['latest_sequences']
            self.data_last_date = assets.get('data_last_date') # .get()으로 안전하게 로드
            self.is_loaded = True
            print("모델과 자산 로딩 완료.")
            return True
        except Exception as e:
            print(f"모델 또는 자산 로딩 중 오류 발생: {e}")
            return False

    def predict_all_orgs(self, start_date_str, end_date_str, progress_callback=None):
        if not self.is_loaded:
            print("오류: 모델과 자산이 로드되지 않았습니다. 먼저 load_assets()를 호출하세요.")
            return []

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        prediction_days = (end_date - start_date).days + 1

        # 1. 모든 예측 시퀀스를 한 번에 준비 (배치 처리)
        all_sequences = []
        org_id_map = [] # 각 시퀀스가 어떤 org_id에 해당하는지 기록
        org_name_map = {}

        print("배치 예측을 위한 데이터 준비 중...")
        for org_id, initial_sequence in self.latest_sequences.items():
            org_name = self.label_encoder.inverse_transform([org_id])[0]
            org_name_map[org_id] = org_name
            # 동일한 초기 시퀀스를 예측일수만큼 반복해서 추가
            for _ in range(prediction_days):
                all_sequences.append(initial_sequence)
                org_id_map.append(org_id)
        
        if not all_sequences:
            return []

        # 2. 모델 예측을 단 한 번만 호출
        print(f"{len(all_sequences)}개의 시퀀스에 대한 예측을 시작합니다...")
        X_predict = np.array(all_sequences)
        # verbose=1로 설정하여 예측 진행 상황을 터미널에서 확인 (디버깅용)
        predictions = self.model.predict(X_predict, verbose=1).flatten()
        print("예측 완료.")

        # 3. 예측 결과 집계
        org_probabilities = {org_id: [] for org_id in self.latest_sequences.keys()}
        for i, org_id in enumerate(org_id_map):
            org_probabilities[org_id].append(predictions[i])
            if progress_callback:
                # 콜백은 예측 후 빠르게 진행되므로, 여기서는 100%로 바로 설정 가능
                progress_callback((i + 1) / len(org_id_map))

        # 4. 지역별 평균 확률 계산
        final_predictions = []
        for org_id, probs in org_probabilities.items():
            avg_prob = np.mean(probs) * 100
            final_predictions.append({
                'org_name': org_name_map[org_id],
                'predicted_probability_percent': avg_prob
            })

        # 5. 최종 정렬
        sorted_predictions = sorted(final_predictions, key=lambda x: x['predicted_probability_percent'], reverse=True)
        
        return sorted_predictions

# 이 파일은 더 이상 직접 실행되지 않으므로 main 블록은 제거합니다.
