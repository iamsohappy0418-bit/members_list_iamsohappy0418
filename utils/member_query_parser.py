import re
from flask import request, Response, jsonify
from utils.sheets import get_member_sheet


# --------------------------------------------------
# 📌 입력값 → 필드 자동 판별
# --------------------------------------------------
def infer_member_field(value: str) -> str:
    """
    입력값으로부터 필드명을 추론
    - 010 시작 → 휴대폰번호
    - 숫자만 → 회원번호
    - 그 외 → 회원명
    """
    if not value:
        return "회원명"

    v = value.strip()

    # 휴대폰번호
    if re.match(r"^01[016789]-?\d{3,4}-?\d{4}$", v):
        return "휴대폰번호"

    # 회원번호 (숫자 4~10자리)
    if re.match(r"^\d{4,10}$", v):
        return "회원번호"

    # 기본은 회원명
    return "회원명"


# --------------------------------------------------
# 📌 자연어 → 조건 추출
# --------------------------------------------------
def parse_natural_query_multi(text: str):
    """
    자연어에서 여러 (필드, 키워드) 추출
    - "코드 a 계보도 장천수" → [("코드","A"),("계보도","장천수")]
    - "회원명 이태수" → [("회원명","이태수")]
    - "이태수" → [("회원명","이태수")]
    - "회원번호 22366" → [("회원번호","22366")]
    - "22366" → [("회원번호","22366")]
    - "휴대폰번호 010-1234-5678" → [("휴대폰번호","010-1234-5678")]
    - "010-1234-5678" → [("휴대폰번호","010-1234-5678")]
    """
    if not text:
        return []

    valid_fields = [
        "회원명", "회원번호", "휴대폰번호", "특수번호", "코드", "계보도", "분류",
        "가입일자", "생년월일", "통신사", "친밀도", "근무처", "소개한분",
        "카드사", "카드주인", "카드번호", "유효기간", "카드생년월일",
        "회원단계", "연령/성별", "직업", "가족관계",
        "니즈", "애용제품", "콘텐츠", "습관챌린지",
        "비즈니스시스템", "GLC프로젝트", "리더님"
    ]

    tokens = text.strip().split()
    results = []
    i = 0
    while i < len(tokens):
        token = tokens[i]

        # ✅ case1: 명시적 필드 + 값
        if token in valid_fields and i + 1 < len(tokens):
            keyword = tokens[i + 1]

            # 코드 값은 항상 대문자로 통일
            if token == "코드":
                keyword = keyword.upper()

            results.append((token, keyword))
            i += 2
            continue

        # ✅ case2: 단일 값만 들어온 경우
        if len(tokens) == 1:
            # 휴대폰번호 판별
            if token.startswith("010"):
                results.append(("휴대폰번호", token))
            # 숫자 → 회원번호
            elif token.isdigit():
                results.append(("회원번호", token))
            # 한글 이름 추정
            elif 2 <= len(token) <= 10 and all("가" <= ch <= "힣" for ch in token):
                results.append(("회원명", token))
            else:
                # fallback → infer_member_field 사용
                field = infer_member_field(token)
                results.append((field, token))
            i += 1
            continue

        i += 1

    return results



