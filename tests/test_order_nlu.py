import sys, os, pytest
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from parser.parse import parse_order_text

@pytest.mark.parametrize("text,expected", [
    (
        "이수민 주문 노니 2개 카드 결제 오늘",
        {
            "회원명": "이수민",
            "제품명": "노니",
            "수량": 2,
            "결제방법": "카드",
            "배송처": "",
            "주문일자": "2025-09-11",  # 실행일 기준 (오늘)
        },
    ),
    (
        "박철수 주문 홍삼 3박스 현금 결제 서울 주소",
        {
            "회원명": "박철수",
            "제품명": "홍삼",
            "수량": 3,
            "결제방법": "현금",
            "배송처": "서울",
        },
    ),
    (
        "김영희 주문 애터미칫솔 1병 계좌이체 내일",
        {
            "회원명": "김영희",
            "제품명": "애터미칫솔",
            "수량": 1,
            "결제방법": "계좌이체",
            "주문일자": "2025-09-12",  # 실행일 기준 (내일)
        },
    ),
    (
        "홍길동 주문 비타민 주소: 부산 카드",
        {
            "회원명": "홍길동",
            "제품명": "비타민",
            "수량": 1,  # 기본값
            "결제방법": "카드",
            "배송처": "부산",
        },
    ),
])
def test_parse_order_text(text, expected):
    """고급 주문 파서 parse_order_text 동작 확인"""
    result = parse_order_text(text)

    # intent 항상 order_auto
    assert result["intent"] == "order_auto"

    # 필수 키 확인
    for key, val in expected.items():
        assert result["query"].get(key) == val
