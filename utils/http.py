# utils/http.py
import os
import requests
from typing import Any, Dict, Optional

DEFAULT_TIMEOUT = int(os.getenv("HTTP_DEFAULT_TIMEOUT", "30"))
MEMBERSLIST_API_URL = os.getenv("MEMBERSLIST_API_URL")

class MemberslistError(RuntimeError):
    """Memberslist API 호출 실패 예외"""
    pass

def _post_json(url: str, payload: Dict[str, Any], timeout: Optional[int] = None) -> Dict[str, Any]:
    r = requests.post(url, json=payload, timeout=timeout or DEFAULT_TIMEOUT)
    r.raise_for_status()
    try:
        return r.json()
    except ValueError:
        # JSON 이 아니면 원문 텍스트라도 반환
        return {"ok": True, "raw": r.text}

def call_memberslist_add_orders(payload: Dict[str, Any], timeout: Optional[int] = None) -> Dict[str, Any]:
    """
    멤버리스트 API로 주문 데이터 전송.
    - 기본 URL(환경변수 MEMBERSLIST_API_URL)에 먼저 요청
    - 404 이면 add_orders <-> addOrders 상호 변환하여 재시도 (호환성)
    """
    if not MEMBERSLIST_API_URL:
        raise MemberslistError("MEMBERSLIST_API_URL 미설정")

    url = MEMBERSLIST_API_URL.rstrip("/")
    try:
        return _post_json(url, payload, timeout)
    except requests.HTTPError as e:
        # 404 이면 경로 케이스 변환하여 한 번 더 시도
        status = getattr(e.response, "status_code", None)
        if status == 404:
            if url.endswith("/add_orders"):
                fallback = url[:-len("/add_orders")] + "/addOrders"
            elif url.endswith("/addOrders"):
                fallback = url[:-len("/addOrders")] + "/add_orders"
            else:
                # 경로가 예상과 다르면 그대로 재던짐
                raise MemberslistError(f"404 Not Found: {url}") from e

            # 재시도
            return _post_json(fallback, payload, timeout)

        # 그 외 HTTP 에러는 래핑해서 전달
        detail = getattr(e.response, "text", str(e))
        raise MemberslistError(f"Memberslist HTTPError: {status} | {detail}") from e
    except requests.RequestException as e:
        # 네트워크 등 요청 레벨 예외
        raise MemberslistError(f"Memberslist RequestException: {e}") from e

