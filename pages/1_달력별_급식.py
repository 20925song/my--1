import streamlit as st
import requests
import re
import pandas as pd

st.set_page_config(page_title="달력별 급식 보기", layout="wide")

st.title("📅 달력별 급식 식단 조회")

@st.cache_data(ttl=3600)
def search_school(school_name):
    url = "https://open.neis.go.kr/hub/schoolInfo"
    res = requests.get(url, params={"Type": "json", "SCHUL_NM": school_name}).json()
    if "schoolInfo" in res:
        return res["schoolInfo"][1]["row"]
    return []

@st.cache_data(ttl=3600)
def get_meal_data(office_code, school_code, start_date, end_date):
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
    res = requests.get(url, params=params).json()
    if "mealServiceDietInfo" in res:
        return res["mealServiceDietInfo"][1]["row"]
    return []

school_name = st.text_input("학교 이름을 입력하세요:", value="송탄고등학교")
selected_date = st.date_input("조회할 날짜를 선택하세요:")
str_date = selected_date.strftime("%Y%m%d")

if school_name:
    schools = search_school(school_name)
    if schools:
        info = schools[0]
        meals = get_meal_data(info["ATPT_OFCDC_SC_CODE"], info["SD_SCHUL_CODE"], str_date, str_date)
        
        st.subheader(f"🔍 {info['SCHUL_NM']} - {selected_date.strftime('%Y년 %m월 %d일')} 급식")
        
        if meals:
            m = meals[0]
            menu_clean = m["DDISH_NM"].replace("<br/>", "\n")
            # 알레르기 번호 제거
            menu_clean = re.sub(r'[\([\#\d\.\)]+', '', menu_clean)
            
            col1, col2 = st.columns(2)
            with col1:
                st.info("### 🍱 오늘의 메뉴")
                st.text(menu_clean)
            with col2:
                st.success("### 🔥 칼로리 정보")
                st.write(m.get("CAL_INFO", "정보 없음"))
        else:
            st.info("해당 날짜에는 급식 정보가 없습니다.")
    else:
        st.error("학교를 찾을 수 없습니다.")
