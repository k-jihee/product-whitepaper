def get_rule_based_answer(query: str) -> str | None:
    """
    특정 질문에 대해 RAG를 거치지 않고 고정 답변만 반환.
    일치/유사 키워드가 충분하면 해당 답을 리턴, 아니면 None
    """
    if not query:
        return None

    q = query.lower().strip()

    # 이 질문을 가리키는 핵심 키워드(조합은 자유롭게 더 추가 가능)
    keywords = [
        "정제포도당", "외기", "공기", "배출", "어디", "점검",
        "s/d", "r/d", "백필터", "스크러버", "순환수", "bx"
    ]

    hit = sum(1 for k in keywords if k in q)
    if ("정제포도당" in q and "배출" in q and ("외기" in q or "공기" in q)) or hit >= 4:
        return (
            "정제포도당 생산 설비에서 정제포도당이 외기로 공기와 함께 배출되는 경우, 다음 개소를 점검하세요.\n\n"
            "1) **S/D 배기 덕트에서 분진 비산 시**\n"
            "   - 스크러버 중단부에 위치하는 **노즐 막힘 여부** 및 **순환수 Bx** 확인\n"
            "   - 점검 이력 : **25년 3월 점검 이력 有 → 과거 패턴 분석 시 6개월 주기 점검 필요**\n"
            "   - 순환수 관리기준 : **Bx 3.0 이하**\n\n"
            "2) **R/D 또는 진동냉각기 배기 덕트에서 분진 비산 시**\n"
            "   - **R/D 백필터 점검 및 교체**\n"
            "   - **진동냉각기 백필터 점검 및 교체**"
        )
    return None


# 예시로 Chatbot 내에서 사용하는 코드 블록 삽입 예시
def page_chatbot():
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
                return  # 아래 RAG 로직 건너뜀

            # 이하 기존 RAG 검색/응답 로직 유지
