
import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os

# CSV 파일 로드
try:
    df = pd.read_csv("product_data.csv", encoding="utf-8")
except Exception as e:
    st.error(f"❌ CSV 파일을 불러오는 중 오류 발생: {e}")
    st.stop()

st.title("🏭 인천 1공장 제품백서")

# 쿼리 파라미터에서 선택된 제품코드 확인
query_params = st.experimental_get_query_params()
selected_code = query_params.get("code", [None])[0]

# 전제품 목록 테이블 (클릭 가능한 HTML 링크 포함)
st.markdown("### 📋 인천 1공장 전제품 목록")

def make_clickable(code, name):
    return f'<a href="/?code={code}" target="_self">{code}</a>', f'<a href="/?code={code}" target="_self">{name}</a>'

df_display = df[["제품코드", "제품명"]].dropna().copy()
df_display[["제품코드", "제품명"]] = df_display.apply(
    lambda row: make_clickable(row["제품코드"], row["제품명"]), axis=1, result_type="expand"
)
st.write(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

# 검색창 및 필터 기능 유지
st.markdown("---")
query = st.text_input("🔍 제품코드 또는 제품명을 입력하세요")

if query:
    results = df[df["제품코드"].astype(str).str.contains(query, case=False, na=False) |
                 df["제품명"].astype(str).str.contains(query, case=False, na=False)]
    if not results.empty:
        st.dataframe(results[["제품코드", "제품명"]])
    else:
        st.warning("🔍 검색 결과가 없습니다.")
else:
    st.info("제품코드 또는 제품명을 입력해주세요.")

# 제품 백서 출력
if selected_code:
    row = df[df["제품코드"] == selected_code].iloc[0]

    st.markdown(f"# {row['제품명']}")
    st.markdown(f"**용도:** {row.get('용도', '-')}")
    st.markdown("---")

    st.markdown("### 1. 제품 정보")
    info_table = pd.DataFrame({
        "항목": ["식품유형", "제품구분", "제품코드", "소비기한"],
        "내용": [row.get("식품유형", "-"), row.get("구분", "-"), row.get("제품코드", "-"), row.get("소비기한", "-")]
    })
    st.table(info_table)

    st.markdown("### 📊 생산량 (3개년)")
    prod_table = pd.DataFrame({
        "연도": ["2022", "2023", "2024"],
        "생산량": [
            f"{int(row.get('생산실적(2022)', 0)):,} KG" if pd.notna(row.get("생산실적(2022)")) else "-",
            f"{int(row.get('생산실적(2023)', 0)):,} KG" if pd.notna(row.get("생산실적(2023)")) else "-",
            f"{int(row.get('생산실적(2024)', 0)):,} KG" if pd.notna(row.get("생산실적(2024)")) else "-"
        ]
    })
    st.table(prod_table)

    st.markdown("### 2. 주요거래처")
    st.markdown(f"{row.get('주요거래처', '-')}")
    st.markdown("### 3. 제조방법")
    st.markdown(f"{row.get('제조방법', '-')}")
    st.markdown("### 4. 원재료명 및 함량")
    st.markdown(f"{row.get('원재료명 및 함량', '-')}")
    st.markdown("### 5. 원산지")
    st.markdown(f"{row.get('원산지', '-')}")
    st.markdown("### 6. 제품 특징")
    st.markdown(f"{row.get('제품특징', '-')}")
    st.markdown("### 7. 제품 규격")
    st.markdown("#### 성상")
    st.markdown(f"{row.get('성상', '-')}")
    st.markdown("#### 사내규격(COA)")
    st.markdown(f"{row.get('사내규격(COA)', '-')}")
    st.markdown("#### 법적규격")
    st.markdown(f"{row.get('법적규격', '-')}")
    st.markdown("### 8. 기타사항")
    st.markdown(f"{row.get('기타사항', '-')}")

    # 이미지 출력
    if "지대그림" in row and pd.notna(row["지대그림"]):
        st.image(row["지대그림"], width=300)

    # PDF 저장 기능
    def generate_pdf(data):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, txt=f"제품 백서 - {data['제품명']}", ln=True, align="C")
        pdf.ln(10)
        for key in ["용도", "식품유형", "구분", "제품코드", "소비기한",
                    "생산실적(2022)", "생산실적(2023)", "생산실적(2024)",
                    "주요거래처", "제조방법", "원재료명 및 함량", "원산지",
                    "제품특징", "성상", "사내규격(COA)", "법적규격", "기타사항"]:
            val = str(data.get(key, "-"))
            pdf.multi_cell(0, 10, f"{key}: {val}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
            pdf.output(tmpfile.name)
            return tmpfile.name

    if st.button("📄 PDF로 저장"):
        pdf_path = generate_pdf(row)
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📥 PDF 다운로드",
                data=f,
                file_name=f"{row['제품명']}_제품백서.pdf",
                mime="application/pdf"
            )
        os.remove(pdf_path)
