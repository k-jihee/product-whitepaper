
import streamlit as st
import pandas as pd
import os, re
from datetime import datetime

st.set_page_config(page_title="인천1공장 포털 (체크리스트·승인형)", layout="wide")

# ------------------------ 공통 경로 ------------------------
DATA_DIR = "data"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
CATALOG_CSV = os.path.join(DATA_DIR, "doc_catalog.csv")
PENDING_CSV = os.path.join(DATA_DIR, "doc_request_pending.csv")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ------------------------ 가벼운 인증 ----------------------
PORTAL_PASSWORD = os.environ.get("INCHON1_PORTAL_PASSWORD", "samyang!11")
if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False
if not st.session_state.auth_ok:
    st.title("🔒 인천1공장 포털 (승인형)")
    pw = st.text_input("비밀번호", type="password")
    if pw == PORTAL_PASSWORD:
        st.session_state.auth_ok = True
        st.rerun()
    elif pw:
        st.error("비밀번호가 올바르지 않습니다.")
    st.stop()

# -------------------- 제품백서 헬퍼 (간략 버전) --------------
@st.cache_data(show_spinner=False)
def load_product_df():
    try:
        df = pd.read_csv("product_data.csv", encoding="utf-8")
    except Exception:
        df = pd.DataFrame()
    return df

def clean_int(value):
    try:
        cleaned = re.sub(r"[^\d.]", "", str(value))
        if cleaned == "":
            return "-"
        return f"{int(float(cleaned)):,} KG"
    except (ValueError, TypeError):
        return "-"

# ---------------------- 카탈로그 초기화 ---------------------
if not os.path.exists(CATALOG_CSV):
    pd.DataFrame([
        {"문서유형":"인증서","문서명":"HACCP 인증서","파일":"HACCP_2025.pdf"},
        {"문서유형":"인증서","문서명":"FSSC22000 인증서","파일":"FSSC_2025.pdf"},
        {"문서유형":"인증서","문서명":"ISO9001 인증서","파일":"ISO9001_2025.pdf"},
        {"문서유형":"증명서","문서명":"원산지증명서","파일":"COO_sample.pdf"},
    ]).to_csv(CATALOG_CSV, index=False, encoding="utf-8-sig")

def load_catalog():
    return pd.read_csv(CATALOG_CSV)

def save_pending(rec: dict):
    header = not os.path.exists(PENDING_CSV)
    pd.DataFrame([rec]).to_csv(PENDING_CSV, mode="a", index=False, encoding="utf-8-sig", header=header)

def read_pending():
    if os.path.exists(PENDING_CSV):
        return pd.read_csv(PENDING_CSV)
    return pd.DataFrame(columns=["요청ID","요청일시","요청자","부서","마감일","관련","문서목록","상태","메모"])

def write_pending(df):
    df.to_csv(PENDING_CSV, index=False, encoding="utf-8-sig")

# ------------------------- UI 구조 -------------------------
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/9/9a/Samyang_logo_2020.svg", width=140)
    page = st.radio("메뉴", ["챗봇(간이검색)", "제품백서", "서류요청(체크리스트)", "승인관리(품질팀)"])
    st.caption("© Samyang Incheon 1 Plant")

# ------------------------- 챗봇 -----------------------------
if page == "챗봇(간이검색)":
    st.title("💬 챗봇 (간이검색)")
    df = load_product_df()
    q = st.text_input("키워드 (예: CCP, mesh, 포도당)")
    if q:
        mask = pd.Series(False, index=df.index)
        for c in df.columns:
            if df[c].dtype == object:
                mask |= df[c].astype(str).str.contains(q, case=False, na=False)
        hits = df.loc[mask].head(30)
        st.dataframe(hits, use_container_width=True)
    with st.expander("개선요청 남기기"):
        who = st.text_input("요청자")
        team = st.text_input("부서")
        need = st.text_area("원하는 기능")
        if st.button("요청 저장"):
            save_pending({
                "요청ID": f"IMPROVE-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "요청일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "요청자": who, "부서": team, "마감일": "", "관련": "챗봇개선",
                "문서목록": need, "상태": "건의", "메모": ""
            })
            st.success("접수되었습니다.")

# ------------------------- 제품백서 -------------------------
elif page == "제품백서":
    st.title("📘 제품백서 (요약보기)")
    df = load_product_df()
    if df.empty:
        st.info("product_data.csv 파일을 같은 폴더에 두면 목록이 표시됩니다.")
    else:
        st.dataframe(df[["제품코드","제품명"]].head(200), use_container_width=True)

# ---------------------- 서류요청(체크리스트) ----------------
elif page == "서류요청(체크리스트)":
    st.title("📂 서류 체크리스트로 요청하기")
    user = st.text_input("요청자")
    team = st.text_input("부서")
    due = st.date_input("희망 마감일")
    ref = st.text_input("관련 제품코드/명 (선택)")

    st.subheader("요청할 문서를 체크하세요")
    catalog = load_catalog()
    selected = []
    cols = st.columns(3)
    for i, row in catalog.iterrows():
        with cols[i % 3]:
            if st.checkbox(f"[{row['문서유형']}] {row['문서명']}", key=f"doc_{i}"):
                selected.append(row['문서명'])
    memo = st.text_area("메모(선택)", height=100)

    if st.button("요청하기", type="primary"):
        if not user or not team or not selected:
            st.error("요청자/부서/문서 선택은 필수입니다.")
        else:
            rec = {
                "요청ID": f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "요청일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "요청자": user, "부서": team, "마감일": str(due),
                "관련": ref, "문서목록": ", ".join(selected),
                "상태": "대기", "메모": memo
            }
            save_pending(rec)
            st.success("요청이 접수되었습니다. (승인관리 탭에서 처리됩니다)")

    st.markdown("---")
    st.subheader("내 최근 요청")
    df = read_pending()
    mine = df[df["요청자"].astype(str)==user] if not df.empty and user else df.tail(20)
    st.dataframe(mine.tail(20), use_container_width=True)

# ---------------------- 승인관리(품질팀) --------------------
else:
    st.title("🛠 승인관리 (품질팀 전용)")
    # 간단 비번
    admin_pw = st.text_input("관리자 암호", type="password")
    ADMIN_PASSWORD = os.environ.get("INCHON1_ADMIN_PW", "quality#77")
    if admin_pw != ADMIN_PASSWORD:
        st.info("관리자 암호를 입력하세요.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["대기 목록", "카탈로그 관리", "업로드 폴더 링크"])

    with tab1:
        df = read_pending()
        if df.empty or (df["상태"]=="건의").all():
            st.info("대기 중인 요청이 없습니다.")
        else:
            view = df[df["상태"].isin(["대기","진행중"])]
            st.dataframe(view, use_container_width=True)
            sel = st.text_input("처리할 요청ID 입력")
            new = st.selectbox("상태 변경", ["진행중","완료","반려"])
            note = st.text_input("비고/메모 추가", value="")
            if st.button("상태 업데이트"):
                if sel and (df["요청ID"]==sel).any():
                    df.loc[df["요청ID"]==sel, "상태"] = new
                    if note:
                        df.loc[df["요청ID"]==sel, "메모"] = note
                    write_pending(df)
                    st.success("업데이트 완료")
                else:
                    st.error("요청ID를 확인하세요.")

    with tab2:
        st.subheader("문서 카탈로그 (체크리스트 항목)")
        cat = load_catalog()
        edited = st.data_editor(cat, num_rows="dynamic", use_container_width=True)
        if st.button("카탈로그 저장"):
            edited.to_csv(CATALOG_CSV, index=False, encoding="utf-8-sig")
            st.success("저장 완료")

    with tab3:
        st.write("첨부용 실제 파일은 아래 폴더에 보관합니다 (현재 버전은 메일 발송 없음).")
        st.code(os.path.abspath(UPLOAD_DIR))
        if os.listdir(UPLOAD_DIR):
            st.write("현재 파일:")
            st.write(os.listdir(UPLOAD_DIR))
        else:
            st.info("uploads 폴더가 비어 있습니다.")
