import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os # 파일 경로 확인용 모듈 추가

# 1. 페이지 설정
st.set_page_config(page_title="식단 재료 산출기", layout="wide")
st.title("☁️ 구글 시트 연동: 식단 재료 산출기")

# 2. 설정: 주소 고정
# (사용자분이 알려주신 주소가 그대로 들어있습니다)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1oLK-Z58FmzQPIaMcZOK0Ob8Ee5VFw-CvJEduJwlYvQk/edit?gid=1265386338#gid=1265386338"

# --- [수정된 핵심 함수] 구글 시트 연결 ---
# 내 컴퓨터에서는 파일을 찾고, 서버에서는 Secrets를 찾도록 똑똑하게 바뀐 부분입니다.
@st.cache_data(ttl=60)
def load_data_from_sheet(url):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # 1. 내 컴퓨터에 키 파일이 있는지 확인
        if os.path.exists('service_account.json'):
            # 파일이 있으면 파일로 인증 (내 컴퓨터용)
            creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
        else:
            # 파일이 없으면 서버의 비밀키(Secrets)로 인증 (Streamlit Cloud용)
            # 주의: Secrets가 설정되어 있어야 작동합니다.
            key_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
        
        client = gspread.authorize(creds)
        doc = client.open_by_url(url)
        worksheet = doc.worksheet("데이터")
        data = worksheet.get_all_records()
        return pd.DataFrame(data)

    except Exception as e:
        # 에러가 나면 화면에 이유를 보여줍니다.
        st.error(f"데이터 로드 실패! 오류 내용: {e}")
        return pd.DataFrame()

# --- 메인 로직 ---
# 데이터를 불러옵니다.
df_data = load_data_from_sheet(SHEET_URL)

if not df_data.empty:
    # 데이터 전처리 (빈 재료명 제거)
    if '재료명(B)' in df_data.columns:
        df_data = df_data[df_data['재료명(B)'] != '']

    # 로드 성공 표시
    st.toast("✅ 데이터 로드 성공!", icon="✅")

    # 메뉴 선택 기능
    if '요리명(A)' in df_data.columns:
        all_menus = df_data['요리명(A)'].unique().tolist()
        
        st.divider()
        st.subheader("1️⃣ 오늘의 식단을 선택하세요")
        
        selected_menus = st.multiselect(
            "아래 박스를 클릭하여 메뉴를 추가하세요.",
            options=all_menus,
            default=[]
        )

        if selected_menus:
            # 계산 로직
            df_filtered = df_data[df_data['요리명(A)'].isin(selected_menus)]

            # 재료 집계
            df_ingredients = df_filtered[df_filtered['구분(E)'] == '재료']
            result_ingredients = df_ingredients.groupby(['재료명(B)', '단위(D)'])['수량(C)'].sum().reset_index()
            result_ingredients.columns = ['재료명', '단위', '총 필요량']
            
            # 소스 집계
            df_sauce = df_filtered[df_filtered['구분(E)'] == '소스']
            result_sauce = df_sauce.groupby(['재료명(B)', '단위(D)'])['수량(C)'].sum().reset_index()
            result_sauce.columns = ['소스명', '단위', '총 필요량']

            # 결과 출력
            st.divider()
            st.subheader("2️⃣ 산출 결과")
            col1, col2 = st.columns(2)

            with col1:
                st.info(f"🥬 **재료 리스트 ({len(result_ingredients)}종)**")
                st.dataframe(result_ingredients, use_container_width=True, hide_index=True)

            with col2:
                st.warning(f"🧂 **소스 리스트 ({len(result_sauce)}종)**")
                st.dataframe(result_sauce, use_container_width=True, hide_index=True)
    else:
        st.error("엑셀 파일에 '요리명(A)' 컬럼이 없습니다.")
else:
    # 데이터가 비어있으면 멈춤 (에러 메시지는 위 함수에서 이미 출력됨)
    st.stop()