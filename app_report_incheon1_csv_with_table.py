
import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os

# CSV 파일 로드 (보안 우회를 위한 방식)
try:
    df = pd.read_csv("product_data.csv", encoding="utf-8")
except Exception as e:
    st.error(f"❌ CSV 파일을 불러오는 중 오류 발생: {e}")
    st.stop()

# 페이지 제목
st.title("🏭 인천 1공장 제품백서")

# 제품코드 + 제품명 목록 출력
st.markdown("### 📋 인천 1공장 전제품 목록")
st.dataframe(df[["제품코드", "제품명"]].dropna().reset_index(drop=True))
st.markdown("---")

# 검색창
query = st.text_input("🔍 제품코드 또는 제품명을 입력하세요")

# 결과 필터링
if query:
    results = df[df["제품코드"].astype(str).str.contains(query, case=False, na=False) | 
                 df["제품명"].astype(str).str.contains(query, case=False, na=False)]
    
    if not results.empty:
        for _, row in results.iterrows():
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
            st.markdown("---")

            st.markdown("### 4. 원재료명 및 함량")
            st.markdown(f"{row.get('원재료명 및 함량', '-')}")
            st.markdown("### 5. 원산지")
            st.markdown(f"{row.get('원산지', '-')}")
            st.markdown("---")

            st.markdown("### 6. 제품 특징")
            st.markdown(f"{row.get('제품특징', '-')}")
            st.markdown("---")

            st.markdown("### 7. 제품 규격")
            st.markdown("#### 성상")
            st.markdown(f"{row.get('성상', '-')}")
            st.markdown("#### 사내규격(COA)")
            st.markdown(f"{row.get('사내규격(COA)', '-')}")
            st.markdown("#### 법적규격")
            st.markdown(f"{row.get('법적규격', '-')}")
            st.markdown("---")

            st.markdown("### 8. 기타사항")
            st.markdown(f"{row.get('기타사항', '-')}")

            if "지대그림" in row and pd.notna(row["지대그림"]):
                st.image(row["지대그림"], width=300)

            # PDF 저장 기능 추가
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

            if st.button(f"📄 '{row['제품명']}' PDF로 저장"):
                pdf_path = generate_pdf(row)
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📥 PDF 다운로드",
                        data=f,
                        file_name=f"{row['제품명']}_제품백서.pdf",
                        mime="application/pdf"
                    )
                os.remove(pdf_path)
    else:
        st.warning("🔍 검색 결과가 없습니다.")
else:
    st.info("제품코드 또는 제품명을 입력해주세요.")
