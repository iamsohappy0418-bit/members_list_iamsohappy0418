import re
from flask import Flask, request, jsonify, redirect



def guess_intent(text: str) -> str:
    """
    자연어 문장에서 intent 추측
    - 단문은 무조건 조회 처리 (특히 회원번호/회원명)
    """
    text = (text or "").strip()

    # ✅ 1. 단문 패턴: 회원 조회 우선
    # - 회원명 (한글 2~4자)
    if re.fullmatch(r"[가-힣]{2,4}", text):
        return "member_find_auto"

    # - 회원번호 (숫자 5~8자리)
    if re.fullmatch(r"\d{5,8}", text):
        return "member_find_auto"

    # - 휴대폰 번호
    if re.fullmatch(r"\d{3}-\d{3,4}-\d{4}", text):
        return "member_find_auto"

    # - 코드 A 형태
    if re.fullmatch(r"코드\s*[A-Za-z0-9]+", text):
        return "member_find_auto"

    # ✅ 2. 주문/수당 맥락 키워드 포함된 경우
    if "주문" in text:
        return "order_find_auto"
    if "후원수당" in text:
        return "commission_find_auto"

    # ✅ 3. 메모/일지 관련
    if any(k in text for k in ["상담일지", "개인일지", "활동일지", "메모"]):
        return "memo_find_auto"

    # ✅ 4. 회원 키워드
    if "회원" in text:
        return "member_find_auto"

    return "unknown"




