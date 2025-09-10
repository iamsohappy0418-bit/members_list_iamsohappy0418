import sys
import os
import pytest

# ✅ 프로젝트 루트 경로 추가 (app.py import 가능하도록)
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import nlu_to_pc_input


# -------------------------------
# 테스트 케이스 모음
# -------------------------------
cases = [
    # --- 회원 검색 ---
    ("코드a", {"intent": "search_member", "query": {"코드": "코드A"}}, "member_code"),
    ("홍길동 회원", {"intent": "search_member", "query": {"회원명": "홍길동"}}, "member_name_with_keyword"),
    ("12345678", {"intent": "search_member", "query": {"회원번호": "12345678"}}, "member_number"),
    ("010-1234-5678", {"intent": "search_member", "query": {"휴대폰번호": "010-1234-5678"}}, "member_phone"),
    ("특수번호 aa668800@", {"intent": "search_member", "query": {"특수번호": "aa668800@"}}, "member_special"),
    ("강소희", {"intent": "search_member", "query": {"회원명": "강소희"}}, "member_simple"),

    # --- 회원 등록/삭제/저장 ---
    ("회원등록 홍길동 번호 12345678",
     {"intent": "register_member", "query": {"raw_text": "회원등록 홍길동 번호 12345678"}}, "register"),
    ("홍길동 회원 삭제", {"intent": "delete_member", "query": {"회원명": "홍길동"}}, "delete_with_keyword"),
    ("이수민 삭제", {"intent": "delete_member", "query": {"회원명": "이수민"}}, "delete_simple"),
    ("회원 저장 홍길동 전화번호 010-9999-8888",
     {"intent": "save_member", "query": {"raw_text": "회원 저장 홍길동 전화번호 010-9999-8888"}}, "save_member"),

    # --- 주문 ---
    ("홍길동 주문", {"intent": "order_auto", "query": {"주문회원": "홍길동"}}, "order_with_name"),
    ("주문 저장", {"intent": "order_auto", "query": {"주문": True}}, "order_simple"),
    ("이수민 주문 노니 2개 카드 결제",
     {"intent": "order_auto", "query": {"주문회원": "이수민"}}, "order_complex"),  # 현재는 단순 회원명 추출까지만 확인

    # --- 메모 저장 ---
    ("이태수 상담일지 저장 오늘 출근합니다",
     {"intent": "memo_add", "query": {"회원명": "이태수", "일지종류": "상담일지", "내용": "오늘 출근합니다"}}, "memo_add_sangdam"),
    ("김영희 개인일지 저장 오늘 기분이 좋습니다",
     {"intent": "memo_add", "query": {"회원명": "김영희", "일지종류": "개인일지", "내용": "오늘 기분이 좋습니다"}}, "memo_add_personal"),
    ("박철수 활동일지 저장 운동 완료",
     {"intent": "memo_add", "query": {"회원명": "박철수", "일지종류": "활동일지", "내용": "운동 완료"}}, "memo_add_activity"),

    # --- 메모 검색 ---
    ("이태수 상담일지 검색 중국",
     {"intent": "memo_search", "query": {"회원명": "이태수", "일지종류": "상담일지", "검색어": "중국"}}, "memo_search_sangdam"),
    ("전체 메모 검색 중국",
     {"intent": "memo_search", "query": {"회원명": "전체", "일지종류": "전체", "검색어": "중국"}}, "memo_search_all"),

    # --- 후원수당 ---
    ("후원수당 전체 조회", {"intent": "commission_find", "query": {"raw_text": "후원수당 전체 조회"}}, "commission_find_all"),
    ("수당 내역", {"intent": "commission_find", "query": {"raw_text": "수당 내역"}}, "commission_find_simple"),

    # --- 알 수 없는 요청 ---
    ("알 수 없는 요청문", {"intent": "unknown", "query": {"raw_text": "알 수 없는 요청문"}}, "unknown_case"),
]


# -------------------------------
# 공통 테스트
# -------------------------------
@pytest.mark.parametrize("text,expected,case_id", cases, ids=[c[2] for c in cases])
def test_nlu_to_pc_input(text, expected, case_id):
    """nlu_to_pc_input 함수가 자연어를 올바르게 intent + query로 변환하는지 테스트"""
    result = nlu_to_pc_input(text)
    assert result["intent"] == expected["intent"]
    assert result["query"] == expected["query"]
