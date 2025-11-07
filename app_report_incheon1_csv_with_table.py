
import streamlit as st
import pandas as pd
import re
import os

# ============================
# 기본 설정 & 전역
# ============================
st.set_page_config(page_title="인천1공장 AI Agent (Core)", layout="wide")
APP_TITLE = "🏭 인천1공장 AI 에이전트"
PROJECT_TITLE = "프로덕트 가디언즈 : 인천1공장의 제품과 노하우를 지켜내는 사람들"
PROJECT_MOTTO = "근무자의 머릿속에만 있던 현장 지식을 AI 속에 담아 누구나 쉽고 빠르게 배우고 연결되게 하자!"

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ============================
# 인증
# ============================
PASSWORD = os.environ.get("INCHON1_PORTAL_PASSWORD", "samyang!11")
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "route" not in st.session_state:
    st.session_state.route = "HOME"  # HOME, CHAT, PRODUCT, INSIGHT

def logout():
    st.session_state.clear()
    st.rerun()

if not st.session_state.authenticated:
    st.title("🔒 로그인 필요")
    pw = st.text_input("비밀번호를 입력하세요", type="password")
    if pw == PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    elif pw:
        st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop()

# ============================
# 유틸
# ============================
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

# ============================
# 데이터 로딩
# ============================
@st.cache_data(show_spinner=False)
def load_product_df():
    try:
        df = pd.read_csv("product_data.csv", encoding="utf-8")
        if "용도" in df.columns:
            df["용도"] = df["용도"].astype(str).str.replace(r"\s*-\s*", " / ", regex=True)
        # 계층 자동 생성
        if "계층구조_2레벨" not in df.columns or "계층구조_3레벨" not in df.columns:
            def get_hierarchy(code):
                if pd.isna(code):
                    return "기타", "기타"
                code = str(code)
                if code.startswith("GIB"):
                    return "FG0009 : 부산물", "부산물"
                elif code.startswith(("GID1","GID2","GID3")):
                    return "FG0001 : 포도당", "포도당분말"
                elif code.startswith(("GID6","GID7")):
                    return "FG0001 : 포도당", "포도당액상"
                elif code.startswith("GIS62"):
                    return "FG0002 : 물엿", "고감미75"
                elif code.startswith(("GIS601","GIS631")):
                    return "FG0002 : 물엿", "고감미82"
                elif code.startswith(("GIS701","GIS703")):
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
                elif code.startswith(("GIF501","GIF502")):
                    return "FG0003 : 과당", "55%과당"
                elif code.startswith("GIC002"):
                    return "FG0004 : 전분", "일반전분"
                elif str(code).startswith(("GIC","GIT")):
                    return "FG0004 : 전분", "변성전분"
                elif code.startswith("GISQ190"):
                    return "FG0006 : 알룰로스", "알룰로스 액상"
                elif code.startswith(("GIN121","GIN1221")):
                    return "FG0007 : 올리고당", "이소말토올리고 액상"
                elif code.startswith(("GIN1230","GIN1220")):
                    return "FG0007 : 올리고당", "이소말토올리고 분말"
                elif code.startswith("GIN131"):
                    return "FG0007 : 올리고당", "갈락토"
                elif code.startswith("GIN151"):
                    return "FG0007 : 올리고당", "말토올리고"
                elif code.startswith(("GIP202","GIP204")):
                    return "FG0008 : 식이섬유", "폴리덱스트로스"
                elif code.startswith(("GIS242","GIS240")):
                    return "FG0008 : 식이섬유", "NMD 액상/분말"
                else:
                    return "기타", "기타"
            df[["계층구조_2레벨", "계층구조_3레벨"]] = df["제품코드"].apply(lambda x: pd.Series(get_hierarchy(x)))
        return df
    except Exception as e:
        st.error(f"❌ product_data.csv 불러오기 오류: {e}")
        return pd.DataFrame()

# ============================
# 페이지
# ============================
def page_home():
    st.title(APP_TITLE)
    st.markdown(f"**{PROJECT_TITLE}**")
    st.caption(PROJECT_MOTTO)
    st.markdown("---")

    st.subheader("스마트 지식 허브")
    st.caption("공정지식 · 제품백서 · 인사이트를 한 곳에서!")
    q = st.text_input("🔎 툴 검색 (예: '제품', '공정', '인사이트')", key="home_search").strip().lower()

    cards = [
        {"key":"CHAT", "title":"GPT / 공정지식", "desc":"공정·제품·규정 등 실무 질의 응답", "tag":"챗봇"},
        {"key":"PRODUCT", "title":"제품백서", "desc":"제품 정보/규격/한도견본 확인 및 PDF 출력", "tag":"문서"},
        {"key":"INSIGHT", "title":"SAMI Insight(준비 중)", "desc":"품질/VOC/생산 데이터 인사이트(데모)", "tag":"인사이트"},
    ]
    if q:
        cards = [c for c in cards if (q in c["title"].lower() or q in c["desc"].lower() or q in c["tag"].lower())]

    cols = st.columns(3)
    for i, c in enumerate(cards):
        with cols[i % 3]:
            with st.container(border=True):
                st.subheader(c["title"])
                st.write(c["desc"])
                st.caption(f"#{c['tag']}")
                if st.button("열기", key=f"open_{c['key']}"):
                    st.session_state.route = c["key"]
                    st.rerun()

def page_chatbot():
    st.title("💬 공정지식 챗봇 (베타)")
    st.info("사내망 AI 연동 전까지는 제품 데이터 기반의 간단한 검색/조회만 제공합니다.")
    df = load_product_df()
    query = st.text_input("무엇을 도와드릴까요? (예: 정제포도당 CCP, 제네덱스 mesh, 식품유형 등)")
    if query:
        mask = pd.Series(False, index=df.index)
        for col in [c for c in df.columns if df[c].dtype == object]:
            mask |= df[col].astype(str).str.contains(query, case=False, na=False)
        hits = df.loc[mask, ["제품코드","제품명","제품특징","사내규격(COA)"]].head(30)
        st.dataframe(hits if not hits.empty else pd.DataFrame(), use_container_width=True)
        if hits.empty:
            st.warning("검색 결과가 없습니다.")

def product_card(row):
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
    else:
        imgs = "".join(
            f'<img src="{link.strip()}" width="500" onclick="showModal(this.src)" style="cursor:pointer; margin:10px;">'
            for link in img_links.split(",") if link.strip()
        )
        sample_html = f"""
        <div style="text-align:left;">
            {imgs}
            <div style="margin-top: 10px;">
                <button onclick="printSample()">🖨️ 한도견본만 PDF로 저장</button>
            </div>
        </div>
        """
    html_template = f"""<style>
    table {{ table-layout: fixed; width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid gray; padding: 8px; text-align: center; }}
    th {{ background-color: #f2f2f2; }}
    @media print {{ button {{ display: none; }} }}
    #modal {{ display:none; position:fixed; left:0; top:0; width:100vw; height:100vh; background:rgba(0,0,0,0.7); align-items:center; justify-content:center; }}
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
    <div id='sample-area'><h3>8. 한도견본</h3>{sample_html}</div>
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
    st.components.v1.html(html_template, height=2200, scrolling=True)

def page_product():
    st.title("📘 제품백서")
    df = load_product_df()
    with st.expander("📋 인천 1공장 전제품 목록", expanded=False):
        st.dataframe(df[["계층구조_2레벨","계층구조_3레벨","제품코드","제품명"]].dropna().reset_index(drop=True), use_container_width=True)
    st.markdown("---")
    st.markdown('<h4>🔍 <b>제품코드 또는 제품명을 입력하세요</b></h4>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        q1 = st.text_input("🔎 제품 1 (예: GIB1010 또는 글루텐피드)")
    with col2:
        q2 = st.text_input("🔎 제품 2 (예: GIS7030 또는 물엿)")
    queries = [q for q in [q1, q2] if q]
    if queries:
        results = pd.DataFrame()
        for q in queries:
            partial = df[
                df["제품코드"].astype(str).str.contains(q, case=False, na=False) |
                df["제품명"].astype(str).str.contains(q, case=False, na=False)
            ]
            results = pd.concat([results, partial])
        if results.empty:
            st.warning("🔍 검색 결과가 없습니다.")
        else:
            cols = st.columns(len(results))
            for col, (_, row) in zip(cols, results.iterrows()):
                with col:
                    product_card(row)
    else:
        st.info("제품코드 또는 제품명을 입력해주세요.")

def page_insight():
    st.title("📊 SAMI Insight (준비 중)")
    st.info("품질/VOC/생산 데이터 기반 자동 인사이트 대시보드는 이후 단계에서 연결 예정입니다.")
    st.write("- 예: CSV 업로드 → 이상탐지, 트렌드, 반복 VOC 패턴 도출")

# ============================
# 레이아웃: 사이드바 네비
# ============================
with st.sidebar:
    st.markdown("### 메뉴")
    sel = st.radio(
        "섹션",
        ["HOME", "CHAT", "PRODUCT", "INSIGHT"],
        index=["HOME","CHAT","PRODUCT","INSIGHT"].index(st.session_state.route),
        label_visibility="collapsed"
    )
    if sel != st.session_state.route:
        st.session_state.route = sel
        st.rerun()
    st.markdown("---")
    st.button("🔓 로그아웃", on_click=logout)
    st.caption("© Samyang Incheon 1 Plant • Internal Use Only")

# ============================
# 라우팅
# ============================
route = st.session_state.route
if route == "HOME":
    page_home()
elif route == "CHAT":
    page_chatbot()
elif route == "PRODUCT":
    page_product()
else:
    page_insight()
