import streamlit as st
import requests
import re
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="학교 급식 식재료 비교", layout="wide")

st.title("🏫 학교별 급식 식재료 등장 빈도 비교")

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
    except Exception as e:
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
        "MMEAL_SC_CODE": "2",  # 중식
        "MLSV_FROM_YMD": start_date,
        "MLSV_TO_YMD": end_date,
        "pSize": 1000,
        "pIndex": 1
    }
    try:
        res = requests.get(url, params=params).json()
        if "mealServiceDietInfo" in res:
            return res["mealServiceDietInfo"][1]["row"]
    except Exception as e:
        pass
    return []

def extract_clean_menus(ddish_nm):
    """
    급식 메뉴 항목에서 알레르기/원산지 번호 등 특수문자를 제거하고
    깨끗한 메뉴 이름 리스트로 반환
    """
    # <br/> 태그 기준으로 개별 메뉴 분리
    raw_items = ddish_nm.split("<br/>")
    clean_items = []
    
    for item in raw_items:
        # 1. 괄호와 숫자, 점, 특수문자 제거 (예: "닭갈비(1.2.5.6)" -> "닭갈비")
        clean_name = re.sub(r'\([^)]*\)', '', item)  # 괄호 안 전체 제거
        clean_name = re.sub(r'[0-9\.\*\#]', '', clean_name)  # 남은 숫자/특수문자 제거
        clean_name = clean_name.strip()
        
        if clean_name:
            clean_items.append(clean_name)
            
    return clean_items

# ---------------------------------------------------------
# UI 구성
# ---------------------------------------------------------
st.sidebar.header("⚙️ 검색 및 비교 설정")

selected_schools = st.sidebar.multiselect(
    "비교할 학교 선택 (3개 이상 권장):",
    options=["송탄고등학교", "평택고등학교", "신한고등학교", "비전고등학교", "한광고등학교", "경기고등학교"],
    default=["송탄고등학교", "평택고등학교", "신한고등학교"]
)

col1, col2 = st.sidebar.columns(2)
with col1:
    s_date = st.date_input("시작일", pd.to_datetime("2024-03-01"))
with col2:
    e_date = st.date_input("종료일", pd.to_datetime("2024-07-31"))

str_s_date = s_date.strftime("%Y%m%d")
str_e_date = e_date.strftime("%Y%m%d")

# 원하는 식재료 키워드 입력
target_keyword = st.sidebar.text_input("찾을 식재료 키워드 (예: 닭, 돼지, 오징어, 두부, 김치)", value="닭").strip()

# ---------------------------------------------------------
# 식재료 빈도 분석 실행
# ---------------------------------------------------------
if len(selected_schools) < 3:
    st.warning("⚠️ 필수 조건을 위해 학교를 3개 이상 선택해 주세요.")

if selected_schools and target_keyword:
    results = []

    for sch_name in selected_schools:
        schools_found = search_school(sch_name)
        if not schools_found:
            st.error(f"'{sch_name}' 정보를 찾지 못했습니다.")
            continue

        info = schools_found[0]
        off_code = info["ATPT_OFCDC_SC_CODE"]
        sch_code = info["SD_SCHUL_CODE"]

        # 급식 데이터 API 요청
        meals = get_meal_data(off_code, sch_code, str_s_date, str_e_date)

        total_days = len(meals)  # 급식이 제공된 총 일수
        keyword_days = 0         # 식재료가 나온 급식 일수
        matching_menu_examples = [] # 발견된 메뉴 예시 저장

        for m in meals:
            ddish_nm = m.get("DDISH_NM", "")
            menu_list = extract_clean_menus(ddish_nm)

            # 검색할 식재료 키워드가 포함된 메뉴 추출
            found_menus = [menu for menu in menu_list if target_keyword in menu]

            if found_menus:
                keyword_days += 1
                matching_menu_examples.extend(found_menus)

        # 출현 비율 계산 (%)
        hit_rate = round((keyword_days / total_days * 100), 1) if total_days > 0 else 0.0

        results.append({
            "학교명": sch_name,
            "총 급식 제공일": f"{total_days}일",
            "식재료 출현 일수": f"{keyword_days}일",
            "출현 비율(%)": hit_rate,
            "발견된 관련 메뉴 예시": ", ".join(list(set(matching_menu_examples))[:4])  # 중복 제거 후 최대 4개
        })

    # ---------------------------------------------------------
    # 시각화 (Plotly)
    # ---------------------------------------------------------
    if results:
        df = pd.DataFrame(results)

        st.subheader(f"📊 '{target_keyword}' 식재료 등장 빈도 분석 결과")

        # Plotly 막대그래프
        fig = px.bar(
            df,
            x="학교명",
            y="출현 비율(%)",
            text="출현 비율(%)",
            color="학교명",
            title=f"조회 기간 중 '{target_keyword}' 식재료 제공 비율 (%)",
            labels={"출현 비율(%)": "제공 비율 (%)"},
            height=400
        )
        fig.update_traces(texttemplate='%{text}%', textposition='outside')
        fig.update_layout(yaxis_range=[0, max(df["출현 비율(%)"].max() + 15, 10)])

        st.plotly_chart(fig, use_container_width=True)

        st.write("### 📋 상세 비교 표")
        st.dataframe(df, hide_index=True, use_container_width=True)
