import streamlit as st
import pandas as pd
import re
import os
import requests 

st.set_page_config(layout="wide")

# 보안을 위해 비밀번호는 Streamlit Secrets에 저장하는 것을 강력히 권장합니다.
# 데모를 위해 여기에 직접 입력합니다.
PASSWORD = "samyang!11" 

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("(자물쇠) 로그인 필요")
    password = st.text_input("비밀번호를 입력하세요", type="password")
    if password == PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    elif password:
        st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop()

# --- Agentspace API를 호출하여 제품 상세 데이터를 가져오는 함수 ---
@st.cache_data(ttl=3600) # 1시간 동안 API 응답을 캐싱하여 반복 호출 방지 (데모용)
def fetch_product_details_from_agentspace(query_text):
    """
    Agentspace API를 호출하여 제품 상세 데이터를 가져옵니다.
    query_text는 제품코드 또는 제품명이 될 수 있습니다.
    """
    # ====================================================================
    # TODO: 중요! 이 부분을 Agentspace에서 발급받은 실제 정보로 변경해주세요!
    # ====================================================================
    # 1. AGENTSPACE_API_URL: Agentspace 에이전트의 API 엔드포인트 URL
    #    예시: "https://your-agentspace-instance.com/api/v1/agents/product-detail-agent"
    AGENTSPACE_API_URL = "https://your-agentspace-instance.com/api/v1/agents/product-detail-agent"
    
    # 2. API_KEY: Agentspace에서 발급받은 API 키 (보안 토큰)
    #    실제 서비스에서는 이 키를 코드에 직접 넣지 않고,
    #    Streamlit Secrets나 환경 변수를 사용하는 것이 좋습니다.
    API_KEY = "YOUR_AGENTSPACE_API_KEY_HERE" 
    # ====================================================================
    
    headers = {
        "Authorization": f"Bearer {API_KEY}", # 인증 방식에 따라 'Bearer' 대신 'x-api-key' 등 사용
        "Content-Type": "application/json"
    }
    # Agentspace 에이전트가 어떤 형식으로 입력을 받는지에 따라 payload를 조정해야 합니다.
    # 여기서는 'product_query'라는 이름으로 검색 텍스트를 보낸다고 가정합니다.
    payload = {"product_query": query_text} 

    try:
        response = requests.post(AGENTSPACE_API_URL, json=payload, headers=headers, timeout=10) # 10초 타임아웃 설정
        response.raise_for_status() # HTTP 오류가 발생하면 예외를 발생시킴 (4xx, 5xx)
        
        agentspace_data_list = response.json() # Agentspace는 여러 제품을 반환할 수도 있으므로 리스트로 가정
        
        if not agentspace_data_list: # Agentspace가 빈 응답을 보낼 경우
            return pd.DataFrame()

        # Agentspace에서 받은 JSON 데이터를 기존 Streamlit 앱이 기대하는 DataFrame 형식으로 변환합니다.
        # Agentspace 에이전트가 반환하는 JSON의 키들이 기존 CSV 컬럼명과 최대한 일치한다고 가정합니다.
        # 예시: agentspace_data_list = [{'제품코드': 'GIS7030', '제품명': '물엿', '생산실적(2024)': '1500000', ...}, ...]
        
        processed_data = []
        for item in agentspace_data_list:
            # '용도' 컬럼을 기존 코드와 동일하게 처리
            if '용도' in item:
                item['용도'] = str(item['용도']).replace(r"\s*-\s*", " / ", regex=True)
                
            # '제품코드'를 기반으로 계층구조 추가 (기존 로직 재활용)
            if '제품코드' in item:
                hierarchy_2, hierarchy_3 = get_hierarchy(item['제품코드'])
                item['계층구분_2레벨'] = hierarchy_2 
                item['계층구분_3레벨'] = hierarchy_3 
            processed_data.append(item)

        return pd.DataFrame(processed_data) # 여러 제품 데이터를 DataFrame으로 반환
        
    except requests.exceptions.Timeout:
        st.error(f"Agentspace API 호출 시간 초과 (10초): {query_text}")
        return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        st.error(f"Agentspace API 호출 오류 ({query_text}): {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생 ({query_text}): {e}")
        return pd.DataFrame()

# 기존 CSV 파일 로드 부분은 Agentspace 연동 데모에서는 사용하지 않습니다.

def clean_int(value):
    try:
        cleaned = re.sub(r"[^\d.]", "", str(value))
        if cleaned == "":
            return "-"
        return "{:,} KG".format(int(float(cleaned))) 
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
    return "<br>".join(["• {}".format(item.strip()) for item in items]) 

# 제품 계층구조 (이 함수는 Agentspace API 응답 처리 시에도 사용됩니다)
def get_hierarchy(code):
    if pd.isna(code):
        return "기타", "기타"
    code = str(code)   # 문자열로 변환
    
    if code.startswith("GIB"):
        return "FG0009 : 부산물", "부산물"
    elif code.startswith("GID1") or code.startswith("GID2") or code.startswith("GID3"):
        return "FG0001 : 포도당", "포도당분말"
    elif code.startswith("GID6") or code.startswith("GID7"):
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
    elif code.startswith("GIS93"):
        return "FG0002 : 물엿", "하이말토스"    
    elif code.startswith("GIF501") or code.startswith("GIF502"):
        return "FG0003 : 과당", "55%과당"
    elif code.startswith("GIC002"):
        return "FG0004 : 전분", "일반전분"
    elif code.startswith("GIC") or code.startswith("GIT"):
        return "FG0004 : 전분", "변성전분"            
    elif code.startswith("GISQ190"):
        return "FG0006 : 알룰로스", "알룰로스 액상"
    elif code.startswith("GIN121") or code.startswith("GIN1221"):
        return "FG0007 : 올리고당", "이소말토올리고 액상"
    elif code.startswith("GIN1230") or code.startswith("GIN1220"):
        return "FG0007 : 올리고당", "이소말토올리고 분말"
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

st.title("🏭 인천 1공장 제품백서 (Agentspace 연동 DEMO)")

# 초기 전제품 목록 제거 또는 Agentspace API를 통한 간략한 목록 로드
with st.container():
    st.markdown("### 📋 제품 검색 가이드")
    st.markdown(
        """
        <p>아래 검색창에 제품 코드 또는 제품명을 입력하여 Agentspace에서 실시간 데이터를 가져옵니다.</p>
        <p>초기 전체 제품 목록은 Agentspace API를 통해 가져올 수 있으나, 현재 데모에서는 검색에 집중합니다.</p>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")
st.markdown('<h4>🔍 <b>제품코드 또는 제품명을 입력하세요</b></h4>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    query1 = st.text_input("검색 제품 1 (예: GIB1010 또는 글루텐피드)") 
with col2:
    query2 = st.text_input("검색 제품 2 (예: GIS7030 또는 물엿)", key="query_input2") 

queries = [q for q in [query1, query2] if q]

if queries:
    results = pd.DataFrame() # Agentspace에서 가져온 데이터를 저장할 DataFrame
    unique_queries = list(set(queries)) # 중복 쿼리 제거
    
    for q_text in unique_queries:
        # Agentspace API를 호출하여 제품 상세 정보를 가져옵니다.
        product_data_from_agentspace = fetch_product_details_from_agentspace(q_text)
        if not product_data_from_agentspace.empty:
            results = pd.concat([results, product_data_from_agentspace], ignore_index=True)
            
    if not results.empty:
        cols = st.columns(len(results))
        # CSS 스타일을 별도로 정의합니다.
        common_style = """
            table {table-layout: fixed; width: 100%; border-collapse: collapse;}
            th, td {border: 1px solid gray; padding: 8px; text-align: center;}
            th {background-color: #f2f2f2;}
            @media print {button {display: none;}}
        """

        for col, (_, row) in zip(cols, results.iterrows()):
            # 기존 CSV 데이터와 동일한 컬럼명을 사용한다고 가정
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

            img_links = str(row.get("한도견본", "")).strip()
            if img_links in ["", "한도견본 없음"]:
                sample_html_content = "해당사항 없음"
                print_button = ""
            else:
                # Agentspace에서 이미지 URL을 제공해야 합니다.
                imgs = "".join(['<img src="{}" width="500" onclick="showModal(this.src)" style="cursor:pointer; margin:10px;">'.format(link.strip()) for link in img_links.split(",") if link.strip()])
                sample_html_content = """
                <div style="text-align:left;">
                    {imgs_content}
                    <div style="margin-top: 10px;">
                        <button onclick="printSample()">한도견본만 PDF로 저장</button>
                    </div>
                </div>
                """.format(imgs_content=imgs)
                print_button = ""  # 따로 빼지 않음

            html_template = """<style>{common_style}</style>

            <div id='print-area'>
            <h2>{product_name}</h2>
            <p><b>용도:</b> {usage}</p>
            <h3>1. 제품 정보</h3>
            <table>
            <tr><th>식품유형</th><th>제품구분</th><th>제품코드</th><th>소비기한</th></tr>
            <tr><td>{food_type}</td><td>{category}</td><td>{product_code}</td><td>{expiration_date}</td></tr>
            </table>
            <h3>📊 생산량 (3개년)</h3>
            <table><tr><th>2022</th><th>2023</th><th>2024</th></tr><tr><td>{prod_2022}</td><td>{prod_2023}</td><td>{prod_2024}</td></tr></table>
            <h3>2. 주요거래처</h3><p>{main_clients}</p>
            <h3>3. 제조방법</h3><p>{manufacturing_method}</p>
            <h3>4. 원재료명 및 함량 / 원산지</h3><p>{ingredients_content} / {origin}</p>
            <h3>5. 제품 특징</h3><p>{product_features}</p>
            <h3>6. 제품 규격</h3>
            <table><tr><th>항목</th><th>법적규격</th><th>사내규격</th></tr>{spec_row_status}{spec_rows_content}</table>
            <h3>7. 기타사항</h3><p>{other_notes}</p></div>

            <div id='sample-area'><h3>8. 한도견본</h3>{sample_html_content_final}{print_button}</div>
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
            <br><button onclick="window.print()">이 제품백서 프린트하기</button>""".format(
                common_style=common_style,
                product_name=row.get('제품명', '-'),
                usage=row.get('용도', '-'),
                food_type=row.get('식품유형', '-'),
                category=row.get('구분', '-'),
                product_code=row.get('제품코드', '-'),
                expiration_date=row.get('소비기한', '-'),
                prod_2022=prod_2022,
                prod_2023=prod_2023,
                prod_2024=prod_2024,
                main_clients=row.get('주요거래처', '-'),
                manufacturing_method=row.get('제조방법', '-'),
                ingredients_content=row.get('원재료명 및 함량', '-'),
                origin=row.get('원산지', '-'),
                product_features=format_features(row.get('제품특징', '-')),
                spec_row_status=성상_row,
                spec_rows_content=spec_rows,
                other_notes=row.get('기타사항', '-'),
                sample_html_content_final=sample_html_content, 
                print_button=print_button
            )


            with col:
                st.components.v1.html(html_template, height=2200, scrolling=True)
    else:
        st.warning("검색 결과가 없습니다. 제품 코드 또는 제품명을 확인해주세요.") 
else:
    st.info("제품코드 또는 제품명을 입력해주세요.")
