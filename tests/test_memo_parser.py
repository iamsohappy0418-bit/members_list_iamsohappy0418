import pytest
from parser import parse_memo   # ✅ parser/__init__.py 에서 바로 import 가능


def test_parse_memo_basic():
    text = "이태수 상담일지 저장 오늘은 날씨가 맑다"
    result = parse_memo(text)

    # 최소한 dict 반환 여부 검증
    assert isinstance(result, dict)
    assert "회원명" in result
    assert "내용" in result
    assert "일지종류" in result


def test_parse_memo_with_personal_log():
    text = "강소희 개인일지 저장 오늘은 부산에 다녀왔다"
    result = parse_memo(text)

    assert isinstance(result, dict)
    assert result.get("회원명") == "강소희"
    assert result.get("일지종류") == "개인일지"
    assert "부산" in result.get("내용", "")


def test_parse_memo_with_activity_log():
    text = "홍길동 활동일지 저장 세미나 참석"
    result = parse_memo(text)

    assert isinstance(result, dict)
    assert result.get("회원명") == "홍길동"
    assert result.get("일지종류") == "활동일지"
    assert "세미나" in result.get("내용", "")










from service import save_memo, find_memo, search_in_sheet
from tests.conftest import assert_contains

def test_memo_lifecycle(today_date):
    member = "테스트회원"
    content = "pytest 메모 저장 테스트"

    # 1. 저장
    save_memo("상담일지", member, content)

    # 2. 검색 (간단 검색)
    results = find_memo("pytest", "상담일지")
    assert_contains(results, "내용", content)

    # 3. 고급 검색 (기간 제한)
    advanced_results, has_more = search_in_sheet(
        "상담일지",
        keywords=["pytest"],
        start_date=today_date,
        end_date=today_date
    )
    assert_contains(advanced_results, "내용", content)

