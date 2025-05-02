import streamlit as st
import pandas as pd
import re

# 🔒 로그인 기능 추가
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

# CSV 파일 로드
try:
    df = pd.read_csv("product_data.csv", encoding="utf-8")
except Exception as e:
    st.error(f"❌ CSV 파일을 불러오는 중 오류 발생: {e}")
    st.stop()

# 숫자 포맷 함수
def clean_int(value):
    try:
        cleaned = re.sub(r"[^\d.]", "", str(value))
        if cleaned == "":
            return "-"
        return f"{int(float(cleaned)):,} KG"
    except (ValueError, TypeError):
        return "-"

# 사내/법적규격 파싱 함수
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

            spec_rows = ""
            for key in sorted(all_keys):
                if key == "성상":
                    legal = "-"
                    internal = row.get("성상", "-")
                else:
                    legal = legal_spec.get(key, "-")
                    internal = internal_spec.get(key, "-")

                spec_rows += "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(key, legal, internal)

            html_content = f'''
<style>
    table {
        table-layout: fixed;
{
        width: 100%;
        border-collapse: collapse;
    }}
    th, td {{
        border: 1px solid gray;
        padding: 8px;
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
        <tr><th>식품유형</th><th>제품구분</th><th>제품코드</th><th>소비기한</th></tr>
        <tr>
            <td>{row.get('식품유형', '-')}</td>
            <td>{row.get('구분', '-')}</td>
            <td>{row.get('제품코드', '-')}</td>
            <td>{row.get('소비기한', '-')}</td>
        </tr>
    </table>

    <h3>📊 생산량 (3개년)</h3>
    <table>
        <tr><th>2022</th><th>2023</th><th>2024</th></tr>
        <tr>
            <td>{prod_2022}</td>
            <td>{prod_2023}</td>
            <td>{prod_2024}</td>
        </tr>
    </table>

    <h3>2. 주요거래처</h3>
    <p>{row.get('주요거래처', '-')}</p>
    <h3>3. 제조방법</h3>
    <p>{row.get('제조방법', '-')}</p>
    <h3>4. 원재료명 및 함량</h3>
    <p>{row.get('원재료명 및 함량', '-')}</p>
    <h3>5. 원산지</h3>
    <p>{row.get('원산지', '-')}</p>
    <h3>6. 제품 특징</h3>
    <p>{row.get('제품특징', '-')}</p>

    <h3>7. 제품 규격</h3>
    <table>
        <tr><th>항목</th><th>법적규격</th><th>사내규격</th></tr>
        {spec_rows}
    </table>

    <h3>8. 기타사항</h3>
    <p>{row.get('기타사항', '-')}</p>
</div>

<br>
<button onclick="window.print()">🖨️ 이 제품백서 프린트하기</button>
'''

            st.components.v1.html(html_content, height=1100, scrolling=True)

            if "지대그림" in row and pd.notna(row["지대그림"]):
                st.image(row["지대그림"], width=300)
    else:
        st.warning("🔍 검색 결과가 없습니다.")
else:
    st.info("제품코드 또는 제품명을 입력해주세요.")