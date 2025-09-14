# routes/commission.py
import re
from flask import g
from parser.parse import parse_commission, clean_commission_data


# ────────────────────────────────────────────────────────────────────
# 공통 헬퍼
# ────────────────────────────────────────────────────────────────────
def _norm(s): 
    return (s or "").strip()

def _get_text_from_g() -> str:
    """
    g.query에서 자연어 텍스트 안전 추출
    우선순위: raw_text > query(str) > query(dict)["text","요청문","조건","criteria"]
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
        for k in ("text", "요청문", "조건", "criteria"):
            v = q.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""

# ────────────────────────────────────────────────────────────────────
# 허브: 자동 분기
# ────────────────────────────────────────────────────────────────────
def commission_find_auto_func():
    """
    후원수당 자동 분기 허브
    - query 가 dict면 → find_commission_func
    - 그 외 자연어 문자열이면 → search_commission_by_nl_func
    """
    try:
        q = g.query.get("query") if hasattr(g, "query") and isinstance(g.query, dict) else None
        # 원문 저장
        txt = _get_text_from_g()
        if txt:
            g.query["raw_text"] = txt
        elif isinstance(q, (dict, str)):
            g.query["raw_text"] = q if isinstance(q, str) else str(q)

        if isinstance(q, dict):
            return find_commission_func()
        return search_commission_by_nl_func()
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}

# ────────────────────────────────────────────────────────────────────
# JSON 기반 조회
# ────────────────────────────────────────────────────────────────────
def find_commission_func():
    """
    JSON 기반 후원수당 조회
    - g.query["query"] dict → service.find_commission 호출
    """
    try:
        q = g.query.get("query") if hasattr(g, "query") and isinstance(g.query, dict) else None
        if not isinstance(q, dict):
            return {"status": "error", "message": "후원수당 조회용 JSON(query)이 필요합니다.", "http_status": 400}

        clean = clean_commission_data(q) if callable(clean_commission_data) else q
        results = find_commission(clean) or []
        return {
            "status": "success",
            "intent": "find_commission",
            "count": len(results),
            "results": results,
            "http_status": 200
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}

# ────────────────────────────────────────────────────────────────────
# 자연어 기반 조회
# ────────────────────────────────────────────────────────────────────
def search_commission_by_nl_func():
    """
    자연어 기반 후원수당 조회
    - '8월 후원수당', '홍길동 후원수당' 등 → parse_commission → find_commission
    """
    try:
        text = _get_text_from_g()
        if not text:
            return {"status": "error", "message": "자연어 요청문이 없습니다.", "http_status": 400}

        parsed = parse_commission(text) or {}
        clean = clean_commission_data(parsed) if callable(clean_commission_data) else parsed

        results = find_commission(clean) or []
        return {
            "status": "success",
            "intent": "search_commission_by_nl",
            "criteria": clean,
            "count": len(results),
            "results": results,
            "http_status": 200
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}


