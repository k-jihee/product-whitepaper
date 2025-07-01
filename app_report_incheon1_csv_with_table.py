
import streamlit as st
import pandas as pd
import re
import os

st.set_page_config(layout="wide")  # ✅ 이 줄 추가

PASSWORD = "samyang!11"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 로그인 필요")
    password = st.text_input("비밀번호를 입력하세요", type="password")
    if password == PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    elif password:
        st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop()

try:
    df = pd.read_csv("product_data.csv", encoding="utf-8")
except Exception as e:
    st.error(f"❌ CSV 파일을 불러오는 중 오류 발생: {e}")
    st.stop()

# 제품 계층구조 컬럼이 없을 경우 자동 추가
if "계층구조_2레벨" not in df.columns or "계층구조_3레벨" not in df.columns:
    def get_hierarchy(code):
        if code.startswith("GIB"):
            return "FG0009 : 부산물", "부산물"
        elif code.startswith("GID1") or code.startswith("GID2") or code.startswith("GID3"):
            return "FG0001 : 포도당", "포도당분말"
        elif code.startswith("GID6"): or code.startswith("GID7"):
            return "FG0001 : 포도당", "포도당액상"
        elif code.startswith("GIS62"):
            return "FG0002 : 물엿", "고감미75"
        elif code.startswith("GIS601") or code.startswith("GIS631"):
            return "FG0002 : 물엿", "고감미82"
        elif code.startswith("GIS701") or code.startswith("GIS703"):
            return "FG0002 : 물엿", "일반75"
        elif code.startswith("GIS401"):
            return "FG0002 : 물엿", "일반82"
        elif code.startswith("GIS201"):
            return "FG0002 : 물엿", "저당물엿"
        elif code.startswith("GIS22"):
            return "FG0002 : 물엿", "제네덱스"
        elif code.startswith("GIS23"):
            return "FG0002 : 물엿", "가루엿"
        elif code.startswith("GIS90"):
            return "FG0002 : 물엿", "맥아82"
        elif code.startswith("GIS92"):
            return "FG0002 : 물엿", "맥아75"
        elif code.startswith("GIF501") or code.startswith("GIF502"):
            return "FG0003 : 과당", "55%과당"
        elif code.startswith("GIC002"):
            return "FG0004 : 전분", "일반전분"
        elif code.startswith("GIC"):
            return "FG0004 : 전분", "변성전분"            
        elif code.startswith("GISQ190"):
            return "FG0006 : 알룰로스", "알룰로스 액상"
        elif code.startswith("GIN113"):
            return "FG0007 : 올리고당", "프락토올리고당 액상"
        elif code.startswith("GIN121") or code.startswith("GIN122"):
            return "FG0007 : 올리고당", "이소말토올리고 액상"
        elif code.startswith("GIN131"):
            return "FG0007 : 올리고당", "갈락토"
        elif code.startswith("GIN151"):
            return "FG0007 : 올리고당", "말토올리고"
        elif code.startswith("GIP202") or code.startswith("GIP204"):
            return "FG0008 : 식이섬유", "폴리덱스트로스"
        elif code.startswith("GIS242") or code.startswith("GIS240"):
            return "FG0008 : 식이섬유", "NMD 액상/분말"
        else:
            return "기타", "기타"

    df[["계층구조_2레벨", "계층구조_3레벨"]] = df["제품코드"].apply(lambda x: pd.Series(get_hierarchy(x)))

st.title("🏭 인천 1공장 제품백서")

with st.container():
    st.markdown("### 📋 인천 1공장 전제품 목록")
    st.markdown(
        """
        <style>
        .custom-df-container {
           max-width:700px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container():
        st.markdown('<div class="custom-df-container">', unsafe_allow_html=True)
        st.dataframe(df[["계층구조_2레벨", "계층구조_3레벨", "제품코드", "제품명"]]
                     .dropna(subset=["제품코드", "제품명"])
                     .reset_index(drop=True), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
