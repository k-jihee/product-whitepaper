import streamlit as st
import pandas as pd
import re
import os

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

def clean_int(value):
    try:
        cleaned = re.sub(r"[^\d.]", "", str(value))
        if cleaned == "":
            return "-"
        return f"{int(float(cleaned)):,} KG"
    except (ValueError, TypeError):
        return "-"

def parse_spec_text(spec_text):
    if pd.isna(spec_text):
        return {}
    lines = str(spec_text).splitlines()
    spec_dict = {}
    for line in lines:
        match = re.match(r"\s*\d+\.\s*(.+?)\s*:\s*(.+)", line)
        if match:
            key, value = match.groups()
            spec_dict[key.strip()] = value.strip()
    return spec_dict

st.title("🏭 인천 1공장 제품백서")
st.markdown("### 📋 인천 1공장 전제품 목록")
st.dataframe(df[["제품코드", "제품명"]].dropna().reset_index(drop=True))
st.markdown("---")
st.markdown('<h4>🔍 <b>제품코드 또는 제품명을 입력하세요</b></h4>', unsafe_allow_html=True)

query = st.text_input("예: GIB1010 또는 글루텐피드", key="query_input")

if query:
    results = df[df["제품코드"].astype(str).str.contains(query, case=False, na=False) |
                 df["제품명"].astype(str).str.contains(query, case=False, na=False)]

    if not results.empty:
        for _, row in results.iterrows():
            prod_2022 = clean_int(row.get('생산실적(2022)'))
            prod_2023 = clean_int(row.get('생산실적(2023)'))
            prod_2024 = clean_int(row.get('생산실적(2024)'))

            internal_spec = parse_spec_text(row.get("사내규격(COA)", ""))
            legal_spec = parse_spec_text(row.get("법적규격", ""))
            all_keys = set(internal_spec.keys()) | set(legal_spec.keys()) | {"성상"}

            성상_row = '<tr><td>성상</td><td colspan="2">{}</td></tr>'.format(row.get("성상", "-"))
            spec_rows = ""
            for key in sorted(all_keys):
                if key == "성상":
                    continue
                legal = legal_spec.get(key, "-")
                internal = internal_spec.get(key, "-")
                spec_rows += "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(key, legal, internal)

            # 🔽 이미지 처리 HTML 코드로 변환
            image_html = ""
            img_src = row.get("한도견본", "")
if pd.notna(img_src):
    for idx, link in enumerate(str(img_src).split(","), start=1):
        link = link.strip()
        if link.startswith("https://github.com/") and "/blob/" in link:
            link = link.replace("https://github.com", "https://raw.githubusercontent.com").replace("/blob/", "/")

        if link.startswith("http"):
            st.image(link, width=300, caption=f"한도견본 {idx}")
        elif os.path.exists(link):
            st.image(link, width=300, caption=f"한도견본 {idx}")
        else:
            st.warning(f"⚠️ 이미지 경로를 찾을 수 없습니다: {link}")

st.components.v1.html(html_template, height=1400, scrolling=True)
    else:
        st.warning("🔍 검색 결과가 없습니다.")
else:
    st.info("제품코드 또는 제품명을 입력해주세요.")