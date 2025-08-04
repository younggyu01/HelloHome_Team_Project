# ==============================================================================
# update_data.py - 데이터 수집 및 데이터베이스 업데이트 스크립트
# ==============================================================================
# 이 스크립트는 독립적으로 실행되어 외부 API(공공데이터포털, 카카오)
# 로부터 최신 데이터를 가져와 가공한 후, MySQL 데이터베이스에 저장하는
# ETL(Extract, Transform, Load) 파이프라인 역할을 합니다.
#
# [주요 실행 흐름]
# 1. **설정 로드:** `config.ini`에서 API 키와 DB 접속 정보를 가져옵니다.
# 2. **데이터 추출 (Extract):**
#    - `fetch_abandoned_animals`: 공공데이터포털에서 유기동물 정보를 조회합니다.
#      (최근 6개월 치, 개/고양이)
#    - `fetch_shelters`: 전국의 모든 동물보호소 정보를 조회합니다.
#    - `get_coordinates_from_address`: 카카오 지도 API를 사용하여 주소를
#      위도/경도 좌표로 변환(지오코딩)합니다.
# 3. **데이터 변환 (Transform):**
#    - `preprocess_data`: API로부터 받은 원본(raw) 데이터를 분석하기 좋은 형태로
#      가공합니다. (컬럼 이름 변경, 데이터 타입 변환, 파생 변수 생성 등)
#    - 동물 데이터와 보호소 데이터를 결합하고, 필요한 정보들을 집계합니다.
# 4. **데이터 적재 (Load):**
#    - `update_database`: 가공된 데이터를 Pandas DataFrame 형태로 만든 후,
#      SQLAlchemy를 통해 `shelters`와 `animals` 테이블에 한 번에 밀어 넣습니다.
#      (`if_exists='replace'` 옵션으로 기존 테이블을 삭제하고 새로 만듭니다.)
#
# [실행 방법]
# - 터미널에서 `python update_data.py` 명령으로 직접 실행합니다.
# - 주기적으로 자동 실행되도록 스케줄링(예: Cron, Windows Scheduler)하여
#   데이터를 최신 상태로 유지할 수 있습니다.
# ==============================================================================

import pandas as pd
import xml.etree.ElementTree as ET
import mysql.connector
from sqlalchemy import create_engine
import configparser
import os
from datetime import datetime, timedelta
import subprocess
import tempfile
from urllib.parse import quote
import requests
import json

# --- 경로 설정 ---
current_script_path = os.path.abspath(__file__)
streamlit_web_dir = os.path.dirname(current_script_path)
project_root = os.path.dirname(streamlit_web_dir)
CONFIG_PATH = os.path.join(project_root, 'config.ini')

# --- 설정 정보 로드 함수 ---
def get_db_config():
    """`config.ini`에서 [DB] 섹션의 설정을 읽어옵니다."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {CONFIG_PATH}")
    config.read(CONFIG_PATH)
    return config['DB']

def get_api_key():
    """`config.ini`에서 공공데이터포털 API 키를 읽어옵니다."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {CONFIG_PATH}")
    config.read(CONFIG_PATH)
    return config['API']['service_key']

def get_kakao_rest_api_key():
    """`config.ini`에서 카카오 지도 API 키를 읽어옵니다."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {CONFIG_PATH}")
    config.read(CONFIG_PATH)
    return config['API']['kakao_rest_api_key']

def fetch_abandoned_animals(api_key, bgnde, endde, upkind=''):
    """공공데이터포털에서 특정 기간과 축종의 유기동물 정보를 가져옵니다."""
    api_key_encoded = quote(api_key)
    endpoint = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/abandonmentPublic_v2"

    all_items = []
    page_no = 1
    num_of_rows = 1000 # API가 허용하는 최대 요청 개수

    while True:
        # API 요청 URL 구성
        url = f"{endpoint}?serviceKey={api_key_encoded}&bgnde={bgnde}&endde={endde}&pageNo={page_no}&numOfRows={num_of_rows}&_type=xml"
        if upkind:
            url += f"&upkind={upkind}"

        print(f"[DEBUG] API 요청 URL: {url}")

        # PowerShell을 사용하여 데이터를 임시 파일로 다운로드
        fp, temp_path = tempfile.mkstemp(suffix=".xml")
        os.close(fp)

        try:
            command = f"powershell -Command \"(New-Object System.Net.WebClient).DownloadFile('{url}', '{temp_path}')\""
            subprocess.run(command, check=True, shell=True, capture_output=True, text=True)

            with open(temp_path, 'rb') as f:
                xml_data = f.read()

            if not xml_data:
                print(f"경고: 페이지 {page_no}에서 빈 응답을 받았습니다.")
                break

            root = ET.fromstring(xml_data.decode('utf-8'))

            # API 응답 코드 확인
            result_code = root.findtext('.//resultCode', 'N/A')
            if result_code != '00':
                print(f"API 오류 발생 (코드: {result_code}, 메시지: {root.findtext('.//resultMsg', 'N/A')})")
                break

            items_in_page = root.findall('.//item')
            if not items_in_page:
                print(f"정보: 페이지 {page_no}에 더 이상 데이터가 없습니다.")
                break

            # 수집된 데이터를 리스트에 추가
            for item in items_in_page:
                item_dict = {child.tag: child.text for child in item}
                all_items.append(item_dict)

            total_count = int(root.findtext('.//totalCount', '0'))
            print(f"페이지 {page_no}에서 {len(items_in_page)}건 데이터 수집. (현재까지 총 {len(all_items)} / 전체 {total_count}건)")

            # 모든 데이터를 수집했으면 반복 종료
            if len(all_items) >= total_count:
                break

            page_no += 1

        except subprocess.CalledProcessError as e:
            print(f"PowerShell을 통한 데이터 다운로드 중 오류 발생: {e.stderr}")
            return None # 오류 발생 시 None 반환
        except ET.ParseError as e:
            print(f"XML 파싱 오류: {e}")
            return None
        except Exception as e:
            print(f"알 수 없는 오류 발생: {e}")
            return None
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    return all_items

def _fetch_sido_list(api_key):
    """보호소 목록 조회를 위해 내부적으로 사용되는 시/도 목록 조회 함수입니다."""
    api_key_encoded = quote(api_key)
    endpoint = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/sido_v2"
    url = f"{endpoint}?serviceKey={api_key_encoded}&numOfRows=100&_type=xml"
    
    fp, temp_path = tempfile.mkstemp(suffix=".xml")
    os.close(fp)
    
    try:
        command = f"powershell -Command \"(New-Object System.Net.WebClient).DownloadFile('{url}', '{temp_path}')\""
        subprocess.run(command, check=True, shell=True, capture_output=True, text=True)
        
        with open(temp_path, 'rb') as f:
            xml_data = f.read()
        
        if not xml_data:
            return []
            
        root = ET.fromstring(xml_data.decode('utf-8'))
        sido_list = []
        for item in root.findall('.//item'):
            sido_list.append({"code": item.findtext("orgCd"), "name": item.findtext("orgdownNm")})
        return sido_list
    except Exception as e:
        print(f"시/도 목록 조회 중 오류 발생: {e}")
        return []
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def _fetch_sigungu_list(api_key, sido_code):
    """특정 시/도에 속한 시/군/구 목록을 조회하는 내부 함수입니다."""
    api_key_encoded = quote(api_key)
    endpoint = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/sigungu_v2"
    url = f"{endpoint}?serviceKey={api_key_encoded}&upr_cd={sido_code}&_type=xml"
    
    fp, temp_path = tempfile.mkstemp(suffix=".xml")
    os.close(fp)
    
    try:
        command = f"powershell -Command \"(New-Object System.Net.WebClient).DownloadFile('{url}', '{temp_path}')\""
        subprocess.run(command, check=True, shell=True, capture_output=True, text=True)
        
        with open(temp_path, 'rb') as f:
            xml_data = f.read()
        
        if not xml_data:
            return []
            
        root = ET.fromstring(xml_data.decode('utf-8'))
        sigungu_list = []
        for item in root.findall('.//item'):
            sigungu_list.append({"upr_code": item.findtext("uprCd"), "code": item.findtext("orgCd"), "name": item.findtext("orgdownNm")})
        return sigungu_list
    except Exception as e:
        print(f"시/군/구 목록 조회 중 오류 발생: {e}")
        return []
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def fetch_shelters(api_key):
    """전국의 모든 동물보호소 정보를 시/도 및 시/군/구별로 순회하며 가져옵니다."""
    api_key_encoded = quote(api_key)
    endpoint = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/shelter_v2"
    all_shelters = []
    sido_list = _fetch_sido_list(api_key)

    if not sido_list:
        print("경고: 시도 목록을 가져오지 못하여 보호소 데이터를 수집할 수 없습니다.")
        return []

    for sido_info in sido_list:
        sido_code = sido_info['code']
        sido_name = sido_info['name']
        print(f"--- {sido_name} ({sido_code}) 지역의 시/군/구 목록 수집 ---")
        sigungu_list = _fetch_sigungu_list(api_key, sido_code)

        # 시/군/구 목록이 없는 경우 (e.g., 세종시), 시/도 코드를 시/군/구 코드로 사용하여 직접 조회 시도
        if not sigungu_list:
            print(f"정보: {sido_name}에 하위 시/군/구 목록이 없습니다. 시/도 코드로 직접 보호소 조회를 시도합니다.")
            sigungu_list = [{'upr_code': sido_code, 'code': sido_code, 'name': sido_name}]

        for sigungu_info in sigungu_list:
            sigungu_code = sigungu_info['code']
            sigungu_name = sigungu_info['name']
            print(f"--- {sido_name} > {sigungu_name} 보호소 데이터 수집 시작 ---")

            url = f"{endpoint}?serviceKey={api_key_encoded}&upr_cd={sido_code}&org_cd={sigungu_code}&_type=xml"
            print(f"[DEBUG] 보호소 API 요청 URL: {url}")

            fp, temp_path = tempfile.mkstemp(suffix=".xml")
            os.close(fp)

            try:
                command = f"powershell -Command \"(New-Object System.Net.WebClient).DownloadFile('{url}', '{temp_path}')\""
                subprocess.run(command, check=True, shell=True, capture_output=True, text=True)

                with open(temp_path, 'rb') as f:
                    xml_data = f.read()

                if not xml_data:
                    continue

                root = ET.fromstring(xml_data.decode('utf-8'))
                result_code = root.findtext('.//resultCode', 'N/A')

                if result_code != '00':
                    if result_code != '03':
                         print(f"API 오류 (코드: {result_code}, 메시지: {root.findtext('.//resultMsg', 'N/A')})")
                    continue

                items_in_page = root.findall('.//item')
                for item in items_in_page:
                    item_dict = {child.tag: child.text for child in item}
                    all_shelters.append(item_dict)

            except Exception as e:
                print(f"{sigungu_name} 보호소 조회 중 오류 발생: {e}")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
    
    return all_shelters

    api_key_encoded = quote(api_key)
    endpoint = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/shelter_v2"
    all_shelters = []
    sido_list = _fetch_sido_list(api_key)

    if not sido_list:
        print("경고: 시도 목록을 가져오지 못하여 보호소 데이터를 수집할 수 없습니다.")
        return []

    for sido_info in sido_list:
        sido_code = sido_info['code']
        sido_name = sido_info['name']
        print(f"--- {sido_name} ({sido_code}) 보호소 데이터 수집 시작 ---")

        page_no = 1
        collected_in_sido = 0
        total_in_sido = -1 # -1로 초기화하여 아직 totalCount를 받지 않았음을 표시

        while True:
            url = f"{endpoint}?serviceKey={api_key_encoded}&upr_cd={sido_code}&pageNo={page_no}&numOfRows=1000&_type=xml"
            print(f"[DEBUG] 보호소 API 요청 URL: {url}") # 디버깅을 위한 URL 출력

            fp, temp_path = tempfile.mkstemp(suffix=".xml")
            os.close(fp)

            try:
                command = f"powershell -Command \"(New-Object System.Net.WebClient).DownloadFile('{url}', '{temp_path}')\""
                subprocess.run(command, check=True, shell=True, capture_output=True, text=True)

                with open(temp_path, 'rb') as f:
                    xml_data = f.read()

                if not xml_data:
                    print(f"경고: {sido_name} 페이지 {page_no}에서 빈 응답을 받았습니다.")
                    break

                root = ET.fromstring(xml_data.decode('utf-8'))
                result_code = root.findtext('.//resultCode', 'N/A')

                if result_code != '00':
                    print(f"API 오류 (코드: {result_code}, 메시지: {root.findtext('.//resultMsg', 'N/A')})")
                    break

                items_in_page = root.findall('.//item')
                if not items_in_page:
                    print(f"정보: {sido_name} 페이지 {page_no}에 더 이상 데이터가 없습니다.")
                    break

                for item in items_in_page:
                    item_dict = {child.tag: child.text for child in item}
                    all_shelters.append(item_dict)
                
                collected_in_sido += len(items_in_page)

                if total_in_sido == -1: # 첫 요청 시에만 totalCount를 설정
                    total_in_sido = int(root.findtext('.//totalCount', '0'))

                print(f"{sido_name} 페이지 {page_no}에서 {len(items_in_page)}건 수집. (현재 시/도 누적 {collected_in_sido} / 전체 {total_in_sido}건)")

                if collected_in_sido >= total_in_sido:
                    break
                
                page_no += 1

            except Exception as e:
                print(f"{sido_name} 보호소 조회 중 오류 발생: {e}")
                break
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
    
    return all_shelters


def get_coordinates_from_address(address):
    """
    카카오 로컬 API를 사용하여 주어진 주소 문자열을 위도, 경도 좌표로 변환합니다.
    지도 시각화를 위해 필수적인 기능입니다.
    """
    kakao_api_key = get_kakao_rest_api_key()
    if not kakao_api_key:
        print("카카오 REST API 키가 설정되지 않았습니다.")
        return None, None

    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {kakao_api_key}"}
    params = {"query": address}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status() # HTTP 오류 발생 시 예외 처리
        data = response.json()
        
        if data and data['documents']:
            coords = data['documents'][0]
            return float(coords['y']), float(coords['x']) # (위도, 경도) 순서로 반환
        else:
            print(f"주소에 대한 좌표를 찾을 수 없습니다: {address}")
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"카카오 지오코딩 API 호출 중 오류 발생: {e}")
        return None, None
    except json.JSONDecodeError:
        print(f"카카오 지오코딩 API 응답 파싱 오류: {response.text}")
        return None, None

def preprocess_data(animal_df_raw, shelter_api_df_raw):
    print(f"[DEBUG] preprocess_data 시작. animal_df_raw 타입: {type(animal_df_raw)}, shelter_api_df_raw 타입: {type(shelter_api_df_raw)}")

    # -------------------------------------
    # 1. 동물 데이터 처리
    # -------------------------------------
    if isinstance(animal_df_raw, pd.DataFrame):
        animals_df = animal_df_raw.copy()
    else:
        animals_df = pd.DataFrame(animal_df_raw)

    if animals_df.empty:
        animals_df = pd.DataFrame()
        shelter_df_from_animals = pd.DataFrame()
    else:
        # 컬럼 이름 변경
        rename_map = {
            'desertionNo': 'desertion_no',
            'careNm': 'shelter_name',
            'age': 'age',
            'kindCd': 'species',
            'kindNm': 'kind_name',
            'specialMark': 'special_mark',
            'sexCd': 'sex',
            'noticeSdt': 'notice_date',
            'noticeNo': 'notice_no',
            'processState': 'process_state',
            'careAddr': 'care_addr',        # 여기 중요
            'careTel': 'care_tel',
            'colorCd': 'color',
            'weight': 'weight',
            'neuterYn': 'neuter',
            'happenPlace': 'happen_place',
            'upKindNm': 'upkind_name'
        }
        animals_df.rename(columns={k: v for k, v in rename_map.items() if k in animals_df.columns}, inplace=True)

        # 이미지 URL
        if 'popfile1' in animals_df.columns:
            animals_df['image_url'] = animals_df['popfile1']
        elif 'popfile2' in animals_df.columns:
            animals_df['image_url'] = animals_df['popfile2']
        else:
            animals_df['image_url'] = None

        animals_df.drop(columns=['popfile1', 'popfile2'], errors='ignore', inplace=True)

        # 날짜 변환
        if 'notice_date' in animals_df.columns:
            animals_df['notice_date'] = pd.to_datetime(animals_df['notice_date'], format='%Y%m%d', errors='coerce')

        # animal_name 생성
        if 'species' in animals_df.columns and 'sex' in animals_df.columns:
            animals_df['animal_name'] = animals_df['species'] + ' (' + animals_df['sex'] + ')'
        elif 'kind_name' in animals_df.columns:
            animals_df['animal_name'] = animals_df['kind_name']
        else:
            animals_df['animal_name'] = '정보 없음'

        animals_df['personality'] = '정보 없음'

        # 보호소 집계
        agg_dict = {
            'care_addr_animal': ('care_addr', 'first'),
            'region': ('care_addr', lambda x: x.iloc[0].split()[0] if x.notna().any() else '정보 없음'),
            'count': ('desertion_no', 'count'),
            'long_term': ('notice_date', lambda x: (x < pd.Timestamp.now() - pd.Timedelta(days=30)).sum()),
            'adopted': ('process_state', lambda x: (x == '종료(입양)').sum()),
            'species': ('species', lambda x: x.value_counts().index[0] if not x.empty else '정보 없음'),
            'kind_name': ('kind_name', lambda x: x.value_counts().index[0] if not x.empty else '정보 없음')
        }
        if 'image_url' in animals_df.columns:
            agg_dict['image_url'] = ('image_url', 'first')

        shelter_df_from_animals = animals_df.groupby('shelter_name').agg(**agg_dict).reset_index()

        if 'image_url' not in shelter_df_from_animals.columns:
            shelter_df_from_animals['image_url'] = None

    # -------------------------------------
    # 2. 보호소 데이터 처리
    # -------------------------------------
    if isinstance(shelter_api_df_raw, pd.DataFrame):
        shelter_api_df_processed = shelter_api_df_raw.copy()
    else:
        shelter_api_df_processed = pd.DataFrame(shelter_api_df_raw)

    if not shelter_api_df_processed.empty:
        rename_cols = {
            'careNm': 'shelter_name',
            'careRegNo': 'care_reg_no',
            'careAddr': 'care_addr_api',
            'careTel': 'care_tel',
            'dataStdDt': 'data_std_dt',
            'lat': 'lat_api',
            'lon': 'lon_api'
        }
        shelter_api_df_processed.rename(columns={k: v for k, v in rename_cols.items() if k in shelter_api_df_processed.columns}, inplace=True)

        shelter_api_df_processed['lat_api'] = pd.to_numeric(shelter_api_df_processed.get('lat_api', pd.NA), errors='coerce')
        shelter_api_df_processed['lon_api'] = pd.to_numeric(shelter_api_df_processed.get('lon_api', pd.NA), errors='coerce')
    else:
        shelter_api_df_processed = pd.DataFrame()

    # -------------------------------------
    # 3. 데이터 병합
    # -------------------------------------
    if shelter_df_from_animals.empty:
        merged_shelter_df = shelter_api_df_processed
    elif shelter_api_df_processed.empty:
        merged_shelter_df = shelter_df_from_animals
    else:
        merged_shelter_df = pd.merge(shelter_df_from_animals, shelter_api_df_processed, on='shelter_name', how='outer')

    if not merged_shelter_df.empty:
        care_addr_api = merged_shelter_df['care_addr_api'] if 'care_addr_api' in merged_shelter_df.columns else pd.Series(index=merged_shelter_df.index)
        care_addr_animal = merged_shelter_df['care_addr_animal'] if 'care_addr_animal' in merged_shelter_df.columns else pd.Series(index=merged_shelter_df.index)
        merged_shelter_df['care_addr'] = care_addr_api.fillna(care_addr_animal)

        # 좌표
        merged_shelter_df['lat'] = merged_shelter_df['lat_api'] if 'lat_api' in merged_shelter_df.columns else pd.NA
        merged_shelter_df['lon'] = merged_shelter_df['lon_api'] if 'lon_api' in merged_shelter_df.columns else pd.NA

        # 주소 좌표 캐싱
        cache = {}
        unique_addresses = merged_shelter_df.loc[
            merged_shelter_df['care_addr'].notna() &
            (merged_shelter_df['lat'].isna() | merged_shelter_df['lon'].isna()),
            'care_addr'
        ].unique()

        for addr in unique_addresses:
            if addr not in cache:
                lat, lon = get_coordinates_from_address(addr)
                cache[addr] = (lat, lon)

        for index, row in merged_shelter_df.iterrows():
            if pd.isna(row['lat']) or pd.isna(row['lon']):
                addr = row['care_addr']
                if addr in cache:
                    merged_shelter_df.at[index, 'lat'], merged_shelter_df.at[index, 'lon'] = cache[addr]

        merged_shelter_df['lat'] = merged_shelter_df['lat'].fillna(0)
        merged_shelter_df['lon'] = merged_shelter_df['lon'].fillna(0)

        merged_shelter_df.drop(columns=['care_addr_api', 'care_addr_animal', 'lat_api', 'lon_api'], inplace=True, errors='ignore')

        # 중복 확인용 출력
        before_count = len(merged_shelter_df)
        duplicate_count = merged_shelter_df.duplicated(subset=['shelter_name']).sum()
        print(f"[DEBUG] 중복 제거 전 보호소 개수: {before_count} (중복 {duplicate_count}개)")

        # 보호소 이름 기준으로 중복 제거
        merged_shelter_df.drop_duplicates(subset=['shelter_name'], inplace=True)

        after_count = len(merged_shelter_df)
        print(f"[DEBUG] 중복 제거 후 보호소 개수: {after_count}")

    # -------------------------------------
    # 4. 최종 컬럼 정리
    # -------------------------------------
    if 'image_url' not in animals_df.columns:
        animals_df['image_url'] = None

    final_animal_cols = [
        'desertion_no', 'shelter_name', 'animal_name', 'species', 'kind_name', 'age',
        'upkind_name', 'image_url', 'personality', 'special_mark', 'notice_date', 'notice_no',
        'sex', 'neuter', 'color', 'weight', 'care_tel', 'care_addr', 
        'happen_place', 
        'process_state' 
    ]
    existing_final_cols = [col for col in final_animal_cols if col in animals_df.columns]

    return merged_shelter_df, animals_df[existing_final_cols]

# --- 데이터 적재 (Load) 함수 ---
def update_database(shelter_df, animal_df):
    """
    가공된 데이터프레임을 데이터베이스의 테이블에 저장합니다.
    `if_exists='replace'` 옵션은 기존 테이블이 있다면 삭제하고 새로 만들기 때문에,
    항상 최신 데이터만 유지됩니다.
    """
    if shelter_df.empty or animal_df.empty:
        print("업데이트할 데이터가 없습니다.")
        return
        
    try:
        db_config = get_db_config()
        engine = create_engine(f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}")
        
        with engine.connect() as conn:
            # to_sql 메소드는 DataFrame을 SQL 테이블로 매우 편리하게 변환해줍니다.
            shelter_df.to_sql('shelters', conn, if_exists='replace', index=False)
            animal_df.to_sql('animals', conn, if_exists='replace', index=False)
        print("데이터베이스 업데이트 성공!")
    except Exception as e:
        print(f"데이터베이스 오류: {e}")

# --- 메인 실행 블록 ---
# 이 스크립트가 직접 실행될 때만 아래 코드가 동작합니다.
if __name__ == "__main__":
    print("실제 데이터로 DB 업데이트를 시작합니다...")
    try:
        API_KEY = get_api_key()
        if not API_KEY or 'YOUR_API_KEY' in API_KEY:
            print("!!! 경고: config.ini 파일에 실제 API 키를 입력하세요.")
        else:
            bgnde_str = '20250501'
            endde_str = '20250802'

            # 동물 데이터 수집 (개, 고양이, 기타)
            animal_types = {'개': '417000', '고양이': '422400', '기타': '429900'}
            all_animals_data = []

            for animal_name, animal_code in animal_types.items():
                print(f"--- {animal_name} 데이터 수집 시작 (기간: {bgnde_str} ~ {endde_str}) ---")
                items = fetch_abandoned_animals(API_KEY, bgnde_str, endde_str, upkind=animal_code)
                if isinstance(items, list):
                    all_animals_data.extend(items)
                    print(f"성공: {animal_name} 데이터 {len(items)}건 수집")
                else:
                    print(f"경고: {animal_name} 데이터를 가져오지 못했습니다.")

            # 🟢 중복 제거 (desertionNo 기준)
            print("중복 제거 중...")
            unique_animals = {
                item.get('desertionNo'): item for item in all_animals_data
            }
            all_animals_data = list(unique_animals.values())
            print(f"중복 제거 후 총 {len(all_animals_data)}건 남음")

            # 보호소 데이터 수집
            print("--- 보호소 데이터 수집 시작 ---")
            all_shelters_data = fetch_shelters(API_KEY)
            if not isinstance(all_shelters_data, list):
                print("경고: 보호소 데이터를 가져오지 못했습니다.")
                all_shelters_data = []

            # 전처리 및 DB 업데이트
            if all_animals_data or all_shelters_data:
                raw_animal_df = pd.DataFrame(all_animals_data)
                raw_shelter_api_df = pd.DataFrame(all_shelters_data)

                if not raw_animal_df.empty or not raw_shelter_api_df.empty:
                    print("데이터 전처리를 시작합니다...")
                    shelters, animals = preprocess_data(raw_animal_df, raw_shelter_api_df)

                    print("데이터베이스 업데이트를 시작합니다...")
                    update_database(shelters, animals)
                else:
                    print("API에서 수집된 동물 및 보호소 데이터가 없어 업데이트를 건너뜁니다.")

    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")