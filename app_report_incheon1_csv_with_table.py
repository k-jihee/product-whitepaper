
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

def format_features(text):
    if pd.isna(text):
        return "-"
    items = re.split(r"\s*-\s*", text.strip())
    items = [item for item in items if item]
    return "<br>".join(f"• {item.strip()}" for item in items)

st.title("🏭 인천 1공장 제품백서")
st.markdown("### 📋 인천 1공장 전제품 목록")
st.dataframe(df[["제품코드", "제품명"]].dropna().reset_index(drop=True), use_container_width=False)
st.markdown("---")
st.markdown('<h4>🔍 <b>제품코드 또는 제품명을 입력하세요</b></h4>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    query1 = st.text_input("🔎 제품 1 (예: GIB1010 또는 글루텐피드)", key="query_input1", use_container_width=False)
with col2:
    query2 = st.text_input("🔎 제품 2 (선택)", key="query_input2", use_container_width=False)

queries = [q for q in [query1, query2] if q]

if queries:
    results = pd.DataFrame()
    for q in queries:
        partial = df[df["제품코드"].astype(str).str.contains(q, case=False, na=False) |
                     df["제품명"].astype(str).str.contains(q, case=False, na=False)]
        results = pd.concat([results, partial])

    if not results.empty:
        cols = st.columns(len(results))
        for col, (_, row) in zip(cols, results.iterrows()):
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
                spec_rows += f"<tr><td>{key}</td><td>{legal}</td><td>{internal}</td></tr>"

            img_links = str(row.get("한도견본", "")).strip()
            if img_links in ["", "한도견본 없음"]:
                sample_html = "해당사항 없음"
                print_button = ""
            else:
                imgs = "".join(f'<img src="{link.strip()}" width="500" onclick="showModal(this.src)" style="cursor:pointer; margin:10px;">' for link in img_links.split(",") if link.strip())
                sample_html = imgs
                print_button = '<button onclick="printSample()">🖨️ 한도견본만 PDF로 저장</button>'

            html_template = f"""<style>
            table {{ table-layout: fixed; width: 100%; border-collapse: collapse; }}
            th, td {{ border: 1px solid gray; padding: 8px; text-align: center; }}
            th {{ background-color: #f2f2f2; }}
            @media print {{ button {{ display: none; }} }}
            </style>

            <div id='print-area'>
            <h2>{row.get('제품명', '-')}</h2>
            <p><b>용도:</b> {row.get('용도', '-')}</p>
            <h3>1. 제품 정보</h3>
            <table>
            <tr><th>식품유형</th><th>제품구분</th><th>제품코드</th><th>소비기한</th></tr>
            <tr><td>{row.get('식품유형', '-')}</td><td>{row.get('구분', '-')}</td><td>{row.get('제품코드', '-')}</td><td>{row.get('소비기한', '-')}</td></tr>
            </table>
            <h3>📊 생산량 (3개년)</h3>
            <table><tr><th>2022</th><th>2023</th><th>2024</th></tr><tr><td>{prod_2022}</td><td>{prod_2023}</td><td>{prod_2024}</td></tr></table>
            <h3>2. 주요거래처</h3><p>{row.get('주요거래처', '-')}</p>
            <h3>3. 제조방법</h3><p>{row.get('제조방법', '-')}</p>
            <h3>4. 원재료명 및 함량 / 원산지</h3><p>{row.get('원재료명 및 함량', '-')} / {row.get('원산지', '-')}</p>
            <h3>5. 제품 특징</h3><p>{format_features(row.get('제품특징', '-'))}</p>
            <h3>6. 제품 규격</h3>
            <table><tr><th>항목</th><th>법적규격</th><th>사내규격</th></tr>{성상_row}{spec_rows}</table>
            <h3>7. 기타사항</h3><p>{row.get('기타사항', '-')}</p></div>

            <div id='sample-area'><h3>8. 한도견본</h3>{sample_html}{print_button}</div>
            <div id="modal" onclick="this.style.display='none'"><img id="modal-img" style="max-width:90%; max-height:90%; object-fit:contain;"></div>
            <script>
            function printSample() {{
                const original = document.body.innerHTML;
                const printSection = document.getElementById("sample-area").innerHTML;
                document.body.innerHTML = printSection;
                window.print();
                document.body.innerHTML = original;
            }}
            function showModal(src) {{
                document.getElementById("modal-img").src = src;
                document.getElementById("modal").style.display = "flex";
            }}
            </script>
            <br><button onclick="window.print()">🖨️ 이 제품백서 프린트하기</button>"""

            with col:
                st.components.v1.html(html_template, height=2200, scrolling=True)
    else:
        st.warning("🔍 검색 결과가 없습니다.")
else:
    st.info("제품코드 또는 제품명을 입력해주세요.")
