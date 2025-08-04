import pandas as pd
import json
import os
from sqlalchemy import create_engine
from utils import get_db_config  # 기존 utils.py에 있는 DB 설정 함수 재사용

# --- JSON -> DataFrame 로딩 함수 ---
def load_json_to_df():
    base_path = os.path.join(os.path.dirname(__file__), "data")

    with open(os.path.join(base_path, "cat_info.json"), "r", encoding="utf-8") as f:
        cat_data = json.load(f)
    cat_df = pd.DataFrame(cat_data)

    with open(os.path.join(base_path, "dog_info.json"), "r", encoding="utf-8") as f:
        dog_data = json.load(f)
    dog_df = pd.DataFrame(dog_data)

    # 리스트나 딕셔너리를 문자열(JSON)으로 변환
    for df in [cat_df, dog_df]:
        if "태그" in df.columns:
            df["태그"] = df["태그"].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, list) else x)
        if "임보 조건" in df.columns:
            df["임보 조건"] = df["임보 조건"].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else x)
        if "히스토리" in df.columns:
            df["히스토리"] = df["히스토리"].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else x)
        if "건강 정보" in df.columns:
            df["건강 정보"] = df["건강 정보"].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else x)

    return cat_df, dog_df


# --- 웹스크래핑 데이터 DB 저장 함수 ---
def update_web_database(cat_df, dog_df):
    if cat_df.empty and dog_df.empty:
        print("업데이트할 데이터가 없습니다.")
        return

    try:
        db_config = get_db_config()
        engine = create_engine(
            f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@"
            f"{db_config['host']}:{db_config['port']}/{db_config['database']}?charset=utf8mb4"
        )

        with engine.connect() as conn:
            if not cat_df.empty:
                cat_df.to_sql('web_cats', conn, if_exists='replace', index=False)
                print(f"web_cats 테이블에 {len(cat_df)}개 데이터 저장 완료!")
            if not dog_df.empty:
                dog_df.to_sql('web_dogs', conn, if_exists='replace', index=False)
                print(f"web_dogs 테이블에 {len(dog_df)}개 데이터 저장 완료!")

        print("웹 데이터베이스 업데이트 성공!")
    except Exception as e:
        print(f"데이터베이스 오류: {e}")


if __name__ == "__main__":
    cat_df, dog_df = load_json_to_df()
    update_web_database(cat_df, dog_df)
