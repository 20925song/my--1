import streamlit as st
import requests
import re
from collections import Counter
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="메뉴별 급식 분석", layout="wide")

st.title("🏆 우리 학교 최다 등장 메뉴 Top 10")

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

school_name = st.text_input("학교 이름:", value="송탄고등학교")

c1, c2 = st.columns(2)
with c1:
    s_date = st.date_input("조회 시작일", pd.to_datetime("2024-03-01"))
with c2:
    e_date = st.date_input("조회 종료일", pd.to_datetime("2024-07-31"))

if school_name:
    schools = search_school(school_name)
    if schools:
        info = schools[0]
        meals = get_meal_data(
            info["ATPT_OFCDC_SC_CODE"], 
            info["SD_SCHUL_CODE"], 
            s_date.strftime("%Y%m%d"), 
            e_date.strftime("%Y%m%d")
        )
        
        all_items = []
        for m in meals:
            items = m["DDISH_NM"].split("<br/>")
            for item in items:
                clean = re.sub(r'[\([\#\d\.\)]+', '', item).strip()
                if clean:
                    all_items.append(clean)
                    
        if all_items:
            counts = Counter(all_items).most_common(10)
            df_top = pd.DataFrame(counts, columns=["메뉴명", "등장 횟수"])
            
            st.subheader(f"📊 {info['SCHUL_NM']} 메뉴 등장 횟수 Top 10")
            
            fig = px.bar(
                df_top,
                x="등장 횟수",
                y="메뉴명",
                orientation='h',
                text="등장 횟수",
                title="가장 자주 나온 메뉴",
                color="등장 횟수",
                color_continuous_scale="Viridis"
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_top, hide_index=True)
