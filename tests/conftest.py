import pytest
from datetime import datetime
from utils import now_kst

@pytest.fixture
def unique_member_number():
    """
    항상 고유한 회원번호를 생성해 반환
    - timestamp 기반으로 생성 (충돌 방지)
    """
    return f"9{int(datetime.now().timestamp())}"

@pytest.fixture
def today_date():
    """
    오늘 날짜 (YYYY-MM-DD 형식)
    """
    return now_kst().strftime("%Y-%m-%d")

def assert_contains(results, key, value):
    """
    검색 결과 리스트에서 특정 key에 value가 포함되어 있는지 확인
    """
    assert any(str(r.get(key, "")) == str(value) for r in results), \
        f"❌ {key}={value} 가 results에 없음: {results}"

def assert_not_contains(results, key, value):
    """
    검색 결과 리스트에서 특정 key에 value가 포함되어 있지 않은지 확인
    """
    assert all(str(r.get(key, "")) != str(value) for r in results), \
        f"❌ {key}={value} 가 results에 남아있음: {results}"
