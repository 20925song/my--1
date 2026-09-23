import streamlit as st
import requests
import re
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="학교 급식 식재료 비교", layout="wide")

st.title("🏫 학교별 급식 식재료 등장 빈도 비교")
st.caption("송탄고등학교를 포함하여 여러 학교의 특정 식재료 출현 빈도를 비교합니다.")

# ---------------------------------------------------------
# API Helper Functions
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def search_school(school_name):
    """학교 이름으로 코드 조회"""
    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {"Type": "json", "SCHUL_NM": school_name}
    try:
        res = requests.get(url, params=params).json()
        if "schoolInfo" in res:
            return res["schoolInfo"][1]["row"]
    except:
        pass
    return []

@st.cache_data(ttl=3600)
def get_meal_data(office_code, school_code, start_date, end_date):
    """급식 식단 정보 조회 (중식)"""
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",
        "MLSV_FROM_YMD": start_date,
        "MLSV_TO_YMD": end_date,
        "pSize": 1000,
        "pIndex": 1
    }
    try:
        res = requests.get(url, params=params).json()
        if "mealServiceDietInfo" in res:
            return res["mealServiceDietInfo"][1]["row"]
    except:
        pass
    return []

def parse_menu(ddish_nm):
    """알레르기 번호 및 특수문자 제거"""
    items = ddish_nm.split("<br/>")
    cleaned = []
    for item in items:
        c = re.sub(r'[\([\#\d\.\)]+', '', item).strip()
        if c:
            cleaned.append(c)
    return cleaned

# ---------------------------------------------------------
# UI 구성 및 설정
# ---------------------------------------------------------
st.sidebar.header("⚙️ 비교 설정")

# [필수 조건] 송탄고등학교 기본 선택 + 3개 이상 선택 가능
default_schools = ["송탄고등학교", "평택고등학교", "신한고등학교"]
selected_schools = st.sidebar.multiselect(
    "비교할 학교 선택 (3개 이상 권장):",
    options=["송탄고등학교", "평택고등학교", "신한고등학교", "비전고등학교", "한광고등학교", "경기고등학교"],
    default=default_schools
)

# 날짜 지정
col1, col2 = st.sidebar.columns(2)
with col1:
    s_date = st.date_input("시작일", pd.to_datetime("2024-03-01"))
with col2:
    e_date = st.date_input("종료일", pd.to_datetime("2024-07-31"))

str_s_date = s_date.strftime("%Y%m%d")
str_e_date = e_date.strftime("%Y%m%d")

# 조사할 식재료 입력
target_keyword = st.sidebar.text_input("조사할 식재료/단어:", value="닭")

# ---------------------------------------------------------
# 데이터 로드 및 분석
# ---------------------------------------------------------
if len(selected_schools) < 3:
    st.warning("⚠️ 필수 조건 충족을 위해 **학교를 3개 이상** 선택해 주세요!")

if selected_schools:
    result_data = []

    for sch_name in selected_schools:
        info_list = search_school(sch_name)
        if not info_list:
            st.error(f"'{sch_name}' 정보를 찾을 수 없습니다.")
            continue
        
        info = info_list[0]
        off_code = info["ATPT_OFCDC_SC_CODE"]
        sch_code = info["SD_SCHUL_CODE"]
        
        meals = get_meal_data(off_code, sch_code, str_s_date, str_e_date)
        
        total_days = len(meals)
        hits = 0
        
        for m in meals:
            parsed = parse_menu(m["DDISH_NM"])
            # 입력한 식재료 키워드가 포함되었는지 확인
            if any(target_keyword in item for item in parsed):
                hits += 1
                
        rate = round((hits / total_days * 100), 1) if total_days > 0 else 0
        result_data.append({
            "학교명": sch_name,
            "총 급식일수": total_days,
            "등장 횟수": hits,
            "출현 비율(%)": rate
        })

    if result_data:
        df = pd.DataFrame(result_data)
        
        st.subheader(f"📊 '{target_keyword}' 식재료 출현 빈도 비교")
        
        c1, c2 = st.columns([3, 2])
        
        with c1:
            # Plotly 그래프 시각화
            fig = px.bar(
                df,
                x="학교명",
                y="출현 비율(%)",
                text="출현 비율(%)",
                color="학교명",
                title=f"학교별 '{target_keyword}'(이)가 포함된 메뉴 출현 비율",
                height=420
            )
            fig.update_traces(texttemplate='%{text}%', textposition='outside')
            fig.update_layout(yaxis_range=[0, max(df["출현 비율(%)"].max() + 15, 10)])
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.write("### 📋 비교 표")
            st.dataframe(df, hide_index=True, use_container_width=True)
