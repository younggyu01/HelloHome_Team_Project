"""
#  SSS  K   K        SSS  H   H IIIII EEEEE L     DDDD  EEEEE RRRR   SSS        4   4 TTTTT H   H       RRRR   OOO   OOO  K   K IIIII EEEEE  SSS  
# S     K  K        S     H   H   I   E     L     D   D E     R   R S           4   4   T   H   H       R   R O   O O   O K  K    I   E     S     
#  SSS  KKK          SSS  HHHHH   I   EEEEE L     D   D EEEEE RRRR   SSS        44444   T   HHHHH       RRRR  O   O O   O KKK     I   EEEEE  SSS  
#     S K  K            S H   H   I   E     L     D   D E     R  R      S           4   T   H   H       R  R  O   O O   O K  K    I   E         S 
# SSSS  K   K       SSSS  H   H IIIII EEEEE LLLLL DDDD  EEEEE R   R SSSS            4   T   H   H       R   R  OOO   OOO  K   K IIIII EEEEE SSSS  

repository master   :   박시훈(cooperear)

file_name           :   final_api-parse.py

"""



from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup

import subprocess
import xmltodict
import json
from pandas import DataFrame
import urllib.parse

import urllib.parse
import subprocess
import xmltodict
import pandas as pd
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from IPython.core.display import HTML


import os
import json
import time
import urllib.parse
import subprocess
import xmltodict
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from bs4 import BeautifulSoup

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns


class AbandonedAnimals:
    """
    유기 동물 데이터를 공공 API를 통해 수집하는 클래스입니다.
    """

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('api_key')
        self.encoding_api_key = os.getenv('encoding_api_key')
        self.decoding_api_key = os.getenv('decoding_api_key')
        self.kakao_api_key = os.getenv('kakao_api_key')

        self.dataframe = None

        # API 키 누락 시 예외 발생
        if not all([self.api_key, self.encoding_api_key, self.decoding_api_key, self.kakao_api_key]):
            raise ValueError("필수 API 키가 누락되었습니다. .env 파일을 확인하세요.")

    def fetch_abandoned_animals(self, *dates):
        """
        공공 API를 통해 유기 동물 데이터를 수집합니다.

        Args:
            dates: 시작일과 종료일을 (bgupd, enupd) 형식으로 전달 가능

        Returns:
            pd.DataFrame: 수집된 데이터프레임
        """
        base_url = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/abandonmentPublic_v2"
        page_no = 1
        all_items = []

        while True:
            if len(dates) == 0:
                params = {
                    "serviceKey": self.decoding_api_key,
                    "pageNo": page_no,
                    "numOfRows": 1000,
                }
            else:
                params = {
                    "serviceKey": self.decoding_api_key,
                    "pageNo": page_no,
                    "bgupd": str(dates[0]),
                    "enupd": str(dates[1]),
                    "numOfRows": 1000,
                }

            encoded_params = urllib.parse.urlencode(params, quote_via=urllib.parse.quote, encoding='utf-8')
            full_url = f"{base_url}?{encoded_params}"
            print(full_url)
            print(f"요청 중: page {page_no}")

            result = subprocess.run(['curl', '-s', full_url], capture_output=True, text=True, encoding='utf-8')
            xml_data = result.stdout

            try:
                parsed_dict = xmltodict.parse(xml_data)
                items = parsed_dict.get('response', {}).get('body', {}).get('items', {})

                if not items or 'item' not in items:
                    print("데이터 종료")
                    break

                item_list = items['item']
                if isinstance(item_list, dict):
                    item_list = [item_list]

                all_items.extend(item_list)
                page_no += 1

            except Exception as e:
                print("오류 발생:", e)
                print("원본 XML 데이터:\n", xml_data)
                return 'error'

        df = pd.DataFrame(all_items)
        print(f"총 수집 데이터 수: {len(df)}")
        df_cleaned = df.dropna(axis=1)
        df_cleaned.to_json('df_cleaned.json', force_ascii=False)

        self.dataframe = df_cleaned
        return self.dataframe
    
    def save_dataframe_to_json(self):
        self.dataframe.to_json('Abandoned_Animals.json')
    
