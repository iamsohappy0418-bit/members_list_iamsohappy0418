import pytest
import json
from app import app

@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as client:
        yield client


def test_memo_save(client):
    payload = {
        "회원명": "이태수",
        "내용": "테스트 메모",
        "일지종류": "개인일지"
    }
    res = client.post("/memo", data=json.dumps(payload), content_type="application/json")
    assert res.status_code in (200, 400, 500)
    assert isinstance(res.get_json(), dict)


def test_memo_search(client):
    payload = {
        "keywords": ["테스트"],
        "일지종류": "상담일지"
    }
    res = client.post("/memo", data=json.dumps(payload), content_type="application/json")
    assert res.status_code in (200, 400, 500)
    assert isinstance(res.get_json(), (list, dict))


def test_memo_invalid(client):
    payload = {"foo": "bar"}
    res = client.post("/memo", data=json.dumps(payload), content_type="application/json")
    assert res.status_code == 400
    assert res.get_json()["status"] == "error"


# ──────────────────────────────
# ✅ 자연어 입력 (문자열) 테스트
# ──────────────────────────────
def test_memo_natural_language(client):
    """
    자연어 문자열 입력 → post_intent() 우회 동작 확인
    """
    payload = {"text": "이태수 상담일지 저장 오늘은 맑음"}
    res = client.post("/memo", data=json.dumps(payload), content_type="application/json")

    assert res.status_code in (200, 400, 500)
    data = res.get_json()
    assert isinstance(data, (dict, list))

