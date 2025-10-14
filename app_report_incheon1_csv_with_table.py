import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime

# ============================
# 기본 설정 & 인증
# ============================
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
    items = re.split(r"\s*-\s*", text.strip())
    items = [item for item in items if item]
    return "<br>".join(f"• {item.strip()}" for item in items)

# === 일별 그룹 표시 유틸 ===
def _ensure_date_columns(df: pd.DataFrame):
    """요청일(입력 시각)과 마감일을 날짜 컬럼으로 안전하게 추가"""
    d = df.copy()
    d["요청일"] = pd.to_datetime(d.get("timestamp", None), errors="coerce").dt.date
    d["마감일"] = pd.to_datetime(d.get("due", None), errors="coerce").dt.date
    return d

def _render_grouped_by_date(df: pd.DataFrame, group_key: str, columns_to_show: list):
    """날짜별로 접어서 표시"""
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
            cols = [c for c in columns_to_show if c in day_df.columns]
            st.dataframe(day_df[cols], use_container_width=True)

# ============================
# 제품백서 로딩
# ============================
@st.cache_data(show_spinner=False)
def load_product_df():
    try:
        df = pd.read_csv("product_data.csv", encoding="utf-8")
        if "용도" in df.columns:
            df["용도"] = df["용도"].astype(str).str.replace(r"\s*-\s*", " / ", regex=True)
        return df
    except Exception as e:
        st.error(f"❌ product_data.csv 불러오기 오류: {e}")
        return pd.DataFrame()

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

    html_template = f"""<style>
    table {{ table-layout: fixed; width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid gray; padding: 8px; text-align: center; }}
    th {{ background-color: #f2f2f2; }}
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
    </div>"""
    st.components.v1.html(html_template, height=600, scrolling=True)

def page_product():
    st.title("📘 제품백서")
    df = load_product_df()
    st.dataframe(df, use_container_width=True)

# ============================
# Helper: doc requests CSV loader
# ============================
def _load_doc_requests_df(csv_path):
    if not os.path.exists(csv_path):
        return pd.DataFrame(columns=[
            "timestamp","requester","team","due","category","priority","ref_product","details","files","status"
        ])
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig", on_bad_lines='skip')
    except Exception as e:
        st.error(f"파일 읽기 오류: {e}")
        df = pd.DataFrame()
    if 'status' not in df.columns:
        df['status'] = '대기'
    return df

# ============================
# 페이지: 서류 요청(사용자)
# ============================
def page_docs_request_user():
    st.title("🗂️ 서류 요청 (사용자)")
    requester = st.text_input("요청자 이름을 입력하세요")
    path = os.path.join(DATA_DIR, "doc_requests.csv")

    with st.form("req_form", clear_on_submit=True):
        team = st.text_input("부서")
        due = st.date_input("희망 마감일")
        category = st.text_input("요청 종류")
        ref_product = st.text_input("관련 제품코드/명")
        details = st.text_area("상세 요청 내용")
        submitted = st.form_submit_button("요청 저장")
        if submitted and requester:
            rec = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "requester": requester, "team": team, "due": str(due),
                "category": category, "priority": "보통", "ref_product": ref_product,
                "details": details, "files": "", "status": "대기"
            }
            pd.DataFrame([rec]).to_csv(path, mode="a", index=False, encoding="utf-8-sig",
                                       header=not os.path.exists(path))
            st.success("요청이 저장되었습니다.")

    st.markdown("---")
    if requester:
        df = _load_doc_requests_df(path)
        mine = df[df["requester"].astype(str) == str(requester)]
        if mine.empty:
            st.info("본인 요청이 없습니다.")
        else:
            st.subheader(f"📅 {requester}님의 요청 일별 보기")
            mine = _ensure_date_columns(mine)
            _render_grouped_by_date(mine, "요청일",
                ["timestamp","team","due","category","ref_product","status","details"])

# ============================
# 페이지: 서류 승인(관리자)
# ============================
def page_docs_admin():
    st.title("🛡️ 서류 승인 (관리자)")
    _admin_pw = st.text_input("관리자 암호", type="password")
    _ADMIN = os.environ.get("INCHON1_ADMIN_PW", "quality#77")
    path = os.path.join(DATA_DIR, "doc_requests.csv")

    if not _admin_pw:
        st.info("관리자 암호를 입력하세요.")
        return
    if _admin_pw != _ADMIN:
        st.error("관리자 암호가 올바르지 않습니다.")
        return

    df = _load_doc_requests_df(path)
    st.subheader("📋 전체 요청 목록 (일별 보기)")
    df2 = _ensure_date_columns(df)
    _render_grouped_by_date(df2, "요청일",
        ["timestamp","requester","team","due","category","priority","ref_product","status","details"])

    st.markdown("---")
    with st.form("admin_form"):
        idx = st.number_input("변경할 행 인덱스", min_value=0,
                              max_value=max(0,len(df)-1) if not df.empty else 0, step=1)
        new_status = st.selectbox("새 상태", ["승인","반려","대기","진행중"])
        submitted = st.form_submit_button("상태 반영")
        if submitted and not df.empty:
            df.loc[int(idx),"status"]=new_status
            df.to_csv(path,index=False,encoding="utf-8-sig")
            st.success("상태 변경 완료")

# ============================
# 페이지: VOC 기록
# ============================
def page_voc():
    st.title("📣 VOC 기록 / 이상발생 해석")
    st.info("간단히 VOC 기록 기능만 표시")

# ============================
# 사이드바
# ============================
with st.sidebar:
    st.markdown("## 🏭 삼양사 인천 1공장 제품백서")
    st.markdown("---")
    st.markdown("### 메뉴")
    page = st.radio(
        "섹션 선택",
        ["제품백서","서류 요청(사용자)","서류 승인(관리자)","VOC 기록(이상발생해석)"],
        index=1
    )
    st.markdown("---")
    st.caption("© Samyang Incheon 1 Plant • Internal Use Only")

# ============================
# 라우팅
# ============================
if page == "제품백서":
    page_product()
elif page == "서류 요청(사용자)":
    page_docs_request_user()
elif page == "서류 승인(관리자)":
    page_docs_admin()
else:
    page_voc()
