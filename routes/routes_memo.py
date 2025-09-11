# routes/memos.py
import re
from flask import g
from service import save_memo, search_memo_core, find_memo, handle_search_memo
from parser.parser_memo import parse_memo



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
    메모 검색 API
    - 자연어 입력 → parse_memo 통해 dict 변환
    - JSON 입력 → 그대로 사용
    - before_request에서 이미 dict로 파싱된 경우도 처리
    - "전체메모 검색 ..." → 상담일지+개인일지+활동일지 그룹핑
    """
    try:
        q = getattr(g, "query", None)  # g.query 전체
        results = {}

        print("[DEBUG] raw g.query:", q)

        sheet_name, keywords, member_name = None, [], None

        # ----------------------------
        # 1) JSON / 자연어 / dict 분기
        # ----------------------------
        if isinstance(q, dict):
            if isinstance(q.get("query"), str):
                # ✅ 자연어 입력
                parsed = parse_memo(q.get("query"))
                print("[DEBUG] parse_memo output:", parsed)

                sheet_name = parsed.get("일지종류")
                keywords = parsed.get("keywords", [])
                member_name = parsed.get("회원명")

            elif isinstance(q.get("query"), dict):
                # ✅ 이미 before_request에서 파싱된 dict
                inner_q = q.get("query", {})
                sheet_name = inner_q.get("일지종류", "").strip()
                member_name = inner_q.get("회원명")

                # keywords vs 검색어 보정
                if "keywords" in inner_q:
                    keywords = inner_q.get("keywords", [])
                elif "검색어" in inner_q:
                    keywords = [inner_q.get("검색어")] if inner_q.get("검색어") else []
                else:
                    keywords = []

            else:
                # ✅ JSON API 입력 (직접 구조화 dict)
                sheet_name = q.get("일지종류", "").strip()
                member_name = q.get("회원명")
                keywords = q.get("keywords", [])

        else:
            # ✅ g.query 자체가 문자열
            parsed = parse_memo(q) if q else {}
            print("[DEBUG] parse_memo output:", parsed)

            sheet_name = parsed.get("일지종류")
            keywords = parsed.get("keywords", [])
            member_name = parsed.get("회원명")

        # ----------------------------
        # 2) sheet_name 검증
        # ----------------------------
        if not sheet_name:
            return {
                "status": "error",
                "message": "❌ 일지종류를 인식할 수 없습니다.",
                "http_status": 400
            }

        # ----------------------------
        # 3) 검색 실행
        # ----------------------------
        if sheet_name == "전체":
            results = {}
            for sn in ["상담일지", "개인일지", "활동일지"]:
                core_results = search_memo_core(sn, keywords, member_name=member_name)
                print(f"[DEBUG] {sn} 검색 결과 {len(core_results)}건")
                results[sn] = core_results


        else:
            results = {
                sheet_name: search_memo_core(sheet_name, keywords, member_name=member_name)
            }

        # ----------------------------
        # 4) 반환
        # ----------------------------
        return {
            "status": "success",
            "intent": "search_memo",
            "results": results,
            "http_status": 200
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
            "http_status": 500
        }







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


