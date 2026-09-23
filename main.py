import streamlit as st
import requests
import re
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="학교 급식 식재료 비교", layout="wide")

st.title("🥗 학교별 주요 식재료 등장 빈도 다중 비교")

# ---------------------------------------------------------
# API Helper Functions
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def search_school(school_name):
    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {"Type": "json", "SCHUL_NM": school_name}
    try:
        res = requests.get(url, params=params).json()
        if "schoolInfo" in res:
            return res["schoolInfo"][1]["row"]
    except Exception:
        pass
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
    try:
        res = requests.get(url, params=params).json()
        if "mealServiceDietInfo" in res:
            return res["mealServiceDietInfo"][1]["row"]
    except Exception:
        pass
    return []

def extract_clean_menus(ddish_nm):
    raw_items = ddish_nm.split("<br/>")
    clean_items = []
    for item in raw_items:
        clean_name = re.sub(r'\([^)]*\)', '', item)
        clean_name = re.sub(r'[0-9\.\*\#]', '', clean_name).strip()
        if clean_name:
            clean_items.append(clean_name)
    return clean_items

# ---------------------------------------------------------
# UI 구성 및 설정
# ---------------------------------------------------------
st.sidebar.header("⚙️ 검색 및 식재료 설정")

# 1. 학교 선택 (필수 조건: 송탄고 기본 + 3개 이상)
selected_schools = st.sidebar.multiselect(
    "비교할 학교 선택 (3개 이상 권장):",
    options=["송탄고등학교", "평택고등학교", "신한고등학교", "비전고등학교", "한광고등학교", "경기고등학교"],
    default=["송탄고등학교", "평택고등학교", "신한고등학교"]
)

# 2. 날짜 선택
col1, col2 = st.sidebar.columns(2)
with col1:
    s_date = st.date_input("시작일", pd.to_datetime("2024-03-01"))
with col2:
    e_date = st.date_input("종료일", pd.to_datetime("2024-07-31"))

str_s_date = s_date.strftime("%Y%m%d")
str_e_date = e_date.strftime("%Y%m%d")

# 3. 조사할 식재료 가짓수 설정 (다중 선택 가능)
default_ingredients = ["닭", "돼지", "소", "오징어", "두부", "김치", "계란", "치즈"]
selected_ingredients = st.sidebar.multiselect(
    "조사할 식재료들을 선택/추가하세요:",
    options=default_ingredients + ["새우", "게", "돈가스", "소시지", "감자"],
    default=["닭", "돼지", "소", "오징어", "두부"]
)

# ---------------------------------------------------------
# 다중 식재료 빈도 분석 실행
# ---------------------------------------------------------
if len(selected_schools) < 3:
    st.warning("⚠️ 필수 조건을 위해 **학교를 3개 이상** 선택해 주세요.")

if selected_schools and selected_ingredients:
    analysis_results = []
    summary_data = []

    for sch_name in selected_schools:
        schools_found = search_school(sch_name)
        if not schools_found:
            st.error(f"'{sch_name}' 정보를 찾지 못했습니다.")
            continue

        info = schools_found[0]
        off_code = info["ATPT_OFCDC_SC_CODE"]
        sch_code = info["SD_SCHUL_CODE"]

        meals = get_meal_data(off_code, sch_code, str_s_date, str_e_date)
        total_days = len(meals)

        if total_days == 0:
            st.info(f"'{sch_name}'의 해당 기간 급식 데이터가 없습니다.")
            continue

        # 각 식재료별 출현 횟수 집계
        for ing in selected_ingredients:
            ing_days = 0
            examples = []

            for m in meals:
                ddish_nm = m.get("DDISH_NM", "")
                menu_list = extract_clean_menus(ddish_nm)

                found = [menu for menu in menu_list if ing in menu]
                if found:
                    ing_days += 1
                    examples.extend(found)

            rate = round((ing_days / total_days * 100), 1)
            
            analysis_results.append({
                "학교명": sch_name,
                "식재료": ing,
                "출현 일수": ing_days,
                "총 급식일수": total_days,
                "출현 비율(%)": rate,
                "메뉴 예시": ", ".join(list(set(examples))[:3])
            })

    # ---------------------------------------------------------
    # 시각화 (Plotly Multi-Bar Chart)
    # ---------------------------------------------------------
    if analysis_results:
        df = pd.DataFrame(analysis_results)

        st.subheader("📊 학교별 식재료 출현 비율 비교")

        # Plotly 그룹 막대 그래프 (학교별 식재료 비교)
        fig = px.bar(
            df,
            x="학교명",
            y="출현 비율(%)",
            color="식재료",
            barmode="group",
            text="출현 비율(%)",
            title="학교별 주요 식재료 제공 비율 (%) 비교",
            height=500
        )
        fig.update_traces(texttemplate='%{text}%', textposition='outside')
        fig.update_layout(yaxis_range=[0, max(df["출현 비율(%)"].max() + 12, 10)])

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # 상세 데이터 피벗 테이블 (가로: 학교, 세로: 식재료)
        st.subheader("📋 식재료별 출현 비율 요약표 (%)")
        pivot_df = df.pivot(index="식재료", columns="학교명", values="출현 비율(%)")
        st.dataframe(pivot_df, use_container_width=True)

        # 전체 상세 내역 보기
        with st.expander("🔍 상세 메뉴 예시 포함 전체 데이터 보기"):
            st.dataframe(df, hide_index=True, use_container_width=True)
