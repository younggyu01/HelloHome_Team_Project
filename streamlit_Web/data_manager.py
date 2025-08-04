

import pandas as pd
import streamlit as st
import configparser
import os
from sqlalchemy import create_engine, text
import xml.etree.ElementTree as ET
from urllib.parse import quote
import subprocess
import tempfile
from datetime import date
from typing import List, Tuple

# --- 경로 및 설정 로드 ---
current_script_path = os.path.abspath(__file__)
streamlit_web_dir = os.path.dirname(current_script_path)
project_root = os.path.dirname(streamlit_web_dir)
CONFIG_PATH = os.path.join(project_root, 'config.ini')

def get_config():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_PATH):
        st.error("설정 파일(config.ini)을 찾을 수 없습니다.")
        return None
    config.read(CONFIG_PATH)
    return config

# --- DB 및 API 클라이언트 ---
@st.cache_resource
def get_db_engine():
    config = get_config()
    if not config or 'DB' not in config:
        st.error("DB 설정이 올바르지 않습니다.")
        return None
    db_config = config['DB']
    try:
        engine = create_engine(
            f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config.get('port', 3306)}/{db_config['database']}"
        )
        with engine.connect() as _: 
            pass
        return engine
    except Exception as e:
        st.error(f"DB 연결에 실패했습니다: {e}")
        return None

def get_api_key():
    config = get_config()
    if not config or 'API' not in config:
        st.error("API 키 설정이 올바르지 않습니다.")
        return None
    return config['API']['service_key']

def fetch_api_data_powershell(url: str) -> ET.Element | None:
    fp, temp_path = tempfile.mkstemp(suffix=".xml")
    os.close(fp)
    try:
        command = f"powershell -Command \"(New-Object System.Net.WebClient).DownloadFile('{url}', '{temp_path}')\""
        subprocess.run(command, check=True, shell=True, capture_output=True, text=True)
        with open(temp_path, 'rb') as f:
            xml_data = f.read()
        if not xml_data:
            return None
        return ET.fromstring(xml_data)
    except subprocess.CalledProcessError as e:
        st.warning(f"PowerShell을 통한 데이터 다운로드 중 오류 발생: {e.stderr}")
        return None
    except Exception as e:
        st.warning(f"API 데이터 처리 중 알 수 없는 오류 발생: {e}")
        return None
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@st.cache_data
def get_sido_list() -> List[dict]:
    api_key = get_api_key()
    if not api_key: return []
    encoded_key = quote(api_key, safe='/')
    endpoint = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/sido_v2"
    url = f"{endpoint}?serviceKey={encoded_key}&numOfRows=100&_type=xml"
    root = fetch_api_data_powershell(url)
    if root is None: return []
    return [{"code": item.findtext("orgCd"), "name": item.findtext("orgdownNm")} for item in root.findall('.//item')]

@st.cache_data
def get_sigungu_list(sido_code: str) -> List[dict]:
    if not sido_code: return []
    api_key = get_api_key()
    if not api_key: return []
    encoded_key = quote(api_key, safe='/')
    endpoint = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/sigungu_v2"
    url = f"{endpoint}?serviceKey={encoded_key}&upr_cd={sido_code}&_type=xml"
    root = fetch_api_data_powershell(url)
    if root is None: return []
    return [{"code": item.findtext("orgCd"), "name": item.findtext("orgdownNm")} for item in root.findall('.//item')]

@st.cache_data
def get_kind_list(upkind_code: str = '') -> List[dict]:
    api_key = get_api_key()
    if not api_key: return []
    encoded_key = quote(api_key, safe='/')
    endpoint = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/kind_v2"
    codes_to_fetch = [upkind_code] if upkind_code else ['417000', '422400', '429900']
    all_kinds = []
    for code in codes_to_fetch:
        page_no = 1
        while True:
            url = f"{endpoint}?serviceKey={encoded_key}&up_kind_cd={code}&pageNo={page_no}&numOfRows=1000&_type=xml"
            root = fetch_api_data_powershell(url)
            if root is None or root.find('.//resultCode').text != '00': break
            items_in_page = root.findall('.//item')
            if not items_in_page: break
            for item in items_in_page:
                all_kinds.append({"code": item.findtext("kindCd"), "name": item.findtext("kindNm")})
            total_count = int(root.find('.//totalCount').text)
            if len(all_kinds) >= total_count: break
            page_no += 1
    return list({v['code']:v for v in all_kinds}.values())

def init_db():
    engine = get_db_engine()
    if engine is None: 
        st.error("DB 엔진을 초기화할 수 없어 앱 실행이 불가능합니다.")
        return
    try:
        with engine.connect() as conn:
            cursor = conn.execute(text("SHOW TABLES LIKE 'shelters'"))
            if cursor.fetchone() is None:
                st.warning("'shelters' 테이블이 DB에 존재하지 않습니다. `update_data.py`를 먼저 실행해주세요.")
    except Exception as e:
        st.error(f"DB 초기화 중 오류 발생: {e}")

@st.cache_data
def load_data(table_name: str) -> pd.DataFrame:
    engine = get_db_engine()
    if engine is None: return pd.DataFrame()
    try:
        with engine.connect() as conn:
            data = pd.read_sql(f"SELECT * FROM {table_name}", conn)
            if table_name == 'shelters':
                data['lat'] = pd.to_numeric(data['lat'], errors='coerce')
                data['lon'] = pd.to_numeric(data['lon'], errors='coerce')
            return data
    except Exception as e:
        st.warning(f"'{table_name}' 테이블 로딩 중 오류: {e}. 빈 데이터를 반환합니다.")
        return pd.DataFrame()

@st.cache_data
def get_filtered_data(
    start_date: date, 
    end_date: date, 
    sido: str, 
    sigungu: str, 
    species: List[str]
) -> Tuple[pd.DataFrame, pd.DataFrame, int, int, int, int]:
    animals = load_data("animals")
    shelters = load_data("shelters")

    if animals.empty or shelters.empty:
        return pd.DataFrame(), pd.DataFrame(), 0, 0, 0, 0

    animals['notice_date'] = pd.to_datetime(animals['notice_date'])
    mask = (animals['notice_date'].dt.date >= start_date) & (animals['notice_date'].dt.date <= end_date)
    filtered_animals = animals[mask]

    if species:
        filtered_animals = filtered_animals[filtered_animals['upkind_name'].isin(species)]

    shelter_names_with_animals = filtered_animals['shelter_name'].unique()
    filtered_shelters = shelters[shelters['shelter_name'].isin(shelter_names_with_animals)]

    addr_col = "care_addr" if "care_addr" in filtered_shelters.columns else "careAddr"
    if sido != "전체":
        filtered_shelters = filtered_shelters[filtered_shelters[addr_col].str.startswith(sido, na=False)]
    if sigungu != "전체":
        full_region_name = f"{sido} {sigungu}"
        filtered_shelters = filtered_shelters[filtered_shelters[addr_col].str.startswith(full_region_name, na=False)]

    final_animal_shelters = filtered_shelters['shelter_name'].unique()
    final_animals = filtered_animals[filtered_animals['shelter_name'].isin(final_animal_shelters)]

    shelter_count = filtered_shelters['shelter_name'].nunique()
    animal_count = len(final_animals)
    long_term_count = int(filtered_shelters['long_term'].sum())
    adopted_count = int(filtered_shelters['adopted'].sum())

    return final_animals, filtered_shelters, shelter_count, animal_count, long_term_count, adopted_count
