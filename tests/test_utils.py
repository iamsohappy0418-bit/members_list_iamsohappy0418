import pytest
from datetime import datetime, timedelta

from utils import (
    # 날짜/시간
    now_kst, process_order_date, parse_dt,

    # 문자열
    remove_josa, remove_spaces, split_to_parts,
    clean_tail_command, clean_value_expression, clean_content,
    build_member_query, normalize_code_query, clean_member_query,

    # 검색
    normalize_query, fallback_natural_search, infer_member_field, parse_natural_query_multi,
)


# =====================================================================================
# 날짜/시간 유틸
# =====================================================================================
def test_now_kst():
    now = now_kst()
    assert now.tzinfo is not None
    assert now.utcoffset().total_seconds() == 9 * 3600  # KST (+9h)


def test_process_order_date_keywords():
    today = datetime.now().strftime("%Y-%m-%d")
    assert process_order_date("오늘") == today

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    assert process_order_date("어제") == yesterday

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    assert process_order_date("내일") == tomorrow


def test_process_order_date_formats():
    assert process_order_date("2025-09-14") == "2025-09-14"
    assert process_order_date("2025.09.14") == "2025-09-14"
    assert process_order_date("2025/09/14") == "2025-09-14"


def test_parse_dt():
    assert parse_dt("2025-09-14") == datetime(2025, 9, 14)
    assert parse_dt("2025/09/14") == datetime(2025, 9, 14)
    assert parse_dt("2025.09.14") == datetime(2025, 9, 14)
    assert parse_dt("2025-09-14 12:30") == datetime(2025, 9, 14, 12, 30)
    assert parse_dt("잘못된날짜") is None


# =====================================================================================
# 문자열 처리 유틸
# =====================================================================================
def test_remove_josa():
    assert remove_josa("사람이") == "사람"
    assert remove_josa("학교로") == "학교"


def test_remove_spaces():
    assert remove_spaces("010 - 1234 - 5678") == "010-1234-5678"


def test_split_to_parts():
    assert split_to_parts("이태수 회원 등록") == ["이태수", "회원", "등록"]


def test_clean_tail_command():
    assert clean_tail_command("주소 서울 수정해줘") == "주소 서울"


def test_clean_value_expression():
    assert clean_value_expression("서울로") == "서울"
    assert clean_value_expression("010-1234-5678번") == "010-1234-5678"


def test_clean_content():
    assert clean_content("이태수님, 오늘 상담했습니다", member_name="이태수") == "오늘 상담했습니다"


def test_build_member_query():
    result = build_member_query("코드가 A인 회원")
    assert result == {"query": "코드 A 회원"}


def test_normalize_code_query():
    assert normalize_code_query("코드a") == "코드A"
    assert normalize_code_query("코드 : b") == "코드B"


def test_clean_member_query():
    cleaned = clean_member_query("회원조회 이태수")
    assert "이태수" in cleaned
    assert "조회" not in cleaned


# =====================================================================================
# 검색 / 파서 유틸
# =====================================================================================
def test_normalize_query():
    assert normalize_query("코드a!!") == "코드A"


def test_fallback_natural_search():
    assert fallback_natural_search("010-1234-5678") == {"휴대폰번호": "010-1234-5678"}
    assert fallback_natural_search("12345") == {"회원번호": "12345"}
    assert fallback_natural_search("이태수") == {"회원명": "이태수"}


def test_infer_member_field():
    assert infer_member_field("010-1111-2222") == "휴대폰번호"
    assert infer_member_field("123456") == "회원번호"
    assert infer_member_field("이태수") == "회원명"


def test_parse_natural_query_multi():
    assert ("회원명", "이태수") in parse_natural_query_multi("이태수")
    assert ("코드", "A") in parse_natural_query_multi("코드 a")
    assert ("회원번호", "22366") in parse_natural_query_multi("22366")
    assert ("휴대폰번호", "010-1234-5678") in parse_natural_query_multi("010-1234-5678")



