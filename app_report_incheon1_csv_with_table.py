from typing import Optional

import streamlit as st
import pandas as pd
import numpy as np
import re
import os
import io
import time
from typing import List, Tuple, Dict, Any

# Optional imports with graceful fallback
try:
    import git  # GitPython
    GIT_AVAILABLE = True
except Exception:
    GIT_AVAILABLE = False

try:
    import pdfplumber
    PDF_AVAILABLE = True
except Exception:
    PDF_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

# =====================================
# 기본 설정
# =====================================
st.set_page_config(page_title="Product Whitepaper AI", layout="wide")
APP_TITLE = "🤖 Product Whitepaper AI"
PROJECT_SUBTITLE = "GitHub 문서를 불러와 챗봇처럼 질의응답 + 제품백서 전용 뷰"
REPO_URL_DEFAULT = "https://github.com/k-jihee/product-whitepaper"

# 라우팅 기본값: 첫 화면은 '챗봇'
if "route" not in st.session_state:
    st.session_state.route = "CHAT"  # CHAT, WHITEPAPER
if "authenticated" not in st.session_state:
    st.session_state.authenticated = True  # 필요 시 비밀번호 처리로 변경 가능
if "vector_ready" not in st.session_state:
    st.session_state.vector_ready = False

# =====================================
# 유틸
# =====================================
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
            key = key.strip() if isinstance(key, str) else key
            spec_dict[key.strip()] = value.strip()
    return spec_dict

def format_features(text):
    if pd.isna(text):
        return "-"
    items = re.split(r"\s*-\s*", text.strip())
    items = [item for item in items if item]
    return "<br>".join(f"• {item.strip()}" for item in items)

def highlight_terms(text: str, query: str) -> str:
    if not query:
        return text
    try:
        pattern = re.compile("(" + re.escape(query) + ")", re.IGNORECASE)
        return pattern.sub(r"<mark>\1</mark>", text)
    except re.error:
        return text



# ----------------------------
# 규칙 기반 응답 함수 (RAG 이전 고정 답)
# ----------------------------
def get_rule_based_answer(query: str) -> Optional[str]:
    """특정 질문에 대해 RAG를 거치지 않고 고정 답변만 반환합니다."""
    if not query:
        return None


# =====================================
# GitHub Repo 동기화/로딩
# =====================================
@st.cache_data(show_spinner=False)
def clone_or_update_repo(repo_url: str, repo_dir: str) -> Tuple[bool, str]:
    os.makedirs(repo_dir, exist_ok=True)
    if not GIT_AVAILABLE:
        return False, "GitPython이 설치되어 있지 않습니다. 'pip install GitPython' 후 다시 시도하세요."
    try:
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            repo = git.Repo(repo_dir)
            origin = repo.remotes.origin
            origin.pull()
            return True, "🔄 최신 내용으로 업데이트했습니다."
        else:
            git.Repo.clone_from(repo_url, repo_dir)
            return True, "✅ 저장소를 클론했습니다."
    except Exception as e:
        return False, f"❌ 저장소 동기화 오류: {e}"

def _read_text_file(path: str) -> str:
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with io.open(path, "r", encoding="cp949") as f:
                return f.read()
        except Exception:
            return ""
    except Exception:
        return ""

def _read_pdf_text(path: str) -> str:
    if not PDF_AVAILABLE:
        return ""
    text = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text.append(page.extract_text() or "")
    except Exception:
        return ""
    return "\n".join(text)

def _chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> List[str]:
    if not text:
        return []
    tokens = re.split(r"(\s+)", text)
    chunks = []
    i = 0
    while i < len(tokens):
        window = tokens[i:i+chunk_size]
        chunks.append("".join(window).strip())
        i += max(1, chunk_size - overlap)
    return [c for c in chunks if c]

@st.cache_data(show_spinner=False)
def load_repo_corpus(repo_dir: str, exts: Tuple[str, ...] = (".md", ".txt", ".csv", ".json", ".pdf")) -> List[Dict[str, Any]]:
    corpus = []
    for root, _, files in os.walk(repo_dir):
        for fn in files:
            if not fn.lower().endswith(exts):
                continue
            path = os.path.join(root, fn)
            text = ""
            if fn.lower().endswith((".md", ".txt", ".csv", ".json")):
                text = _read_text_file(path)
            elif fn.lower().endswith(".pdf"):
                text = _read_pdf_text(path)
            if not text:
                continue
            # 파일 단위 chunking
            for idx, chunk in enumerate(_chunk_text(text)):
                corpus.append({
                    "path": path.replace(repo_dir, "").lstrip(os.sep),
                    "chunk_id": idx,
                    "text": chunk,
                })
    return corpus

@st.cache_resource(show_spinner=False)
def build_vector_store(corpus: List[Dict[str, Any]]):
    if not SKLEARN_AVAILABLE:
        return None, None
    texts = [c["text"] for c in corpus]
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=100_000,
        min_df=1,
        stop_words=None
    )
    X = vectorizer.fit_transform(texts)
    return vectorizer, X

def retrieve(query: str, vectorizer, X, corpus: List[Dict[str, Any]], topk: int = 6) -> List[Dict[str, Any]]:
    if not (SKLEARN_AVAILABLE and vectorizer is not None and X is not None):
        # 단순 키워드 필터링 fallback
        q = query.lower()
        ranked = []
        for doc in corpus:
            score = (doc["text"].lower().count(q)) if q else 0
            if score > 0:
                ranked.append((score, doc))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in ranked[:topk]]
    q_vec = vectorizer.transform([query])
    sims = cosine_similarity(q_vec, X)[0]
    idxs = np.argsort(-sims)[:topk]
    results = []
    for i in idxs:
        doc = corpus[i].copy()
        doc["score"] = float(sims[i])
        results.append(doc)
    return results

def synthesize_answer(query: str, hits: List[Dict[str, Any]]) -> str:
    """
    간단 요약기: 관련 chunk들을 연결해 답변 초안을 만듭니다.
    (필요 시 OPENAI_API_KEY 설정하여 LLM 호출 파이프라인을 추가하실 수 있습니다.)
    """
    if not hits:
        return "관련 문서를 찾지 못했습니다. 질문을 조금 다르게 해보시겠어요?"
    # 가장 상위 3개 chunk 기반 추출형 응답
    merged = "\n\n".join([h["text"] for h in hits[:3]])
    # 길이 제한
    merged = merged[:2000]
    # 쿼리 하이라이트
    merged = highlight_terms(merged, query)
    prefix = "아래는 저장소 문서에서 추출된 관련 내용입니다:\n\n"
    return prefix + merged

# =====================================
# 제품백서 로딩
# =====================================
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

# =====================================
# 페이지: 챗봇
# =====================================
def page_chatbot():
    st.title("💬 챗봇 전용")
    st.caption("GitHub 저장소의 문서를 기반으로 질의응답합니다. (NotebookLM 유사 RAG)")

    with st.expander("⚙️ 데이터 소스 설정", expanded=False):
        repo_url = st.text_input("GitHub Repo URL", value=os.environ.get("REPO_URL", REPO_URL_DEFAULT))
        repo_dir = st.text_input("로컬 캐시 폴더", value=os.environ.get("REPO_CACHE_DIR", "repo_cache"))
        colA, colB, colC = st.columns(3)
        with colA:
            sync = st.button("🔄 저장소 동기화 (clone/pull)")
        with colB:
            reset_index = st.button("🧹 인덱스 재생성")
        with colC:
            show_stats = st.checkbox("문서 통계 보기", value=False)

        status_box = st.empty()
        if sync:
            ok, msg = clone_or_update_repo(repo_url, repo_dir)
            status_box.info(msg)
            if ok:
                st.cache_data.clear()
                st.cache_resource.clear()
                st.session_state.vector_ready = False

        corpus = load_repo_corpus(repo_dir)
        if show_stats:
            st.write(f"문서 청크 수: {len(corpus)}")
            sample_paths = sorted(list({c['path'] for c in corpus}))[:20]
            st.write("예시 파일:", sample_paths)

        if (not st.session_state.vector_ready) and corpus:
            vectorizer, X = build_vector_store(corpus)
            st.session_state.vectorizer = vectorizer
            st.session_state.X = X
            st.session_state.corpus = corpus
            st.session_state.vector_ready = True
            status_box.success("✅ 인덱스가 준비되었습니다.")

        if reset_index:
            st.cache_resource.clear()
            if corpus:
                vectorizer, X = build_vector_store(corpus)
                st.session_state.vectorizer = vectorizer
                st.session_state.X = X
                st.session_state.corpus = corpus
                st.session_state.vector_ready = True
                status_box.success("🔁 인덱스를 재생성했습니다.")

    # 채팅 UI
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "무엇을 도와드릴까요? 예) '정제포도당 CCP 알려줘', 'GIS703 용도'"}]

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    query = st.chat_input("질문을 입력하세요")
    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("검색 중입니다...")
            # 1) 규칙 기반(고정 멘트) 우선 적용
            rule_answer = get_rule_based_answer(query)
            if rule_answer:
                placeholder.markdown(rule_answer)
                st.session_state.messages.append({"role": "assistant", "content": rule_answer})
            else:
                corpus = st.session_state.get("corpus", [])
                vectorizer = st.session_state.get("vectorizer", None)
                X = st.session_state.get("X", None)

                hits = retrieve(query, vectorizer, X, corpus, topk=6) if corpus else []
                answer = synthesize_answer(query, hits)
                # 결과 렌더
                placeholder.markdown(answer, unsafe_allow_html=True)
                if hits:
                    with st.expander("🔎 참조 문서 (상위 6개)"):
                        for h in hits:
                            score_txt = f" | score={h.get('score', 0):.3f}" if "score" in h else ""
                            st.markdown(f"**{h['path']}** (chunk #{h['chunk_id']}){score_txt}")
                            st.code(h["text"][:800])

                st.session_state.messages.append({"role": "assistant", "content": answer})
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧻 대화 초기화"):
            st.session_state.messages = [{"role": "assistant", "content": "무엇을 도와드릴까요?"}]
            st.experimental_rerun()
    with col2:
        st.caption("※ 고급 요약/생성은 OPENAI_API_KEY 연동 후 확장 가능")

# =====================================
# 페이지: 제품백서
# =====================================
def page_whitepaper():
    st.title("📘 제품백서 전용")
    df = load_product_df()

    with st.expander("📋 전제품 목록", expanded=False):
        if not df.empty:
            st.dataframe(df[["계층구조_2레벨","계층구조_3레벨","제품코드","제품명"]].dropna().reset_index(drop=True), use_container_width=True)
        else:
            st.info("product_data.csv 를 프로젝트 루트에 두면 목록이 표시됩니다.")

    st.markdown("---")
    st.markdown('<h4>🔍 <b>제품코드 또는 제품명을 입력하세요</b></h4>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        q1 = st.text_input("🔎 제품 1 (예: GIB1010 또는 글루텐피드)")
    with col2:
        q2 = st.text_input("🔎 제품 2 (예: GIS7030 또는 물엿)")
    queries = [q for q in [q1, q2] if q]

    if queries and not df.empty:
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
            cols = st.columns(min(3, len(results)))
            idx = 0
            for _, row in results.iterrows():
                with cols[idx % len(cols)]:
                    product_card(row)
                idx += 1
    elif not queries:
        st.info("제품코드 또는 제품명을 입력해주세요.")

# =====================================
# 사이드바 내비
# =====================================
with st.sidebar:
    st.markdown(f"### {APP_TITLE}")
    st.caption(PROJECT_SUBTITLE)
    sel = st.radio(
        "섹션",
        ["💬 챗봇", "📘 제품백서"],
        index=0 if st.session_state.route == "CHAT" else 1,
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.caption("© Internal Use Only")

if sel.startswith("💬"):
    st.session_state.route = "CHAT"
    page_chatbot()
else:
    st.session_state.route = "WHITEPAPER"
    page_whitepaper()
