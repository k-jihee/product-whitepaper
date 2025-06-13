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

def format_features(text):
    if pd.isna(text):
       return "-"
    items = re.split(r"\s*-\s*", text.strip())
    # 첫 항목이 빈 항목일 수 있어 제거
    items = [item for item in items if item]
    return "<br>".join(f"• {item.strip()}" for item in items)

st.title("🏭 인천 1공장 제품백서")
st.markdown("### 📋 인천 1공장 전제품 목록")
st.dataframe(df[["제품코드", "제품명"]].dropna().reset_index(drop=True))
st.markdown("---")



st.markdown("---")

st.markdown("### 🔍 비교할 제품코드 또는 제품명을 입력하세요 (최대 3개)")

col1, col2, col3 = st.columns(3)
with col1:
    input1 = st.text_input("제품 (1)", key="cmp1")
with col2:
    input2 = st.text_input("제품 (2)", key="cmp2")
with col3:
    input3 = st.text_input("제품 (3)", key="cmp3")

compare_inputs = [i.strip() for i in [input1, input2, input3] if i.strip()]
compare_rows = df[df["제품코드"].astype(str).isin(compare_inputs) | df["제품명"].astype(str).isin(compare_inputs)]

compare_inputs = [i for i in [input1, input2, input3] if i]
compare_rows = df[df["제품코드"].astype(str).isin(compare_inputs) | df["제품명"].astype(str).isin(compare_inputs)]

if not compare_rows.empty and len(compare_inputs) >= 2:
    compare_cols = st.columns(len(compare_rows))
    for col, (_, row) in zip(compare_cols, compare_rows.iterrows()):
        prod_2022 = clean_int(row.get('생산실적(2022)'))
        prod_2023 = clean_int(row.get('생산실적(2023)'))
        prod_2024 = clean_int(row.get('생산실적(2024)'))
        internal_spec = parse_spec_text(row.get("사내규격(COA)", ""))
        legal_spec = parse_spec_text(row.get("법적규격", ""))
        all_keys = set(internal_spec.keys()) | set(legal_spec.keys()) | {"성상"}
        with col:
            container_id = f"compare-{row.get('제품코드', 'unknown')}"
            html_content = f"""
<div id="{container_id}">
    <h3>{row.get('제품명', '-')}</h3>
    <p><b>용도:</b> {row.get('용도', '-')}</p>
    <p><b>식품유형:</b> {row.get('식품유형', '-')}</p>
    <p><b>제품코드:</b> {row.get('제품코드', '-')}</p>
    <p><b>구분:</b> {row.get('구분', '-')}</p>
    <p><b>소비기한:</b> {row.get('소비기한', '-')}</p>
    <p><b>주요거래처:</b> {row.get('주요거래처', '-')}</p>
    <p><b>제조방법:</b> {row.get('제조방법', '-')}</p>
    <p><b>원재료 및 원산지:</b> {row.get('원재료명 및 함량', '-')} / {row.get('원산지', '-')}</p>
    <p><b>제품특징:</b><br>{format_features(row.get('제품특징', '-'))}</p>
    <p><b>2022:</b> {prod_2022} / <b>2023:</b> {prod_2023} / <b>2024:</b> {prod_2024}</p>
    <h4>제품 규격</h4>
    <ul>
    <li><b>성상:</b> {row.get('성상', '-')}</li>
"""
            for key in sorted(all_keys):
                if key != "성상":
                    html_content += f"<li>{key}: 법적({legal_spec.get(key, '-')}) / 사내({internal_spec.get(key, '-')})</li>"
            html_content += f"""
    </ul>
    <p><b>기타사항:</b> {row.get('기타사항', '-')}</p>
</div>

<button onclick="printSection('{container_id}')">🖨️ 이 제품 PDF로 저장</button>
"""

            html_content += """
<script>
function printSection(id) {
    var content = document.getElementById(id).innerHTML;
    var win = window.open('', '', 'height=700,width=700');
    win.document.write('<html><head><title>Print</title></head><body>');
    win.document.write(content);
    win.document.write('</body></html>');
    win.document.close();
    win.print();
}
</script>
"""
            st.components.v1.html(html_content, height=1200, scrolling=True)
else:
    if len(compare_inputs) >= 2:
        st.warning("❌ 입력한 제품 중 일부를 찾을 수 없습니다.")




st.markdown("---")
st.markdown("### 🆚 제품 비교 (표 형식, PDF 출력 가능)")

col1, col2, col3 = st.columns(3)
st.markdown("### 🔍 비교할 제품코드 또는 제품명을 입력하세요 (최대 3개)")

col1, col2, col3 = st.columns(3)
with col1:
    input1 = st.text_input("제품 (1)", key="cmp1")
with col2:
    input2 = st.text_input("제품 (2)", key="cmp2")
with col3:
    input3 = st.text_input("제품 (3)", key="cmp3")

compare_inputs = [i.strip() for i in [input1, input2, input3] if i.strip()]
compare_rows = df[df["제품코드"].astype(str).isin(compare_inputs) | df["제품명"].astype(str).isin(compare_inputs)]

compare_inputs = [i for i in [input1, input2, input3] if i]
compare_rows = df[df["제품코드"].astype(str).isin(compare_inputs) | df["제품명"].astype(str).isin(compare_inputs)]

if not compare_rows.empty and len(compare_inputs) >= 2:
    html_table = "<table border='1' style='border-collapse:collapse; width:100%; text-align:center;'>"
    html_table += "<thead><tr><th>항목</th>"
    for _, row in compare_rows.iterrows():
        html_table += f"<th>{row.get('제품명', '-')}</th>"
    html_table += "</tr></thead><tbody>"

    def row_html(label, key):
        html = f"<tr><td><b>{label}</b></td>"
        for _, row in compare_rows.iterrows():
            val = row.get(key, '-')
            html += f"<td>{val}</td>"
        html += "</tr>"
        return html

    # 기본 항목
    html_table += row_html("제품코드", "제품코드")
    html_table += row_html("용도", "용도")
    html_table += row_html("식품유형", "식품유형")
    html_table += row_html("제품구분", "구분")
    html_table += row_html("소비기한", "소비기한")
    html_table += row_html("주요거래처", "주요거래처")
    html_table += row_html("제조방법", "제조방법")
    html_table += row_html("원재료명 및 함량", "원재료명 및 함량")
    html_table += row_html("원산지", "원산지")
    html_table += row_html("제품특징", "제품특징")
    html_table += row_html("생산실적(2022)", "생산실적(2022)")
    html_table += row_html("생산실적(2023)", "생산실적(2023)")
    html_table += row_html("생산실적(2024)", "생산실적(2024)")
    html_table += row_html("기타사항", "기타사항")

    # 규격 항목 통합
    spec_keys = set()
    for _, row in compare_rows.iterrows():
        spec_keys.update(parse_spec_text(row.get("법적규격", "")).keys())
        spec_keys.update(parse_spec_text(row.get("사내규격(COA)", "")).keys())
    spec_keys.add("성상")

    for key in sorted(spec_keys):
        html_table += f"<tr><td><b>{key} (법적)</b></td>"
        for _, row in compare_rows.iterrows():
            val = parse_spec_text(row.get("법적규격", "")).get(key, "-") if key != "성상" else row.get("성상", "-")
            html_table += f"<td>{val}</td>"
        html_table += "</tr>"
        html_table += f"<tr><td><b>{key} (사내)</b></td>"
        for _, row in compare_rows.iterrows():
            val = parse_spec_text(row.get("사내규격(COA)", "")).get(key, "-") if key != "성상" else "-"
            html_table += f"<td>{val}</td>"
        html_table += "</tr>"

    html_table += "</tbody></table>"
    html_table += "<br><button onclick="window.print()">🖨️ 비교결과 PDF로 저장</button>"

    st.components.v1.html(html_table, height=1600, scrolling=True)
else:
    if len(compare_inputs) >= 2:
        st.warning("❌ 입력한 제품 중 일부를 찾을 수 없습니다.")
