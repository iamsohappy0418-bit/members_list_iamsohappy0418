"""
utils/http.py
HTTP 요청 / 외부 API 연동 유틸
"""

import os
import requests
from typing import Any, Dict, Optional

# ==========================================================
# 환경변수 설정
# ==========================================================
DEFAULT_TIMEOUT = int(os.getenv("HTTP_DEFAULT_TIMEOUT", "30"))
MEMBERSLIST_API_URL = os.getenv("MEMBERSLIST_API_URL")
IMPACT_API_URL = os.getenv("IMPACT_API_URL")

# ==========================================================
# 예외 클래스
# ==========================================================
class MemberslistError(RuntimeError):
    """Memberslist API 호출 실패 예외"""
    pass

class ImpactError(Exception):
    """Impact API 호출 실패 예외"""
    pass

# ==========================================================
# 내부 유틸
# ==========================================================
def _normalize_timeout(t: Optional[int]) -> int:
    """타임아웃 정규화"""
    try:
        return int(t) if t is not None else DEFAULT_TIMEOUT
    except Exception:
        return DEFAULT_TIMEOUT

def _ensure_json_payload(payload: Any) -> Dict[str, Any]:
    """payload가 dict인지 확인"""
    if isinstance(payload, dict):
        return payload
    raise MemberslistError(f"payload는 dict여야 합니다. (got: {type(payload).__name__})")

def _post_json(url: str, payload: Dict[str, Any], timeout: Optional[int] = None) -> Dict[str, Any]:
    """POST JSON 요청"""
    p = _ensure_json_payload(payload)
    to = _normalize_timeout(timeout)
    r = requests.post(url, json=p, timeout=to)
    r.raise_for_status()
    try:
        return r.json()
    except ValueError:
        return {"ok": True, "raw": r.text}

# ==========================================================
# 외부 API 호출
# ==========================================================
def call_memberslist_add_orders(payload: Dict[str, Any], timeout: Optional[int] = None) -> Dict[str, Any]:
    """
    멤버리스트 API로 주문 데이터 전송
    - 기본 URL(환경변수 MEMBERSLIST_API_URL)에 먼저 요청
    - 404 발생 시 add_orders <-> addOrders 경로 자동 변환 후 재시도
    """
    if not MEMBERSLIST_API_URL:
        raise MemberslistError("MEMBERSLIST_API_URL 미설정")

    url = MEMBERSLIST_API_URL.rstrip("/")
    try:
        return _post_json(url, payload, timeout)
    except requests.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        if status == 404:
            if url.endswith("/add_orders"):
                fallback = url[:-len("/add_orders")] + "/addOrders"
            elif url.endswith("/addOrders"):
                fallback = url[:-len("/addOrders")] + "/add_orders"
            else:
                raise MemberslistError(f"404 Not Found: {url}") from e
            return _post_json(fallback, payload, timeout)

        detail = getattr(e.response, "text", str(e))
        raise MemberslistError(f"Memberslist HTTPError: {status} | {detail}") from e
    except requests.RequestException as e:
        raise MemberslistError(f"Memberslist RequestException: {e}") from e


def call_impact_sync(payload: dict):
    """
    Impact API로 데이터 동기화
    - 기본 URL: IMPACT_API_URL (예: /sync)
    - payload 예시: {"type": "order", "member": "...", "orders": [...], "source": "sheet_gpt"}
    """
    if not IMPACT_API_URL:
        raise ImpactError("IMPACT_API_URL 미설정")

    try:
        r = requests.post(IMPACT_API_URL, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise ImpactError(f"임팩트 API 요청 실패: {str(e)}")


