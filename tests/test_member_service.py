import pytest
from service import (
    register_member_internal,
    find_member_internal,
    update_member_internal,
    delete_member_internal,
)
from utils import now_kst

from datetime import datetime



def test_member_lifecycle():
    name = "테스트회원"
    number = f"9{int(datetime.now().timestamp())}"  # 항상 고유 번호
    phone = "010-1234-7777"

    # 1. 등록
    result = register_member_internal(name, number, phone)
    assert result["status"] in ("created", "exists")
    assert result["data"]["회원명"] == name
    assert result["data"]["회원번호"] == number
    assert result["data"]["휴대폰번호"] == phone

    # 2. 조회
    results = find_member_internal(name=name)
    assert any(r.get("회원명") == name for r in results)

    # 3. 수정
    updates = {"주소": "서울특별시 강남구"}
    update_result = update_member_internal(
        요청문=f"{name} 주소를 서울특별시 강남구로 수정",
        회원명=name,
        필드="주소",
        값="서울특별시 강남구"
    )
    assert update_result["status"] == "success"

    # 수정 확인
    results = find_member_internal(name=name)
    assert any(r.get("주소") == "서울특별시 강남구" for r in results)

    # 4. 삭제
    delete_result, http_status = delete_member_internal(name)
    assert http_status in (200, 404)

    # 삭제 확인
    results = find_member_internal(name=name)
    assert not any(r.get("회원명") == name for r in results)







from service import register_member_internal, find_member, delete_member
from tests.conftest import assert_contains, assert_not_contains

def test_member_lifecycle(unique_member_number):
    name = "테스트회원"
    number = unique_member_number
    phone = "010-1234-5678"

    # 1. 등록
    result = register_member_internal(name, number, phone)
    assert result["status"] in ("created", "exists")

    # 2. 조회
    found = find_member(name)
    assert_contains(found, "회원명", name)

    # 3. 삭제
    delete_member(name)
    found_after = find_member(name)
    assert_not_contains(found_after, "회원명", name)



