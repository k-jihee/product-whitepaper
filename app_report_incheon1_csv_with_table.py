
import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime

# ============================
# 기본 설정 & 전역
# ============================
st.set_page_config(page_title="인천1공장 AI Agent", layout="wide")
APP_TITLE = "🏭 인천1공장 AI Agent"
DATA_DIR = "data"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ============================
# 인증
# ============================
PASSWORD = os.environ.get("INCHON1_PORTAL_PASSWORD", "samyang!11")
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "route" not in st.session_state:
    st.session_state.route = "HOME"  # HOME, CHAT, PRODUCT, DOCS_USER, DOCS_ADMIN, VOC, INSIGHT, VOICE

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
# 공용 유틸
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

def ensure_date_columns(df: pd.DataFrame):
    d = df.copy()
    d["요청일"] = pd.to_datetime(d.get("timestamp", None), errors="coerce").dt.date
    d["마감일"] = pd.to_datetime(d.get("due", None), errors="coerce").dt.date
    return d

def grouped_by_date(df: pd.DataFrame, group_key: str, columns_to_show: list):
    if df.empty:
        st.info("표시할 데이터가 없습니다.")
        return
    if group_key not in df.columns:
        st.warning(f"'{group_key}' 기준 열이 없어 그룹화할 수 없습니다.")
        return
    tmp = df.dropna(subset=[group_key]).copy()
    if tmp.empty:
        st.info("유효한 날짜 데이터가 없습니다.")
        return
    days = sorted(tmp[group_key].unique(), reverse=True)
    for day in days:
        day_df = tmp[tmp[group_key] == day].copy()
        with st.expander(f"📅 {day} — {len(day_df)}건", expanded=False):
            st.dataframe(day_df[columns_to_show], use_container_width=True)

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

def load_doc_requests_csv(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        df = pd.DataFrame(columns=[
            "timestamp", "requester", "team", "due", "category",
            "priority", "ref_product", "details", "files", "status"
        ])
        if 'status' not in df.columns:
            df['status'] = '대기'
        return df
    try:
        df = pd.read_csv(path, encoding="utf-8-sig", on_bad_lines='warn')
    except pd.errors.ParserError:
        df = pd.read_csv(path, encoding="utf-8-sig", on_bad_lines='skip')
    except UnicodeDecodeError:
        st.error("인코딩 오류(utf-8-sig). 파일을 다시 저장해주세요.")
        return pd.DataFrame(columns=[
            "timestamp", "requester", "team", "due", "category",
            "priority", "ref_product", "details", "files", "status"
        ])
    except Exception as e:
        st.error(f"❌ 예기치 않은 오류: {e}")
        return pd.DataFrame(columns=[
            "timestamp", "requester", "team", "due", "category",
            "priority", "ref_product", "details", "files", "status"
        ])
    if 'status' not in df.columns:
        df['status'] = '대기'
    return df

# ============================
# 페이지 구현
# ============================
def page_home():
    st.title(APP_TITLE)
    st.caption("공정지식 · 품질데이터 · 설비관리 · 규정검색 · VOC · 회의요약을 한 곳에서!")

    # 검색(카드 필터)
    q = st.text_input("🔎 툴 검색 (예: '제품', 'VOC', '회의')", key="home_search").strip().lower()

    cards = [
        {"key":"CHAT", "title":"GPT / 공정지식", "desc":"공정·제품·규정 등 일반 질의 응답", "tag":"챗봇"},
        {"key":"PRODUCT", "title":"제품백서", "desc":"제품 정보/규격/한도견본 확인 및 PDF 출력", "tag":"문서"},
        {"key":"DOCS_USER", "title":"서류 요청", "desc":"HACCP·ISO·제품규격 등 전사 문서 요청/다운", "tag":"업무 보조"},
        {"key":"DOCS_ADMIN", "title":"서류 승인", "desc":"요청 현황 조회 및 승인/반려 처리(관리자)", "tag":"관리"},
        {"key":"VOC", "title":"VOC 기록", "desc":"고객 VOC·내부 이상 기록·통계", "tag":"업무 보조"},
        {"key":"VOICE", "title":"Voice Note(베타)", "desc":"회의 녹음 업로드 → 요약/회의록(준비 중)", "tag":"업무 보조"},
        {"key":"INSIGHT", "title":"SAMI Insight(베타)", "desc":"제품/품질/VOC 패턴 인사이트(준비 중)", "tag":"인사이트"},
    ]

    # 필터 적용
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
    st.info("사내망 연결형 챗봇 연동 전까지는 간단한 FAQ 검색만 제공합니다.")
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

def page_docs_user():
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
        try:
            df_products = load_product_df()
        except Exception:
            try:
                df_products = pd.read_csv("product_data.csv", encoding="utf-8")
            except Exception:
                df_products = pd.DataFrame(columns=["제품코드","제품명"])
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
    st.markdown("---")
    st.subheader("내 요청 & 다운로드")
    if not requester:
        st.caption("상단의 '요청자'에 이름을 입력하면, 본인의 요청 내역 및 승인된 파일 다운로드 섹션이 나타납니다.")
        return
    try:
        _df_all = load_doc_requests_csv(path)
        _mine = _df_all[_df_all["requester"].astype(str) == str(requester)]
        if _mine.empty:
            st.info("본인 이름으로 접수된 요청이 없습니다.")
            return
        st.write(f"**'{requester}'님의 요청 (일별 보기)**")
        _mine2 = ensure_date_columns(_mine)
        group_choice = st.radio("그룹 기준", ["요청일(입력시각)", "마감일"], horizontal=True, key="user_group_choice")
        group_key = "요청일" if group_choice == "요청일(입력시각)" else "마감일"
        recent_days = st.slider("최근 N일만 보기 (0=전체)", min_value=0, max_value=60, value=0, step=5, key="user_recent_days")
        if recent_days > 0 and not _mine2.empty:
            cutoff = pd.Timestamp.today().date() - pd.Timedelta(days=recent_days)
            _mine2 = _mine2[_mine2[group_key] >= cutoff]
        _user_cols = ["timestamp", "team", "due", "category", "priority", "ref_product", "status", "details"]
        _user_cols = [c for c in _user_cols if c in _mine2.columns]
        grouped_by_date(_mine2, group_key, _user_cols)
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
        df = load_doc_requests_csv(path)
        st.subheader("📋 전체 요청 목록 (일별 보기)")
        df2 = ensure_date_columns(df)
        colA, colB, colC = st.columns([1.2, 1, 2])
        with colA:
            group_choice = st.radio("그룹 기준", ["요청일(입력시각)", "마감일"], horizontal=True, key="admin_group_choice")
            group_key = "요청일" if group_choice == "요청일(입력시각)" else "마감일"
        with colB:
            recent_days = st.slider("최근 N일", min_value=0, max_value=180, value=30, step=10, key="admin_recent_days")
        with colC:
            status_filter = st.multiselect("상태 필터", ["대기", "진행중", "승인", "반려"], default=["대기","진행중","승인","반려"], key="admin_status_filter")
        if status_filter:
            df2 = df2[df2["status"].isin(status_filter)]
        if recent_days > 0 and not df2.empty:
            cutoff = pd.Timestamp.today().date() - pd.Timedelta(days=recent_days)
            df2 = df2[df2[group_key] >= cutoff]
        _admin_cols = ["timestamp", "requester", "team", "due", "category", "priority", "ref_product", "status", "details"]
        _admin_cols = [c for c in _admin_cols if c in df2.columns]
        grouped_by_date(df2, group_key, _admin_cols)
        st.markdown("---")
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
        try:
            df_products = load_product_df()
        except Exception:
            try:
                df_products = pd.read_csv("product_data.csv", encoding="utf-8")
            except Exception:
                df_products = pd.DataFrame(columns=["제품코드","제품명"])
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

def page_insight():
    st.title("📊 SAMI Insight (베타)")
    st.info("품질/VOC/생산 데이터 기반의 자동 인사이트는 구축 예정입니다. CSV 업로드 기능부터 제공할 예정입니다.")

def page_voice():
    st.title("🎙️ Voice Note (베타)")
    st.info("회의 녹음 업로드 → 자동 요약/회의록 기능은 사내망 AI 엔진 연동 후 제공됩니다.")

# ============================
# 레이아웃: 상단 네비 + 사이드바
# ============================
with st.sidebar:
    st.markdown("### 메뉴")
    sel = st.radio(
        "섹션",
        ["HOME", "CHAT", "PRODUCT", "DOCS_USER", "DOCS_ADMIN", "VOC", "INSIGHT", "VOICE"],
        index=["HOME","CHAT","PRODUCT","DOCS_USER","DOCS_ADMIN","VOC","INSIGHT","VOICE"].index(st.session_state.route),
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
elif route == "DOCS_USER":
    page_docs_user()
elif route == "DOCS_ADMIN":
    page_docs_admin()
elif route == "VOC":
    page_voc()
elif route == "INSIGHT":
    page_insight()
else:
    page_voice()
