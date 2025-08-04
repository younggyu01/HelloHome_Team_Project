# ==============================================================================
# utils.py - 공통 유틸리티 모듈
# ==============================================================================
# 이 파일은 프로젝트의 여러 부분에서 공통적으로 사용될 수 있는
# 보조 함수들을 모아놓은 곳입니다.
#
# [사용 목적]
# - **코드 중복 방지:** 여러 파일에서 동일한 기능이 필요할 때, 여기에 함수를
#   정의하고 각 파일에서 임포트하여 사용함으로써 코드의 중복을 줄입니다.
# - **유지보수성 향상:** 공통 로직이 한 곳에 모여있으므로, 수정이 필요할 때
#   이 파일만 수정하면 모든 곳에 반영되어 유지보수가 용이해집니다.
# - **프로젝트 구조화:** 특정 기능에 종속되지 않는 범용적인 함수들을
#   별도로 관리하여 프로젝트 구조를 더 깔끔하게 만듭니다.
#
# [예시]
# - 날짜/시간 포맷팅 함수
# - 특정 문자열을 정제하는 함수
# - 복잡한 계산을 수행하는 함수 등
# ==============================================================================
import configparser
import os
import base64
from datetime import datetime

def get_image_as_base64(path: str) -> str | None:
    """
    이미지 파일을 읽어 Base64로 인코딩된 문자열을 반환합니다.
    파일을 찾지 못하면 None을 반환합니다.

    Args:
        path (str): 이미지 파일 경로

    Returns:
        str | None: Base64 인코딩된 이미지 문자열 또는 None
    """
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return None

def format_date(dt: datetime) -> str:
    """
    datetime 객체를 'YYYY-MM-DD' 형식의 문자열로 변환합니다.

    Args:
        dt (datetime): 변환할 datetime 객체

    Returns:
        str: 포맷팅된 날짜 문자열
    """
    return dt.strftime("%Y-%m-%d")

def get_db_config() -> dict:
    """
    프로젝트 루트에 있는 config.ini에서 DB 설정 정보를 읽어 반환합니다.
    """
    current_file = os.path.abspath(__file__)
    streamlit_web_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(streamlit_web_dir)

    config_path = os.path.join(project_root, "config.ini")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"config.ini 파일을 찾을 수 없습니다: {config_path}")

    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")

    if "DB" not in config:
        raise KeyError(f"[DB] 섹션을 config.ini에서 찾을 수 없습니다. (path={config_path})")

    return {
        "host": config["DB"]["host"],
        "user": config["DB"]["user"],
        "password": config["DB"]["password"],
        "database": config["DB"]["database"],
        "port": int(config["DB"]["port"])
    }
