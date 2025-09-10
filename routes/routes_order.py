import re
from flask import g, request
from parser import parse_order_from_text
from utils import extract_order_from_uploaded_image
from service import handle_product_order, save_order_to_sheet




def _norm(s): 
    return (s or "").strip()

def _ok(res) -> bool:
    return bool(res) and (res.get("status") in {"ok", "success", True})

def _get_text_from_g() -> str:
    """
    g.query에서 주문 자연어 텍스트를 안전하게 추출
    우선순위: raw_text > query(str) > query(dict)["text","요청문","주문문","내용"]
    """
    if not hasattr(g, "query") or not isinstance(g.query, dict):
        return ""
    rt = g.query.get("raw_text")
    if isinstance(rt, str) and rt.strip():
        return rt.strip()
    q = g.query.get("query")
    if isinstance(q, str) and q.strip():
        return q.strip()
    if isinstance(q, dict):
        for k in ("text", "요청문", "주문문", "내용"):
            v = q.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""

def _is_structured_order(obj: dict) -> bool:
    """
    dict가 '구조화 주문'인지 판별.
    최소 기준: 대표 키가 하나 이상 존재.
    """
    if not isinstance(obj, dict):
        return False
    candidate_keys = {
        "주문", "주문회원", "items", "상품", "order", "member", "date", "결제", "수량"
    }
    return any(k in obj for k in candidate_keys)


def order_auto_func():
    """
    주문 허브 (라우트 아님)
    - 파일 업로드가 있으면 → order_upload_func
    - query 가 dict이고 '구조화 주문'이면 → save_order_proxy_func
    - 그 외(문자열/텍스트 dict 등) → order_nl_func
    """
    try:
        q = g.query.get("query") if hasattr(g, "query") and isinstance(g.query, dict) else None
        # 원본 텍스트 저장 (문자열/딕셔너리 모두 문자열화)
        raw = _get_text_from_g()
        if raw:
            g.query["raw_text"] = raw
        elif isinstance(q, (dict, str)):
            g.query["raw_text"] = q if isinstance(q, str) else str(q)

        # 1) 파일 업로드 우선
        if hasattr(request, "files") and request.files:
            return order_upload_func()

        # 2) 구조화 JSON → 저장 프록시
        if isinstance(q, dict) and _is_structured_order(q):
            return save_order_proxy_func()

        # 3) 자연어 텍스트 → NLU 기반
        return order_nl_func()

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}


def order_nl_func():
    """
    자연어 주문 처리
    - g.query["raw_text"] 기준으로 파싱 → 서비스 저장
    """
    try:
        text = _get_text_from_g()
        if not text:
            return {"status": "error", "message": "주문 문장이 비어 있습니다.", "http_status": 400}

        parsed = parse_order_from_text(text)  # 프로젝트 파서 사용
        if not parsed:
            return {"status": "error", "message": "주문을 해석할 수 없습니다.", "http_status": 400}

        # 저장 로직 (서비스 계층)
        res = handle_product_order(parsed) if callable(handle_product_order) else save_order_to_sheet(parsed)
        return {
            "status": "success" if _ok(res) else "error",
            "intent": "order_auto",  # 허브에서 호출되므로 intent는 order_auto로 유지
            "parsed": parsed,
            "http_status": 200 if _ok(res) else 400
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}


def order_upload_func():
    """
    이미지/스캔된 주문서 업로드 처리
    - request.files에서 첫 파일 인식 → OCR/LLM 파싱 → 저장
    """
    try:
        if not (hasattr(request, "files") and request.files):
            return {"status": "error", "message": "업로드된 파일이 없습니다.", "http_status": 400}

        # 가장 첫 파일 기준
        file_key = next(iter(request.files.keys()))
        file = request.files[file_key]

        parsed = extract_order_from_uploaded_image(file)
        if not parsed:
            return {"status": "error", "message": "업로드된 이미지에서 주문을 추출하지 못했습니다.", "http_status": 400}

        res = handle_product_order(parsed) if callable(handle_product_order) else save_order_to_sheet(parsed)
        return {
            "status": "success" if _ok(res) else "error",
            "intent": "order_upload",
            "parsed": parsed,
            "http_status": 200 if _ok(res) else 400
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}


def save_order_proxy_func():
    """
    구조화 JSON 주문 저장
    - g.query["query"] 가 dict라고 가정
    - 일부 필드명 표준화(회원명/주문회원, member 등) 후 저장
    """
    try:
        payload = g.query.get("query") if hasattr(g, "query") and isinstance(g.query, dict) else None
        if not isinstance(payload, dict):
            return {"status": "error", "message": "주문 JSON(payload)이 필요합니다.", "http_status": 400}

        # 필드 표준화(있을 때만)
        if "회원명" in payload and "주문회원" not in payload:
            payload["주문회원"] = payload["회원명"]
        if "member" in payload and "주문회원" not in payload:
            payload["주문회원"] = payload["member"]

        res = handle_product_order(payload) if callable(handle_product_order) else save_order_to_sheet(payload)
        return {
            "status": "success" if _ok(res) else "error",
            "intent": "save_order_proxy",
            "http_status": 200 if _ok(res) else 400
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}


