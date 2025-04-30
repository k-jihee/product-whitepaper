
import streamlit as st
import pandas as pd

# CSV 파일 로드
try:
    df = pd.read_csv("product_data.csv", encoding="utf-8")
except Exception as e:
    st.error(f"❌ CSV 파일을 불러오는 중 오류 발생: {e}")
    st.stop()

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
            prod_2022 = f"{int(row['생산실적(2022)']):,} KG" if pd.notna(row.get('생산실적(2022)')) else "-"
            prod_2023 = f"{int(row['생산실적(2023)']):,} KG" if pd.notna(row.get('생산실적(2023)')) else "-"
            prod_2024 = f"{int(row['생산실적(2024)']):,} KG" if pd.notna(row.get('생산실적(2024)')) else "-"

            st.markdown(f"<h2>{row['제품명']}</h2>", unsafe_allow_html=True)
            st.markdown(f"<b>용도:</b> {row.get('용도', '-')}", unsafe_allow_html=True)
            st.markdown("---")

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
                    <tr style="text-align:center; font-weight:bold;"><th>항목</th><th>내용</th></tr>
                    <tr><td style="text-align:center;">성상</td><td style="text-align:left;">무색 투명한 액체로 이취, 이물이 없어야 한다.</td></tr>
                    <tr><td style="text-align:center;">사내규격</td><td style="text-align:left;">
                        1. 수분(%) : 25 이하<br>
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
