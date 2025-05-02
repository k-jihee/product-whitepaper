import streamlit as st
import pandas as pd
import re

# 🔒 로그인 기능 추가
PASSWORD = "samyang!11"  # 원하는 비밀번호로 설정

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

# CSV 파일 로드
try:
    df = pd.read_csv("product_data.csv", encoding="utf-8")
except Exception as e:
    st.error(f"❌ CSV 파일을 불러오는 중 오류 발생: {e}")
    st.stop()

# 안전한 숫자 변환 함수
def clean_int(value):
    try:
        cleaned = re.sub(r"[^\d.]", "", str(value))
        if cleaned == "":
            return "-"
        return f"{int(float(cleaned)):,} KG"
    except (ValueError, TypeError):
        return "-"


# 사내/법적규격 항목 파싱 함수
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

            st.markdown(f"<h2>{row['제품명']}</h2>", unsafe_allow_html=True)
            st.markdown(f"<b>용도:</b> {row.get('용도', '-')}", unsafe_allow_html=True)
            st.markdown("---")

            
            internal_spec = parse_spec_text(row.get("사내규격(COA)", ""))
            legal_spec = parse_spec_text(row.get("법적규격", ""))
            all_keys = set(internal_spec.keys()) | set(legal_spec.keys())
            spec_rows = ""
            for key in sorted(all_keys):
                spec_rows += f"""
                <tr>
                    <td>{key}</td>
                    <td>{legal_spec.get(key, "-")}</td>
                    <td>{internal_spec.get(key, "-")}</td>
                </tr>
                """

html_content = f"""
            <style>
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                th, td {{
                    border: 1px solid #ccc;
                    padding: 8px;
                }}
                th {{
                    text-align: center;
                }}
                td {{
                    text-align: center;
                }}
                @media print {{
                    button {{
                        display: none;
                    }}
                }}
            </style>

            <div id="print-area">
                <h2>{row['제품명']}</h2>
                <p><b>용도:</b> {row.get('용도', '-')}</p>

                <h3>1. 제품 정보</h3>
                <table>
                    <tr style="text-align:center;"><th>식품유형</th><th>제품구분</th><th>제품코드</th><th>소비기한</th></tr>
                    <tr style="text-align:center;">
                        <td>{row.get('식품유형', '-')}</td>
                        <td>{row.get('구분', '-')}</td>
                        <td>{row.get('제품코드', '-')}</td>
                        <td>{row.get('소비기한', '-')}</td>
                    </tr>
                </table>

                <h3>📊 생산량 (3개년)</h3>
                <table>
                    <tr style="text-align:center;"><th>2022</th><th>2023</th><th>2024</th></tr>
                    <tr style="text-align:center;">
                        <td>{prod_2022}</td>
                        <td>{prod_2023}</t
<h3>7. 제품 규격</h3>
<table>
    <tr style="text-align:center; font-weight:bold;"><th>항목</th><th>법적규격</th><th>사내규격</th></tr>
    <tr>
        <td>성상</td>
        <td>-</td>
        <td>{row.get('성상', '-')}</td>
    </tr>
    {spec_rows}
</table>
     2. 이소말토올리고당 함량(무수물%) : 50 이상<br>
                        3. pH(30%) : 4.5~7<br>
                        4. Ash(%) : 0.1 이하<br>
                        5. CV(30%) : 95 이상<br>
                        6. 납(ppm) : 1.0 이하
                    </td></tr>
                    <tr><td style="text-align:center;">법적규격</td><td style="text-align:left;">
                        1. 올리고당함량(%) : 이소말토올리고당 10 이상<br>
                        2. 납(mg/kg) : 1.0 이하
                    </td></tr>
                </table>

                <h3>8. 기타사항</h3>
                <p>{row.get('기타사항', '-')}</p>
            </div>

            <br>
            <button onclick="window.print()">🖨️ 이 제품백서 프린트하기</button>
            """

            st.components.v1.html(html_content, height=1000, scrolling=True)

            if "지대그림" in row and pd.notna(row["지대그림"]):
                st.image(row["지대그림"], width=300)
    else:
        st.warning("🔍 검색 결과가 없습니다.")
else:
    st.info("제품코드 또는 제품명을 입력해주세요.")
