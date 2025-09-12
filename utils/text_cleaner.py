import re

# ======================================================================================
# ✅ 꼬리 명령어 정제
# ======================================================================================
def clean_tail_command(text: str) -> str:
    """
    요청문 끝에 붙은 불필요한 꼬리 명령어 제거
    - 조사("로", "으로")와 함께 붙은 경우도 제거
    - 흔한 명령형 꼬리 ("수정해줘", "변경", "바꿔줘", "해주세요" 등) 처리
    """
    if not text:
        return text
    s = text.strip()

    tail_phrases = [
        "정확히 수정해줘", "수정해줘", "변경해줘", "바꿔줘",
        "수정", "변경", "바꿔", "삭제",
        "저장해줘", "기록", "입력", "해주세요", "해줘", "남겨"
    ]
    for phrase in tail_phrases:
        pattern = rf"(?:\s*(?:으로|로))?\s*{re.escape(phrase)}\s*[^\w가-힣]*$"
        s = re.sub(pattern, "", s)
    return s.strip()


# ======================================================================================
# ✅ 값 정제 (조사/불필요 기호 제거)
# ======================================================================================
def clean_value_expression(text: str) -> str:
    """
    값에 붙은 조사/불필요한 문자/꼬리 명령어 제거
    - "서울로" → "서울"
    - "010-1111-2222번" → "010-1111-2222"
    - "12345," → "12345"
    - "주소 서울 수정해 줘" → "주소 서울"
    """
    if not text:
        return text
    s = text.strip()

    # 1) 일반적인 조사 제거
    s = re.sub(r"(으로|로|으로의|로의|으로부터|로부터|은|는|이|가|을|를|와|과|에서|에)$", "", s)

    # 2) 자주 나오는 꼬리 명령어 제거
    particles = ['값을', '수정해 줘', '수정해줘', '변경해 줘', '변경해줘', '삭제해 줘', '삭제해줘']
    for p in particles:
        pattern = rf'({p})\s*$'
        s = re.sub(pattern, '', s)

    # 3) 불필요한 기호 제거
    s = s.strip(" ,.")

    return s


# ======================================================================================
# ✅ 본문 정제 (회원명/불필요 단어 제거)
# ======================================================================================


def clean_content(text: str, member_name: str = None) -> str:
    """
    메모/요청문에서 불필요한 기호, 회원명 등을 제거한 정제 문자열 반환
    """
    if not text:
        return ""

    # 불필요한 앞뒤 기호 제거
    s = text.strip(" \t:：,，.'\"“”‘’")

    # 회원명 + 선택적 '님' + 기호 제거 (예: "이태수.", "이태수 .", "이태수님," → "")
    if member_name:
        pattern = rf"{re.escape(member_name)}\s*(님)?\s*[:：,，.]*"
        s = re.sub(pattern, "", s)

    return s.strip()




# utils/text_cleaner.py

def build_member_query(user_input: str) -> dict:
    """
    자연어 입력을 API용 JSON 쿼리로 변환합니다.
    불필요한 조사/단어를 제거하여 핵심 키워드만 남깁니다.
    예: "코드가 A인 회원" -> { "query": "코드 A 회원" }
    """
    replacements = [
        ("가 ", " "), ("이 ", " "), ("은 ", " "), ("는 ", " "),
        ("인 ", " "), ("중 ", " "), ("명단", ""), ("사람", "회원"),
    ]
    query = user_input
    for old, new in replacements:
        query = query.replace(old, new)

    query = " ".join(query.split())  # 불필요한 공백 제거
    return {"query": query}




def normalize_code_query(text: str) -> str:
    """
    코드 검색용 query 정규화
    - 코드a, 코드 A, 코드: b, 코드 :C, 코드aa → 코드A, 코드B, 코드C, 코드AA
    """
    if not text:
        return ""
    match = re.search(r"코드\s*[:：]?\s*([a-zA-Z]+)", text, re.IGNORECASE)
    if match:
        return f"코드{match.group(1).upper()}"
    return text.strip()





# utils/text_cleaner.py
def clean_member_query(text: str) -> str:
    """
    회원 관련 요청문에서 불필요한 액션 단어 제거
    (조회/검색/등록/수정/삭제/탈퇴/추가 등)
    """
    if not isinstance(text, str):
        return ""

    original = text.strip()
    cleaned = original

    tokens_to_remove = [
        "회원조회", "회원 조회", "회원검색", "회원 검색", "조회", "검색",
        "회원수정", "회원 수정", "수정",
        "회원삭제", "회원 삭제", "삭제", "탈퇴",
        "회원등록", "회원 등록", "회원추가", "회원 추가", "등록", "추가"
    ]

    removed_tokens = []
    for token in tokens_to_remove:
        if token in cleaned:
            cleaned = cleaned.replace(token, "").strip()
            removed_tokens.append(token)

    # ✅ 디버그 로그 출력
    if removed_tokens:
        print(f"[clean_member_query] 원문: '{original}'")
        print(f"[clean_member_query] 제거된 토큰: {removed_tokens}")
        print(f"[clean_member_query] 최종 query: '{cleaned}'")

    return cleaned




