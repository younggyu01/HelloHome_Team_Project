# 🐾 Hello Home: 전국 유기동물 통합 조회 및 분석 대시보드

![Header Image](https://raw.githubusercontent.com/cooperear/SK_Shielders_4th_rookie_1st_Team_Project/refs/heads/main/HelloHome_ICON_%ED%88%AC%EB%AA%85.png) 
*<p align="center">전국 보호소의 유기동물 정보를 한눈에 확인하고, 따뜻한 가족이 되어주세요.</p>*

---

## 🌟 프로젝트 소개

**Hello Home**은 전국의 유기동물 데이터를 실시간으로 조회하고, 다양한 관점에서 분석하며, 미래 발생 건수를 예측하는 Streamlit 기반의 웹 애플리케이션입니다. 사용자는 이 대시보드를 통해 다음을 할 수 있습니다.

- **🗺️ 지도 기반 조회**: 전국 보호소의 위치와 보호 중인 동물 현황을 지도를 통해 직관적으로 파악합니다.
- **📊 심층 분석**: 축종, 나이, 품종, 지역 등 다양한 조건에 따른 유기동물 데이터를 시각화된 차트로 분석합니다.
- **🔮 발생 예측**: LSTM 딥러닝 모델을 활용하여 미래의 지역별 유기동물 발생 확률을 예측합니다.
- **❤️ 찜하기 기능**: 관심 있는 동물을 찜 목록에 추가하여 언제든지 다시 확인할 수 있습니다.
- **📋 상세 정보**: 각 보호소와 동물의 상세 정보를 확인하고, 입양에 필요한 정보를 얻을 수 있습니다.
- **🌐 외부 입양 정보**: 공공 데이터 외에, 추가적인 외부 입양 사이트의 정보를 스크래핑하여 제공합니다.

이 프로젝트는 흩어져 있는 유기동물 정보를 통합하여 예비 입양자에게는 더 나은 탐색 환경을 제공하고, 데이터 분석을 통해 유기동물 문제에 대한 사회적 인식을 높이는 것을 목표로 합니다.

---

## 🛠️ 기술 스택

- **언어**: `Python 3.9+`
- **웹 프레임워크**: `Streamlit`
- **데이터 처리 및 분석**: `Pandas`, `NumPy`
- **데이터 시각화**: `Plotly`, `Folium`
- **데이터베이스**: `MariaDB` (with `SQLAlchemy`)
- **딥러닝 모델**: `TensorFlow (Keras)`
- **머신러닝**: `Scikit-learn`

---

## 📂 프로젝트 구조와 핵심 파일

프로젝트는 기능별로 명확하게 모듈화되어 유지보수와 확장성을 높였습니다.

```
team_project/
│
├── .gitignore
├── README.md
├── requirements.txt
├── config.ini.example
│
└── streamlit_Web/
    ├── app.py              # 🚀 애플리케이션의 메인 실행 파일
    ├── data_manager.py     # 🗃️ 데이터 소스(DB, API) 관리
    ├── ui_components.py    # 🎨 UI 컴포넌트(헤더, 사이드바, 카드 등)
    ├── utils.py            # 🛠️ 프로젝트 공통 유틸리티 함수
    │
    ├── data/               # 🖼️ 정적 및 중간 데이터
    │   ├── HelloHome_ICON_투명.png # 로고 이미지
    │   └── ... (cat_info.json, dog_info.json 등)
    │
    ├── lstm_model/         # 🔮 LSTM 예측 모델 관련 파일
    │   ├── lstm_improved.py    # ✨ 모델 클래스 및 예측 로직 (핵심)
    │   ├── prepare_model_assets.py # ⚙️ 모델 자산 생성 스크립트 (개발용)
    │   ├── model_assets.pkl    # 📦 모델 자산 (규칙, 최신 데이터)
    │   └── lstm_model_animal_shelter_improved.h5 # 🧠 훈련된 모델 파일
    │
    └── tabs/               # 📑 각 탭의 UI와 로직
        └── ... (각 탭 뷰 파일)
```

### 예측 모델의 동작 방식 변경

이 프로젝트의 예측 기능은 초기 버전과 달리, 더 이상 무거운 원본 CSV 파일에 직접 의존하지 않습니다. 대신, 다음과 같은 효율적인 구조로 변경되었습니다.

- **`prepare_model_assets.py` (개발용 스크립트):**
  - Git 저장소에 포함되지 않는 원본 `data...csv` 파일을 읽습니다.
  - 예측에 필요한 모든 규칙(LabelEncoder, Scaler)과 데이터(최신 시퀀스, 마지막 날짜)를 추출하여, 가볍고 빠른 `model_assets.pkl` 파일 하나로 만듭니다.
  - 이 스크립트는 원본 데이터가 갱신되었을 때 **개발자가 단 한 번만 실행**하면 됩니다.

- **`model_assets.pkl` (핵심 자산 파일):**
  - 예측에 필요한 모든 정보가 담겨있는 압축 파일입니다. 
  - 이 파일과 `.h5` 모델 파일만 있으면, 원본 데이터 없이도 모든 사용자가 빠르고 일관된 예측 결과를 얻을 수 있습니다.

- **`data/` 디렉토리의 `.json` 파일 (예: `cat_info.json`)**
  - 이 파일들은 웹 스크래핑을 통해 수집된 데이터가 데이터베이스에 저장되기 전, **중간 단계에서 임시로 저장되는 파일**입니다.
  - 따라서 웹 애플리케이션이 직접 이 파일들을 읽지는 않지만, 전체 데이터 파이프라인(수집 → 가공 → DB 저장)의 일부로 사용됩니다.

---

## 🚀 시작하기

이 프로젝트를 실행하는 방법은 두 가지 목적에 따라 나뉩니다.

### A. 단순 실행 (대부분의 경우)

> 이미 생성된 모델 자산(`model_assets.pkl`)을 사용하여 웹 애플리케이션을 바로 실행하는 방법입니다.

**1. 사전 준비**

- `Python 3.9+`, `Git`, `MariaDB` 데이터베이스가 설치되어 있어야 합니다.

**2. 프로젝트 클론 및 설정**

```bash
# 1. 프로젝트를 로컬 컴퓨터에 복제합니다.
# (저장소에 포함된 .pkl, .h5 파일도 함께 받아집니다)
git clone https://github.com/cooperear/SK_Shielders_4th_rookie_1st_Team_Project.git

# 2. 프로젝트 폴더로 이동합니다.
cd SK_Shielders_4th_rookie_1st_Team_Project

# 3. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 4. 필요한 라이브러리 설치
pip install -r requirements.txt
```

**3. 데이터베이스 및 API 키 설정**

- 프로젝트 루트의 `config.ini.example` 파일을 복사하여 `config.ini` 파일을 생성합니다.
- `config.ini` 파일을 열어 본인의 환경에 맞게 정보를 수정합니다.

```ini
# config.ini 예시
[API]
service_key = YOUR_PUBLIC_DATA_PORTAL_API_KEY
kakao_rest_api_key = YOUR_KAKAO_REST_API_KEY

[DB]
host = 127.0.0.1
user = your_db_user
password = your_db_password
database = your_db_name
port = your_port
```

**4. 데이터베이스 테이블 생성 및 데이터 적재**

- 애플리케이션에 필요한 데이터를 DB에 미리 적재해야 합니다. (예: `update_data.py`와 같은 데이터 파이프라인 스크립트 실행)

**5. 애플리케이션 실행**

```bash
# streamlit_Web/ 디렉토리로 이동하여 앱 실행
cd streamlit_Web
streamlit run app.py
```
- 이제 웹 브라우저에서 `http://localhost:8501`로 접속하면 모든 기능이 정상적으로 동작합니다.

---

### B. 개발 및 모델 자산 재성성

> 원본 예측 데이터(`data...csv`)가 변경되었거나, 모델 관련 로직을 수정하여 `model_assets.pkl` 파일을 다시 만들어야 할 때 사용하는 방법입니다.

**1. 원본 데이터 준비**

- `streamlit_Web/data/` 디렉토리 안에 모델 학습에 사용된 원본 `data20230731_20250730.csv` 파일이 있어야 합니다.
- **주의:** 이 CSV 파일은 용량이 크므로 `.gitignore`에 의해 Git 저장소에는 포함되지 않습니다. 별도로 관리해야 합니다.

**2. 모델 자산(`model_assets.pkl`) 생성**

- 아래 명령어를 터미널에서 실행하여 `.pkl` 파일을 생성(또는 덮어쓰기)합니다.

```bash
# streamlit_Web/lstm_model/ 디렉토리로 이동
cd streamlit_Web/lstm_model

# 자산 생성 스크립트 실행
python prepare_model_assets.py
```
- "성공! 모든 자산이 ... 저장되었습니다." 메시지를 확인합니다.

**3. 애플리케이션 실행**

- 자산 생성이 완료되었다면, 위의 **'A. 단순 실행'** 방법의 5번 단계에 따라 앱을 실행합니다.

**4. 변경된 자산 커밋 (중요)**

- 새로 생성되거나 변경된 `model_assets.pkl` 파일은 다른 팀원들도 사용할 수 있도록 **반드시 Git에 커밋하고 푸시**해야 합니다.

```bash
git add streamlit_Web/lstm_model/model_assets.pkl
git commit -m "feat: 예측 모델 자산 업데이트"
git push
```

---

## 🗄️ 데이터베이스 스키마 정보

이 프로젝트는 `shelter_db` 데이터베이스 내의 4개 테이블을 사용합니다. 각 테이블의 구조는 다음과 같습니다.

#### `animals`

공공데이터포털 API를 통해 수집된 유기동물의 기본 정보가 저장됩니다.

| Field         | Type     | Description                                      |
|---------------|----------|--------------------------------------------------|
| desertion_no  | text     | 유기번호 (고유 ID)                               |
| shelter_name  | text     | 보호소 이름                                      |
| animal_name   | text     | 동물 이름                                        |
| species       | text     | 종 (개, 고양이 등)                               |
| kind_name     | text     | 품종                                             |
| age           | text     | 나이                                             |
| upkind_name   | text     | 축종 (개, 고양이, 기타)                          |
| image_url     | text     | 동물 이미지 URL                                  |
| personality   | text     | 성격/특징                                        |
| special_mark  | text     | 특징                                             |
| notice_date   | datetime | 공고일                                           |
| notice_no     | text     | 공고번호                                         |
| sex           | text     | 성별 (M: 수컷, F: 암컷)                          |
| neuter        | text     | 중성화 여부 (Y: 예, N: 아니오, U: 미상)          |
| color         | text     | 색상                                             |
| weight        | text     | 체중                                             |
| care_tel      | text     | 보호소 연락처                                    |
| care_addr     | text     | 보호소 주소                                      |
| happen_place  | text     | 발견 장소                                        |
| process_state | text     | 상태 (보호중, 종료(입양), 종료(반환) 등)         |


#### `shelters`

보호소의 위치, 현황 등 상세 정보가 저장됩니다.

| Field              | Type   | Description                                      |
|--------------------|--------|--------------------------------------------------|
| shelter_name       | text   | 보호소 이름                                      |
| region             | text   | 지역 (예: 서울특별시 강남구)                     |
| count              | double | 현재 보호중인 동물 수                            |
| long_term          | double | 장기 보호 동물 수                                |
| adopted            | double | 입양 완료된 동물 수                              |
| species            | text   | 주요 보호 축종                                   |
| kind_name          | text   | 주요 보호 품종                                   |
| image_url          | text   | 대표 이미지 URL                                  |
| care_reg_no        | text   | 동물보호관리시스템 등록번호                      |
| care_addr          | text   | 보호소 주소                                      |
| lat                | double | 위도                                             |
| lon                | double | 경도                                             |


#### `web_cats` 및 `web_dogs`

외부 웹사이트에서 스크래핑한 고양이와 강아지의 입양 정보가 각각 저장됩니다. 두 테이블은 동일한 구조를 가집니다.

| Field             | Type | Description                                      |
|-------------------|------|--------------------------------------------------|
| 이미지            | text | 동물 이미지 URL                                  |
| 이름              | text | 동물 이름                                        |
| 성별              | text | 성별                                             |
| 출생시기          | text | 출생 시기 (예: 2023년생)                         |
| 몸무게            | text | 체중                                             |
| 태그              | text | 현재 상태 태그 (JSON 배열, 예: ["임보가능"])   |
| 성격 및 특징      | text | 성격 및 외모 특징                                |
| 임보 조건         | text | 임시보호 조건 (JSON 객체)                        |
| 히스토리          | text | 구조 이력 (JSON 객체)                            |
| 건강 정보         | text | 건강 정보 (JSON 객체)                            |
| 공고날짜          | text | 공고 게시일                                      |
| 사이트링크        | text | 원본 게시물 링크                                 |
