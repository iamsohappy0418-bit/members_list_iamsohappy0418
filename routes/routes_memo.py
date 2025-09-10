# routes/memos.py
import re
from flask import g
from service import save_memo, search_memo_core, find_memo, handle_search_memo



# ────────────────────────────────────────────────────────────────────
# 공통 헬퍼
# ────────────────────────────────────────────────────────────────────
def _norm(s: str) -> str:
    return (s or "").strip()

def _get_text_from_g() -> str:
    """
    g.query에서 자연어 텍스트를 안전하게 추출
    우선순위: raw_text(str) > query(str) > query(dict)["text"/"요청문"/"메모"/"내용"]
    """
    if not hasattr(g, "query") or not isinstance(g.query, dict):
        return ""
    # 1) raw_text 우선
    rt = g.query.get("raw_text")
    if isinstance(rt, str) and rt.strip():
        return rt.strip()

    q = g.query.get("query")
    # 2) query가 문자열
    if isinstance(q, str) and q.strip():
        return q.strip()
    # 3) query가 dict면 대표 키들에서 추출
    if isinstance(q, dict):
        for k in ("text", "요청문", "메모", "내용"):
            v = q.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""

# ────────────────────────────────────────────────────────────────────
# 1) 메모/일지 자동 분기 허브
# ────────────────────────────────────────────────────────────────────
def memo_find_auto_func():
    """
    메모/일지 자동 분기 허브
    - '저장' 포함 → memo_save_auto_func
    - '검색' 포함 → search_memo_from_text_func
    - 그 외 → search_memo_func
    """
    try:
        text = _get_text_from_g()
        if "저장" in text:
            return memo_save_auto_func()
        if "검색" in text:
            return search_memo_from_text_func()
        return search_memo_func()
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}

# ────────────────────────────────────────────────────────────────────
# 2) 자연어 메모 저장
# ────────────────────────────────────────────────────────────────────
def memo_save_auto_func():
    """
    자연어 메모 저장 (업서트 느낌)
    - g.query의 raw_text 또는 query에서 텍스트를 추출하여 저장
    """
    try:
        text = _get_text_from_g()
        if not text:
            return {"status": "error", "message": "메모 내용이 없습니다.", "http_status": 400}

        res = save_memo(text)
        ok = (res or {}).get("status") in {"ok", "success", True}
        return {
            "status": "success" if ok else "error",
            "intent": "memo_save_auto",
            "http_status": 201 if ok else 400
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}

# ────────────────────────────────────────────────────────────────────
# 3) 자연어 기반 메모 검색
# ────────────────────────────────────────────────────────────────────
def search_memo_from_text_func():
    """
    자연어 기반 메모 검색
    """
    try:
        text = _get_text_from_g()
        if not text:
            return {"status": "error", "message": "검색 문장이 없습니다.", "http_status": 400}

        results = handle_search_memo(text) if callable(handle_search_memo) \
                  else search_memo_core({"text": text})

        return {
            "status": "success",
            "intent": "search_memo_from_text",
            "count": len(results or []),
            "results": results or [],
            "http_status": 200
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}

# ────────────────────────────────────────────────────────────────────
# 4) JSON 기반 메모 검색
# ────────────────────────────────────────────────────────────────────
def search_memo_func():
    """
    JSON 기반 메모 검색
    - g.query["query"] 가 dict라면 필터 검색, 아니면 텍스트 검색으로 폴백
    """
    try:
        q = g.query.get("query") if hasattr(g, "query") and isinstance(g.query, dict) else None

        if isinstance(q, dict):
            results = search_memo_core(q)
        else:
            text = _get_text_from_g()
            results = handle_search_memo(text) if text else []

        return {
            "status": "success",
            "intent": "search_memo",
            "count": len(results or []),
            "results": results or [],
            "http_status": 200
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}

# ────────────────────────────────────────────────────────────────────
# 5) 상담/개인/활동 일지 저장(JSON 전용)
# ────────────────────────────────────────────────────────────────────
def add_counseling_func():
    """
    상담일지/개인일지/활동일지 저장(JSON 전용)
    - g.query["query"] dict 에 저장 필드가 포함되어 있다고 가정
    """
    try:
        q = g.query.get("query") if hasattr(g, "query") and isinstance(g.query, dict) else None
        text = ""
        if isinstance(q, dict):
            for k in ("요청문", "text", "메모", "내용"):
                v = q.get(k)
                if isinstance(v, str) and v.strip():
                    text = v.strip()
                    break
        if not text:
            # 폴백: 자연어 경로
            text = _get_text_from_g()

        if not text:
            return {"status": "error", "message": "저장할 요청문이 없습니다.", "http_status": 400}

        res = save_memo(text)
        ok = (res or {}).get("status") in {"ok", "success", True}
        return {
            "status": "success" if ok else "error",
            "intent": "add_counseling",
            "http_status": 201 if ok else 400
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}


