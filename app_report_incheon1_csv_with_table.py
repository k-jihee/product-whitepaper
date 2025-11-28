import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime

# ============================
# 기본 설정 & 인증
# ============================
import base64
import os   # 이미 상단에 있으니 중복만 아니면 됨

def set_background(image_path: str):
    # 파일이 없으면 경고만 띄우고 넘어가기
    if not os.path.exists(image_path):
        st.warning(f"배경 이미지 파일을 찾을 수 없습니다: {os.path.abspath(image_path)}")
        return

    with open(image_path, "rb") as f:
        data = f.read()
    encoded = base64.b64encode(data).decode()

    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:image/png;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}
        main .block-container {{
            background: transparent;
        }}
        [data-testid="stSidebar"] {{
            background: rgba(0, 0, 0, 0.55);
            color: #ffffff;
        }}
        body, [data-testid="stMarkdownContainer"], .stMarkdown p {{
            color: #f5f5f5;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

st.set_page_config(page_title="인천1공장 포털", layout="wide")

PASSWORD = os.environ.get("INCHON1_PORTAL_PASSWORD", "samyang!11")

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

# ✅ 여기 추가
set_background("binary.PNG")   # 또는 "배경.PNG"

# ============================
# [추가] 인트로 화면 로직
# ============================

# 1. 인트로 시청 여부를 저장할 세션 변수 초기화
if "intro_done" not in st.session_state:
    st.session_state["intro_done"] = False

def show_intro_page():
    # 인트로 화면에서는 사이드바를 숨기고, 배경색이나 여백을 조정하는 CSS 적용
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;} /* 사이드바 숨김 */
            .block-container {padding-top: 2rem;}      /* 상단 여백 조정 */
        </style>
    """, unsafe_allow_html=True)

    # 화면 구성을 위해 컬럼 사용 (중앙 정렬 효과)
    col1, col2, col3 = st.columns([1, 10, 1]) 
    
    with col2:
        # 업로드해주신 로봇 이미지 표시 (파일명이 정확해야 합니다)
        # 이미지 파일이 코드와 같은 폴더에 있어야 합니다.
        st.vedio("ntro_video.mp4", format="video/mp4", autoplay=True, muted=True)
        
        # 간격 추가
        st.write("") 
        st.write("")

        # 접속 버튼 (화면 중앙 느낌을 주기 위해 컬럼 내부 사용)
        b_col1, b_col2, b_col3 = st.columns([2, 3, 2])
        with b_col2:
            # 버튼을 누르면 인트로 종료 상태로 변경하고 리런
            if st.button("🚀 시스템 접속 (Enter)", use_container_width=True):
                st.session_state["intro_done"] = True
                st.rerun()

# 2. 로그인 성공 후, 인트로를 아직 안 봤다면 인트로 페이지 표시 후 중단
if st.session_state.authenticated and not st.session_state["intro_done"]:
    show_intro_page()
    st.stop()  # 여기서 코드 실행을 멈춰서 아래의 사이드바/대시보드가 보이지 않게 함


# ============================
# 공용 유틸
# ============================
def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

DATA_DIR = "data"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
ensure_dir(DATA_DIR)
ensure_dir(UPLOAD_DIR)

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

    # 1) 줄 단위로 먼저 나누기
    lines = str(text).splitlines()

    items = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 2) 맨 앞에 붙은 -, • 같은 불릿 제거
        #    예: "- 정제포도당(1A) 대비 입자가 큼" → "정제포도당(1A) 대비 입자가 큼"
        line = re.sub(r"^[-•]\s*", "", line)
        items.append(line)

    # 3) 각 줄 앞에 •를 붙이고 <br>로 줄바꿈
    return "<br>".join(f"• {item}" for item in items)

def _ensure_date_columns(df: pd.DataFrame):
    """요청일(입력 시각)과 마감일을 날짜 컬럼으로 안전하게 추가"""
    d = df.copy()
    # 요청일: timestamp(문자열) → date
    d["요청일"] = pd.to_datetime(d.get("timestamp", None), errors="coerce").dt.date
    # 마감일: due(문자열) → date
    d["마감일"] = pd.to_datetime(d.get("due", None), errors="coerce").dt.date
    return d

def _render_grouped_by_date(df: pd.DataFrame, group_key: str, columns_to_show: list):
    """
    날짜별로 접어서 표시. group_key는 '요청일' 또는 '마감일'
    columns_to_show는 테이블로 보여줄 컬럼 목록
    """
    if df.empty:
        st.info("표시할 데이터가 없습니다.")
        return
    if group_key not in df.columns:
        st.warning(f"'{group_key}' 기준 열이 없어 그룹화할 수 없습니다.")
        return

    # NaT/NaN 제거 후 날짜 내림차순
    tmp = df.dropna(subset=[group_key]).copy()
    if tmp.empty:
        st.info("유효한 날짜 데이터가 없습니다.")
        return

    # 최신 날짜가 위로 오게 정렬
    days = sorted(tmp[group_key].unique(), reverse=True)
    for day in days:
        day_df = tmp[tmp[group_key] == day].copy()
        with st.expander(f"📅 {day} — {len(day_df)}건", expanded=False):
            st.dataframe(day_df[columns_to_show], use_container_width=True)

# ============================
# 제품백서 로딩
# ============================
@st.cache_data(show_spinner=False)
def load_product_df():
    try:
        df = pd.read_csv("product_data.csv", encoding="utf-8")
        if "용도" in df.columns:
            df["용도"] = df["용도"].astype(str).str.replace(r"\s*-\s*", " / ", regex=True)
        # 계층구조 자동 생성
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
# 페이지: AI 챗봇(플레이스홀더)
# ============================
def page_chatbot():
    # 0) 이 페이지에서는 헤더/사이드바/메인 컨테이너 스크롤 전부 숨기기
    st.markdown(
        """
        <style>
        /* 상단 기본 헤더 숨기기 */
        header[data-testid="stHeader"] {
            display: none;
        }

        /* 메인 컨테이너 여백 제거 */
        main .block-container {
            padding: 0;
            margin: 0;
            max-width: 100%;
        }

        /* 전체 앱 컨테이너와 메인 영역, 사이드바 스크롤 숨기기 */
        html, body,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stSidebar"],
        [data-testid="stVerticalBlock"] {
            margin: 0;
            height: 100%;
            overflow: hidden !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 1) 화면 전체를 덮는 iframe (이 화면만 보이게)
    iframe_html = """
    <iframe
        src="https://samibot.samyang.com/chatbot/9e054af9-fdbe-4290-b914-7620c73a5e1d"
        style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 80vh;
            border: none;
        "
        allow="clipboard-write; microphone; camera">
    </iframe>
    """

    # 컴포넌트 자체는 화면에 잡히게 최소 높이만 줌
    st.components.v1.html(iframe_html, height=800, scrolling=False)


# ============================
# 페이지: 제품백서
# ============================
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
        print_button = ""
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
        print_button = ""
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

# ============================
# Helper: doc requests CSV loader
# ============================
def _load_doc_requests_df(csv_path):
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        df = pd.DataFrame(columns=[
            "timestamp", "requester", "team", "due", "category",
            "priority", "ref_product", "details", "files", "status"
        ])
        if 'status' not in df.columns:
            df['status'] = '대기'
        return df
    df = pd.DataFrame()
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig", on_bad_lines='warn')
    except pd.errors.ParserError as e:
        st.warning(f"⚠️ '{os.path.basename(csv_path)}' 파일 파싱 오류 발생. 손상된 줄을 건너뛰고 다시 시도합니다. (오류: {e})")
        try:
            df = pd.read_csv(csv_path, encoding="utf-8-sig", on_bad_lines='skip')
        except Exception as inner_e:
            st.error(f"❌ 손상된 줄을 건너뛰면서 파일을 읽는 중에도 오류 발생: {inner_e}")
            return pd.DataFrame(columns=[
                "timestamp", "requester", "team", "due", "category",
                "priority", "ref_product", "details", "files", "status"
            ])
    except UnicodeDecodeError:
        st.error(f"❌ '{os.path.basename(csv_path)}' 파일을 읽는 중 인코딩 오류가 발생했습니다. (현재: utf-8-sig)")
        return pd.DataFrame(columns=[
            "timestamp", "requester", "team", "due", "category",
            "priority", "ref_product", "details", "files", "status"
        ])
    except Exception as e:
        st.error(f"❌ '{os.path.basename(csv_path)}' 파일을 읽는 중 예기치 않은 오류가 발생했습니다: {e}")
        return pd.DataFrame(columns=[
            "timestamp", "requester", "team", "due", "category",
            "priority", "ref_product", "details", "files", "status"
        ])
    if 'status' not in df.columns:
        df['status'] = '대기'
    return df

# ============================
# 페이지: 서류 요청(사용자)
# ============================
def page_docs_request_user():
    st.title("🗂️ 서류 요청 (사용자)")
    st.caption("예: HACCP, ISO9001, 제품규격, FSSC22000, 할랄, 원산지규격서, MSDS 등")
    requester = st.text_input("요청자 (이름을 입력하면 '내 요청' 및 '다운로드' 확인 가능)")
    path = os.path.join(DATA_DIR, "doc_requests.csv")
    with st.form("doc_req_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            team = st.text_input("부서")
            due = st.date_input("희망 마감일")
        with col2:
            st.markdown("**요청 종류**")
            _colA, _colB, _colC, _colD = st.columns(4)
            _labels = [
                "HACCP 인증서", "ISO9001 인증서", "제품규격", "FSSC22000",
                "할랄인증서", "원산지규격서", "MSDS", "기타",
            ]
            _checks = []
            for idx, lbl in enumerate(_labels):
                with [_colA, _colB, _colC, _colD][idx % 4]:
                    _checks.append(st.checkbox(lbl, key=f"req_kind_{idx}"))
            category = ", ".join([lbl for lbl, on in zip(_labels, _checks) if on])
            priority = st.select_slider("우선순위", ["낮음","보통","높음","긴급"], value="보통")
        # 제품선택
        try:
            df_products = load_product_df()
        except Exception:
            import pandas as _pd
            try:
                df_products = _pd.read_csv("product_data.csv", encoding="utf-8")
            except Exception:
                df_products = _pd.DataFrame(columns=["제품코드","제품명"])
        if not df_products.empty and {"제품코드","제품명"}.issubset(set(df_products.columns)):
            _opts = (df_products[["제품코드","제품명"]]
                        .astype(str)
                        .dropna()
                        .assign(_opt=lambda d: d["제품코드"].str.strip() + " | " + d["제품명"].str.strip())
                        ["_opt"]
                        .drop_duplicates()
                        .sort_values()
                        .tolist())
        else:
            _opts = []
        multi_pick = st.toggle("여러 제품 선택", value=False, help="여러 제품에 대한 요청이라면 켜주세요.")
        if multi_pick:
            _picked = st.multiselect("관련 제품코드/명 (검색 가능)", options=_opts, placeholder="예: GID*** | 포도당...")
            ref_product = ", ".join(_picked) if _picked else ""
        else:
            ref_product = st.selectbox("관련 제품코드/명 (선택)", options=[""] + _opts, index=0,
                                       placeholder="클릭 후 검색/선택",
                                       help="클릭하면 검색 드롭다운이 열립니다.")
        details = st.text_area("상세 요청 내용", height=140)
        files = st.file_uploader("참고 파일 업로드 (다중)", accept_multiple_files=True)
        submitted = st.form_submit_button("요청 저장")
        if submitted:
            if not requester:
                st.error("요청자 이름을 반드시 입력해주세요.")
            else:
                saved_files = []
                for f in files or []:
                    save_path = os.path.join(UPLOAD_DIR, f.name)
                    with open(save_path, "wb") as out:
                        out.write(f.read())
                    saved_files.append(save_path)
                rec = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "requester": requester, "team": team, "due": str(due),
                    "category": category, "priority": priority, "ref_product": ref_product,
                    "details": details, "files": ";".join(saved_files), "status": "대기"
                }
                pd.DataFrame([rec]).to_csv(path, mode="a", index=False, encoding="utf-8-sig",
                                           header=not os.path.exists(path))
                st.success("요청이 저장되었습니다.")
    # 🔒 사용자 페이지는 '전체 요청 현황'을 보여주지 않음 (본인 것만)
    st.markdown("---")
    st.subheader("내 요청 & 다운로드")
    if not requester:
        st.caption("상단의 '요청자'에 이름을 입력하면, 본인의 요청 내역 및 승인된 파일 다운로드 섹션이 나타납니다.")
        return
    try:
        _df_all = _load_doc_requests_df(path)
        _mine = _df_all[_df_all["requester"].astype(str) == str(requester)]
        if _mine.empty:
            st.info("본인 이름으로 접수된 요청이 없습니다.")
            return

        # 2) 사용자 페이지(내 요청) — “일별 보기”로 교체
        # 기존: st.dataframe(_mine.tail(20), ...)
        # 교체: 날짜 그룹 선택 + 그룹 표시
        st.write(f"**'{requester}'님의 요청 (일별 보기)**")

        # 날짜 컬럼 추가
        _mine2 = _ensure_date_columns(_mine)

        # 그룹 기준 선택
        group_choice = st.radio("그룹 기준", ["요청일(입력시각)", "마감일"], horizontal=True, key="user_group_choice")
        group_key = "요청일" if group_choice == "요청일(입력시각)" else "마감일"

        # (선택) 최근 N일만 보기 필터
        recent_days = st.slider("최근 N일만 보기 (0=전체)", min_value=0, max_value=60, value=0, step=5, key="user_recent_days")
        if recent_days > 0 and not _mine2.empty:
            cutoff = pd.Timestamp.today().date() - pd.Timedelta(days=recent_days)
            _mine2 = _mine2[_mine2[group_key] >= cutoff]

        # 날짜별 접기 테이블
        _user_cols = ["timestamp", "team", "due", "category", "priority", "ref_product", "status", "details"]
        _user_cols = [c for c in _user_cols if c in _mine2.columns]
        _render_grouped_by_date(_mine2, group_key, _user_cols)

        _approved_list = _mine[_mine["status"] == "승인"]
        if _approved_list.empty:
            st.info("아직 승인된 요청이 없습니다.")
            return

        st.markdown("---")
        st.success("✅ **승인된 요청 파일 다운로드**")
        st.info("파일명 규칙: `제품코드_인증서키.확장자` (예: GIS7030_HACCP.pdf)")
        _cert_name_map = {
            "HACCP 인증서": "HACCP", "ISO9001 인증서": "ISO9001",
            "제품규격": "SPEC", "FSSC22000": "FSSC22000",
            "할랄인증서": "HALAL", "원산지규격서": "COO", "MSDS": "MSDS",
            "기타": "ETC"
        }
        extensions = ["pdf", "docx", "xlsx", "pptx", "jpg", "png"]
        found_any_files_globally = False
        for _, approved_req in _approved_list.iterrows():
            _cat_str = approved_req.get("category", "")
            _prod_str = approved_req.get("ref_product", "")
            with st.container(border=True):
                st.write(f"**요청일: {approved_req.get('timestamp')} / 제품: {_prod_str if _prod_str else 'N/A'}**")
                # ✅ 파이프(|) 유무와 상관없이 코드 인식
                tokens = [t.strip() for t in str(_prod_str).split(',') if t.strip()]
                product_codes = [t.split('|')[0].strip() for t in tokens] or ['N/A']
                requested_certs = [c.strip() for c in str(_cat_str).split(',') if c.strip()]
                if not requested_certs:
                    st.write("다운로드할 인증서 종류가 지정되지 않았습니다.")
                    continue
                files_for_this_request = []
                for code in product_codes:
                    if code == 'N/A':
                        continue
                    for cert_label in requested_certs:
                        cert_key = _cert_name_map.get(cert_label, cert_label)
                        file_found = False
                        for ext in extensions:
                            fname = f"{code}_{cert_key}.{ext}"
                            fpath = os.path.join(UPLOAD_DIR, fname)
                            if os.path.exists(fpath):
                                files_for_this_request.append({"path": fpath, "name": fname,
                                                               "label": f"{code} - {cert_label}"})
                                found_any_files_globally = True
                                file_found = True
                                break
                        if not file_found and cert_label != "기타":
                            st.warning(f"❌ '{code} - {cert_label}' 파일을 찾을 수 없습니다. "
                                       f"(예상: `{code}_{cert_key}.*` in `{os.path.abspath(UPLOAD_DIR)}`)")
                if files_for_this_request:
                    for file_info in files_for_this_request:
                        with open(file_info["path"], "rb") as _f:
                            st.download_button(
                                label=f"⬇️ {file_info['label']}",
                                data=_f.read(),
                                file_name=file_info["name"],
                                mime="application/octet-stream"
                            )
        if not found_any_files_globally:
            st.info("다운로드 가능한 승인된 파일이 없습니다. 품질팀에 문의하세요.")
    except FileNotFoundError:
        st.info("아직 요청 기록이 없습니다.")
    except Exception as e:
        st.error(f"내 요청을 불러오는 중 오류 발생: {e}")

# ============================
# 페이지: 서류 승인(관리자)
# ============================
def page_docs_admin():
    st.title("🛡️ 서류 승인 (관리자)")
    st.caption("품질팀 전용: 전체 요청 조회 및 승인/반려 처리")
    _admin_pw = st.text_input("관리자 암호", type="password", key="admin_pw")
    _ADMIN = os.environ.get("INCHON1_ADMIN_PW", "quality#77")
    path = os.path.join(DATA_DIR, "doc_requests.csv")
    if not _admin_pw:
        st.info("관리자 암호를 입력하세요.")
        return
    if _admin_pw != _ADMIN:
        st.error("관리자 암호가 올바르지 않습니다.")
        return
    try:
        df = _load_doc_requests_df(path)
        
        # 3) 관리자 페이지(전체 요청) — “일별 보기 + 기간 필터” 추가
        st.subheader("📋 전체 요청 목록 (일별 보기)")

        df2 = _ensure_date_columns(df)

        # 필터: 그룹 기준 + 기간
        colA, colB, colC = st.columns([1.2, 1, 2])
        with colA:
            group_choice = st.radio("그룹 기준", ["요청일(입력시각)", "마감일"], horizontal=True, key="admin_group_choice")
            group_key = "요청일" if group_choice == "요청일(입력시각)" else "마감일"

        with colB:
            recent_days = st.slider("최근 N일", min_value=0, max_value=180, value=30, step=10, key="admin_recent_days")

        with colC:
            status_filter = st.multiselect("상태 필터", ["대기", "진행중", "승인", "반려"], default=["대기","진행중","승인","반려"], key="admin_status_filter")

        # 상태 필터 적용
        if status_filter:
            df2 = df2[df2["status"].isin(status_filter)]

        # 기간 필터 적용
        if recent_days > 0 and not df2.empty:
            cutoff = pd.Timestamp.today().date() - pd.Timedelta(days=recent_days)
            df2 = df2[df2[group_key] >= cutoff]

        _admin_cols = ["timestamp", "requester", "team", "due", "category", "priority", "ref_product", "status", "details"]
        _admin_cols = [c for c in _admin_cols if c in df2.columns]
        _render_grouped_by_date(df2, group_key, _admin_cols)
        
        st.markdown("---") # Add a separator before the form
        
        with st.form("admin_form"):
            colA, colB = st.columns([1, 2])
            with colA:
                sel_idx = st.number_input("승인/반려할 행 인덱스", min_value=0,
                                          max_value=max(0, len(df)-1) if not df.empty else 0, step=1)
            with colB:
                status_options = ["승인","반려","대기","진행중"]
                current_status = df.loc[int(sel_idx), 'status'] if not df.empty else '대기'
                default_index = status_options.index(current_status) if current_status in status_options else 2
                new_status = st.selectbox("처리 상태", status_options, index=default_index)
            submitted = st.form_submit_button("상태 반영")
            if submitted:
                if not df.empty and int(sel_idx) < len(df):
                    df.loc[int(sel_idx), "status"] = new_status
                    df.to_csv(path, index=False, encoding="utf-8-sig")
                    st.success(f"인덱스 {sel_idx}의 상태가 '{new_status}'(으)로 변경되었습니다. 새로고침 후 확인하세요.")
                else:
                    st.warning("선택된 인덱스에 해당하는 요청이 없습니다.")
    except FileNotFoundError:
        st.info("요청 기록이 없습니다.")
    except Exception as e:
        st.error(f"관리자 뷰 로딩 중 오류: {e}")
        st.exception(e)

# ============================
# 페이지: VOC 기록(이상발생해석)
# ============================
def page_voc():
    st.title("📣 VOC 기록 / 이상발생 해석")
    with st.form("voc_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            date = st.date_input("발생일")
        with c2:
            source = st.selectbox("유형", ["고객 VOC", "내부 이상", "민원", "기타"])
        with c3:
            severity = st.select_slider("심각도", ["Low","Medium","High","Critical"], value="Medium")

        # 제품선택 로직을 서류 요청 페이지에서 가져옴
        try:
            df_products = load_product_df()
        except Exception:
            import pandas as _pd
            try:
                df_products = _pd.read_csv("product_data.csv", encoding="utf-8")
            except Exception:
                df_products = _pd.DataFrame(columns=["제품코드","제품명"])

        if not df_products.empty and {"제품코드","제품명"}.issubset(set(df_products.columns)):
            _opts = (df_products[["제품코드","제품명"]]
                        .astype(str)
                        .dropna()
                        .assign(_opt=lambda d: d["제품코드"].str.strip() + " | " + d["제품명"].str.strip())
                        ["_opt"]
                        .drop_duplicates()
                        .sort_values()
                        .tolist())
        else:
            _opts = []

        multi_pick_voc = st.toggle("여러 제품 선택", value=False, help="여러 제품에 대한 VOC라면 켜주세요.", key="voc_multi_pick")
        if multi_pick_voc:
            _picked_voc = st.multiselect("관련 제품코드/명 (검색 가능)", options=_opts, placeholder="예: GID*** | 포도당...", key="voc_product_multiselect")
            product = ", ".join(_picked_voc) if _picked_voc else ""
        else:
            product = st.selectbox("관련 제품코드/명 (선택)", options=[""] + _opts, index=0,
                                       placeholder="클릭 후 검색/선택",
                                       help="클릭하면 검색 드롭다운이 열립니다.", key="voc_product_selectbox")

        desc = st.text_area("내용", height=120)
        cause = st.text_area("원인(가설)", height=100)
        action = st.text_area("즉시조치/대책", height=100)
        uploaded = st.file_uploader("첨부 (사진/문서)", accept_multiple_files=True)
        submit = st.form_submit_button("기록 저장")
        if submit:
            saved_files = []
            for f in uploaded or []:
                save_path = os.path.join(UPLOAD_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{f.name}")
                with open(save_path, "wb") as out:
                    out.write(f.read())
                saved_files.append(save_path)
            rec = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "date": str(date), "type": source, "severity": severity,
                "product": product, "desc": desc, "cause": cause, "action": action,
                "files": ";".join(saved_files)
            }
            path = os.path.join(DATA_DIR, "voc_logs.csv")
            pd.DataFrame([rec]).to_csv(path, mode="a", index=False, encoding="utf-8-sig",
                                       header=not os.path.exists(path))
            st.success("VOC가 저장되었습니다.")
    path = os.path.join(DATA_DIR, "voc_logs.csv")
    if os.path.exists(path):
        st.markdown("---")
        st.subheader("📈 VOC 로그")
        df = pd.read_csv(path)
        st.dataframe(df, use_container_width=True)
        with st.expander("간단 통계", expanded=False):
            st.write("유형별 건수")
            st.bar_chart(df["type"].value_counts())
            st.write("심각도별 건수")
            st.bar_chart(df["severity"].value_counts())


# ============================
# 페이지: 홈 (대시보드)
# ============================
def page_home():

    # 🔥 챗봇 페이지에서 전체 레이아웃을 숨겼던 CSS 초기화 (타이틀이 다시 보이도록)
    st.markdown("""
        <style>
        html, body,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stSidebar"],
        [data-testid="stVerticalBlock"] {
            overflow: auto !important;
            height: auto !important;
        }
        main .block-container {
            padding: 1rem 2rem !important;
            margin: auto !important;
            max-width: 100% !important;
        }
        header[data-testid="stHeader"] {
            display: block !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # 🔎 질문하기 창(클릭 → 챗봇 이동)
    st.markdown("""
        <style>
        .fake-input-btn button {
            width: 100% !important;
            border-radius: 10px !important;
            border: 1px solid #ff4b4b !important;
            background: #f5f6fa !important;
            color: #888 !important;
            text-align: left !important;
            padding: 12px 16px !important;
            font-size: 14px !important;
            height: 46px !important;
        }
        .fake-input-btn button:hover {
            background: #eceff4 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 class='home-title'>🏭 인천1공장 AI 에이전트 🏭</h1>", unsafe_allow_html=True)
    st.markdown("<p class='home-sub'>주요 기능을 한 곳에서 빠르게 이동하세요.</p>", unsafe_allow_html=True)
    st.markdown("<div class='fake-input-btn'>", unsafe_allow_html=True)
    clicked = st.button("인천 1공장 AI 챗봇에게 질문하기...", use_container_width=True, key="fake_search")
    st.markdown("</div>", unsafe_allow_html=True)

    if clicked:
        st.session_state["page"] = "인천 1공장 AI 챗봇"
        st.rerun()




    # 카드 데이터
    cards = [
        {"emoji": "🤖", "title": "인천 1공장 AI 챗봇", "desc": "질문하면 바로 챗봇으로 이동합니다.", "goto": "인천 1공장 AI 챗봇"},
        {"emoji": "📘", "title": "제품 백서", "desc": "제품 정보, 규격, COA를 확인합니다.", "goto": "제품백서"},
        {"emoji": "🗂️", "title": "서류 요청", "desc": "HACCP, ISO, 규격서 등을 요청합니다.", "goto": "서류 요청(사용자)"},
        {"emoji": "📣", "title": "VOC 로그", "desc": "VOC 및 이상 발생 내역을 기록합니다.", "goto": "VOC 기록(이상발생해석)"},
    ]

    # 🔹 가로 4칸 카드 (st.columns 사용)
    cols = st.columns(len(cards))
    for col, c in zip(cols, cards):
        with col:
            with st.container(border=True):
                st.markdown(
                    f"<div class='home-card-title'>{c['emoji']} {c['title']}</div>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<div class='home-card-desc'>{c['desc']}</div>",
                    unsafe_allow_html=True
                )
                st.write("")  # 여백
                if st.button("바로가기", key=f"go_{c['goto']}"):
                    st.session_state["page"] = c["goto"]
                    st.rerun()


# ============================
# 사이드바 네비게이션
# ============================
with st.sidebar:
    st.markdown("## 🏭 인천 1공장 AI 에이전트 🏭")
    st.markdown("---")
    st.markdown("### 메뉴")

    if "page" not in st.session_state:
        st.session_state["page"] = "Home"

    page = st.radio(
        "섹션을 선택하세요",
        ["Home", "인천 1공장 AI 챗봇", "제품백서", "서류 요청(사용자)", "서류 승인(관리자)", "VOC 기록(이상발생해석)"],
        index=["Home","인천 1공장 AI 챗봇","제품백서","서류 요청(사용자)","서류 승인(관리자)","VOC 기록(이상발생해석)"].index(st.session_state["page"]),
        label_visibility="collapsed"
    )

    st.session_state["page"] = page
    st.markdown("---")
    st.caption("© Samyang Incheon 1 Plant • Internal Use Only")


# ============================
# 라우팅
# ============================
if page == "Home":
    page_home()
elif page == "인천 1공장 AI 챗봇":
    page_chatbot()
elif page == "제품백서":
    page_product()
elif page == "서류 요청(사용자)":
    page_docs_request_user()
elif page == "서류 승인(관리자)":
    page_docs_admin()
else:
    page_voc()
