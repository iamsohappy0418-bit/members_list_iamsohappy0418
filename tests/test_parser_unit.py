import pytest
from parser import (
    guess_intent,
    preprocess_user_input,   # ← 여기로 교체
    parse_order_text,
    parse_request_and_update,
    # parse_memo 가 분리되어 있다면 여기 추가
)
from app import preprocess_member_query




# ────────────────────────────────
# guess_intent
# ────────────────────────────────
@pytest.mark.parametrize("query, expected", [
    ("회원검색 이태수", "search_member"),
    ("회원등록 홍길동", "register_member"),
    ("제품주문 저장", "order_save"),
    ("상담일지 저장", "memo_save"),
])

def test_guess_intent(query, expected):
    intent, _ = guess_intent(query)
    assert intent == expected




# ────────────────────────────────
# preprocess_member_query
# ────────────────────────────────
def test_preprocess_member_query():
    text = "회원검색 이태수"
    cleaned = preprocess_member_query(text)
    assert cleaned == "이태수"


# ────────────────────────────────
# parse_order_text
# ────────────────────────────────
def test_parse_order_text_basic():
    text = "이태수 제품주문 저장"
    result = parse_order_text(text)
    assert isinstance(result, dict)
    assert result.get("회원명") == "이태수"


# ────────────────────────────────
# parse_request_and_update
# ────────────────────────────────
def test_parse_request_and_update_multi_fields():
    text = "이태수 주소 서울로 변경, 전화번호 010-1234-5678"
    result = parse_request_and_update(text)
    assert result["회원명"] == "이태수"
    assert result["fields"]["주소"] == "서울"
    assert result["fields"]["휴대폰번호"] == "010-1234-5678"


# ────────────────────────────────
# parse_memo (있다면)
# ────────────────────────────────
def test_parse_memo_basic():
    from parser.parse import parse_memo
    text = "이태수 상담일지 저장 오늘은 좋은 날씨"
    member, sheet, content = parse_memo(text)
    assert member == "이태수"
    assert sheet == "상담일지"
    assert "오늘은 좋은 날씨" in content



def test_preprocess_user_input_save():
    text = "이태수 상담일지 저장 오늘은 좋은 날씨"
    result = preprocess_user_input(text)

    assert result["member_name"] == "이태수"
    assert result["diary_type"] == "상담일지"
    assert result["action"] == "저장"
    assert result["keyword"] == "오늘은 좋은 날씨"
    assert "저장" in result["query"]


def test_preprocess_user_input_search_with_option():
    text = "홍길동 개인일지 검색 전체"
    result = preprocess_user_input(text)

    assert result["member_name"] == "홍길동"
    assert result["diary_type"] == "개인일지"
    assert result["action"] == "검색"
    assert result["options"].get("full_list") is True
    assert "전체" not in result["keyword"]



