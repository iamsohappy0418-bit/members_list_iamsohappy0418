import sys
import os
import pytest

# ✅ 프로젝트 루트를 PYTHONPATH에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app  # app.py 모듈
from flask.testing import FlaskClient


@pytest.fixture
def client() -> FlaskClient:
    """Flask 테스트 클라이언트 생성"""
    app.app.config["TESTING"] = True
    return app.app.test_client()


def test_home(client: FlaskClient):
    """헬스체크 엔드포인트 확인"""
    rv = client.get("/")
    assert rv.status_code == 200
    assert "Flask 서버가 실행 중" in rv.get_data(as_text=True)


def test_openapi(client: FlaskClient):
    """OpenAPI 스펙 반환 확인"""
    rv = client.get("/openapi.json")
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, dict)
    assert "paths" in data  # OpenAPI 스펙 구조 검증


def test_guess_intent_search_member(client: FlaskClient):
    """guess_intent 엔드포인트에서 회원검색 intent 추출"""
    payload = {"query": "회원검색 이태수"}
    rv = client.post("/guess_intent", json=payload)
    assert rv.status_code == 200
    data = rv.get_json()
    assert "status" in data
    assert data["status"] == "success" or "intent" in data


def test_post_intent_member_select(client: FlaskClient):
    """postIntent → member_select intent 처리"""
    payload = {"text": "이태수 전체정보"}
    rv = client.post("/postIntent", json=payload)
    assert rv.status_code in (200, 400)  # 데이터 없으면 400, 있으면 200
    data = rv.get_json()
    assert "status" in data


def test_member_route(client: FlaskClient):
    """member 엔드포인트 기본 동작 확인"""
    payload = {"query": "이태수"}
    rv = client.post("/member", json=payload)
    assert rv.status_code in (200, 400)
    data = rv.get_json()
    assert "status" in data


def test_memo_route(client: FlaskClient):
    """memo 엔드포인트 기본 동작 확인"""
    payload = {"query": "이태수 상담일지 저장 오늘은 좋은 날씨"}
    rv = client.post("/memo", json=payload)
    assert rv.status_code in (200, 400)
    data = rv.get_json()
    assert "status" in data


def test_order_route(client: FlaskClient):
    """order 엔드포인트 기본 동작 확인"""
    payload = {"query": "이태수 제품주문 저장"}
    rv = client.post("/order", json=payload)
    assert rv.status_code in (200, 400)
    data = rv.get_json()
    assert "status" in data


def test_commission_route(client: FlaskClient):
    """commission 엔드포인트 기본 동작 확인"""
    payload = {"query": "이태수 후원수당 조회"}
    rv = client.post("/commission", json=payload)
    assert rv.status_code in (200, 400)
    data = rv.get_json()
    assert "status" in data
