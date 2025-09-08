import traceback

# ===== flask =====
from flask import request, jsonify, g

# ===== parser =====
from parser import parse_commission   # 자연어 후원수당 파서

# ===== service =====
from service.service_commission import (
    find_commission,   # 후원수당 조회
)





# --------------------------
# 실제 처리 함수들
# --------------------------
def commission_find_auto_func():
    """자동 분기: JSON vs 자연어"""
    data = request.get_json(silent=True) or {}

    if "query" in data or "text" in data:
        return search_commission_by_nl_func()
    if "회원명" in data:
        return find_commission_func()
    if isinstance(data, str) and data.strip():
        return search_commission_by_nl_func()

    return {
        "status": "error",
        "message": "❌ 입력이 올바르지 않습니다. "
                   "자연어는 'query/text/단일문자열', "
                   "JSON은 '회원명'을 포함해야 합니다.",
        "http_status": 400
    }


def find_commission_func():
    """후원수당 조회 API (JSON 전용)"""
    try:
        data = request.get_json()
        member = data.get("회원명", "").strip()
        if not member:
            return {"status": "error", "error": "회원명이 필요합니다.", "http_status": 400}

        results = find_commission({"회원명": member})
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "error": str(e), "http_status": 500}


def search_commission_by_nl_func():
    """후원수당 자연어 검색 API"""
    try:
        data = request.get_json()
        query = data.get("query") or data.get("text")
        if not query:
            return {"status": "error", "message": "query/text 파라미터가 필요합니다.", "http_status": 400}

        parsed = parse_commission(query)
        member = parsed.get("회원명", "")
        if not member:
            return {"status": "error", "message": "자연어에서 회원명을 추출할 수 없습니다.", "http_status": 400}

        results = find_commission({"회원명": member})
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": f"[서버 오류] {str(e)}", "http_status": 500}



