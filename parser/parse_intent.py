import re

# -------------------------------
# intent 규칙 정의
# -------------------------------
INTENT_RULES = {
    # 회원 관련
    ("회원", "검색"): "search_member",
    ("회원", "조회"): "search_member",   # ✅ 조회도 검색과 동일 처리
    ("회원", "등록"): "register_member",
    ("회원", "추가"): "register_member",
    ("회원", "수정"): "update_member",
    ("회원", "저장"): "save_member",
    ("회원", "삭제"): "delete_member",
    ("회원", "탈퇴"): "delete_member",
    ("코드", "검색"): "search_by_code_logic",

    # ✅ 회원 선택 관련 추가
    ("전체정보",): "member_select",
    ("상세정보",): "member_select",
    ("상세",): "member_select",
    ("종료",): "member_select",
    ("끝",): "member_select",


    # 메모/일지 관련
    ("일지", "저장"): "memo_add",
    ("상담일지", "추가"): "add_counseling",
    ("일지", "검색"): "memo_search",
    ("일지", "조회"): "memo_find",
    ("검색", "자연어"): "search_memo_from_text",
    ("일지", "자동"): "memo_find_auto",

    # 주문 관련
    ("주문", "자동"): "order_auto",
    ("주문", "업로드"): "order_upload",
    ("주문", "자연어"): "order_nl",
    ("주문", "저장"): "save_order_proxy",

    # 후원수당 관련
    ("수당", "찾기"): "commission_find",
    ("수당", "자동"): "commission_find_auto",
    ("수당", "자연어"): "search_commission_by_nl",
}




def guess_intent(query: str) -> str:
    """
    단순 규칙 기반 intent 추출
    """
    query = (query or "").strip()

    # 1. 일반 규칙 검사
    for keywords, intent in INTENT_RULES.items():
        if all(kw in query for kw in keywords):
            return intent

    # 2. 회원명 단독 입력 (한글 2~4자) → 자동 조회
    import re
    if re.fullmatch(r"[가-힣]{2,4}", query):
        return "search_member"

    return "unknown"









# -------------------------------
# 전처리 함수
# -------------------------------

DIARY_TYPES = ["개인일지", "상담일지", "활동일지"]

def preprocess_user_input(user_input: str) -> dict:
    """
    사용자 입력 전처리
    - 회원명, 일지종류, 액션(검색/저장/수정) 추출
    - 불필요한 토큰 제거 후 query 재구성
    - 옵션(full_list 등) 감지
    """
    import re

    member_name = None
    diary_type = None
    action = None
    keyword = None
    options = {}

    # 1. 회원명 추출 (2~4자 한글 이름 감지)
    m = re.fullmatch(r"[가-힣]{2,4}", user_input.strip())
    if m:
        member_name = m.group(0)

    # 2. 일지 종류 추출
    for dtype in DIARY_TYPES:
        if dtype in user_input:
            diary_type = dtype
            break

    # 3. 동작(action) 추출
    if "검색" in user_input:
        action = "검색"
    elif "저장" in user_input:
        action = "저장"
    elif "수정" in user_input:
        action = "수정"

    # 4. 옵션 파싱
    if "전체목록" in user_input or "전체" in user_input:
        options["full_list"] = True

    # 5. 검색 키워드 추출
    exclude_tokens = filter(None, [member_name, diary_type, action, "전체목록", "전체"])
    keyword_tokens = [word for word in user_input.split() if word not in exclude_tokens]
    keyword = " ".join(keyword_tokens).strip()

    # 6. query 재구성
    query_parts = []
    if member_name:
        query_parts.append(member_name)
    if diary_type:
        query_parts.append(diary_type)
    if action:
        query_parts.append(action)
    if keyword:
        query_parts.append(keyword)

    final_query = " ".join(query_parts)

    return {
        "query": final_query,
        "options": options
    }

