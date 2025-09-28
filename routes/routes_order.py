import re
from flask import g, request
from utils import parse_order_from_text
from utils import extract_order_from_uploaded_image
from utils import process_order_date
from utils import get_worksheet
from parser.parse import handle_product_order, save_order_to_sheet


import os, re, io, json, base64, requests, traceback
from flask import jsonify
from datetime import datetime



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







def get_member_info_by_name_list(name: str) -> list[dict]:
    """
    DB 시트에서 회원명으로 검색하여 일치하는 회원 목록 반환
    - 여러 명 있을 경우 순번 부여
    - 필드: 회원번호, 휴대폰번호, 주소, 가입일자
    """
    sheet = get_member_sheet()
    rows = sheet.get_all_records()

    matched = [
        {
            "순번": i + 1,
            "회원명": row.get("회원명", "").strip(),
            "회원번호": str(row.get("회원번호", "")).strip(),
            "휴대폰번호": str(row.get("휴대폰번호", "")).strip(),
            "주소": str(row.get("주소", "")).strip(),
            "가입일자": str(row.get("가입일자", "")).strip(),
        }
        for i, row in enumerate(rows)
        if str(row.get("회원명", "")).strip() == name
    ]

    return matched








def order_upload_func():
    """
    이미지/스캔된 주문서 업로드 처리
    - request.files + request.form["text"] 필수
    - 회원명 추출 후 DB 조회
    - 동명이인 > 1명 → candidates 반환 (409)
    - 클라이언트가 회원번호 포함 재요청 시 저장
    """
    try:
        if not (hasattr(request, "files") and request.files):
            return {"status": "error", "message": "업로드된 파일이 없습니다.", "http_status": 400}

        file_key = next(iter(request.files.keys()))
        file = request.files[file_key]

        user_text = request.form.get("text", "").strip()
        member_name = user_text.split()[0] if user_text else "미지정"
        member_no = request.form.get("회원번호", "").strip()

        # 1) 이미지 → JSON 파싱
        parsed = extract_order_from_uploaded_image(file)
        if not parsed or "orders" not in parsed:
            return {"status": "error", "message": "이미지에서 주문 추출 실패", "raw": parsed, "http_status": 400}

        # 2) 회원 확인
      
        member_info = None

        if member_no:  # ✅ 클라이언트가 회원번호를 직접 지정한 경우
            matched = get_member_info_by_number(member_no)
            if not matched:
                return {"error": f"회원번호 {member_no} 회원을 찾을 수 없습니다.", "http_status": 404}
            member_info = matched
        else:  # ✅ 회원명으로 검색
            matched_members = get_member_info_by_name_list(member_name)
            if len(matched_members) == 0:
                return {"error": f"{member_name} 회원을 찾을 수 없습니다.", "http_status": 404}
            elif len(matched_members) > 1:
                return {
                    "error": f"{member_name} 이름으로 여러 명의 회원이 존재합니다. 순번을 선택해 주세요.",
                    "candidates": matched_members,
                    "http_status": 409
                }
            member_info = matched_members[0]

        # 3) 주문 데이터 병합
        today = datetime.now().strftime("%Y-%m-%d")
        enriched_orders = []
        for o in parsed["orders"]:
            enriched_orders.append({
                "주문일자": today,
                "회원명": member_name,
                "회원번호": member_info.get("회원번호", ""),
                "휴대폰번호": member_info.get("휴대폰번호", ""),
                "제품명": o.get("제품명"),
                "제품가격": o.get("제품가격"),
                "PV": o.get("PV"),
                "결재방법": o.get("결재방법", "카드"),
                "주문자_고객명": o.get("주문자_고객명"),
                "주문자_휴대폰번호": o.get("주문자_휴대폰번호"),
                "배송처": o.get("배송처"),
                "수령확인": o.get("수령확인", "N"),
            })

        # 4) 저장 실행
        results = []
        for order in enriched_orders:
            res = handle_product_order(order) if callable(handle_product_order) else save_order_to_sheet(order)
            results.append(res)

        return {
            "status": "success" if all(_ok(r) for r in results) else "error",
            "intent": "order_upload",
            "parsed": enriched_orders,
            "http_status": 200 if all(_ok(r) for r in results) else 400,
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}






from parser import handle_order_save

def save_order_proxy_func():
    """
    구조화 JSON 주문 저장
    - g.query["query"] dict 기반
    """
    try:
        payload = g.query.get("query") if hasattr(g, "query") and isinstance(g.query, dict) else None
        if not isinstance(payload, dict):
            return {"status": "error", "message": "주문 JSON(payload)이 필요합니다.", "http_status": 400}

        # 필드 보정
        if "회원명" in payload and "주문회원" not in payload:
            payload["주문회원"] = payload["회원명"]
        if "member" in payload and "주문회원" not in payload:
            payload["주문회원"] = payload["member"]

        # ✅ 주문 저장 실행
        res = handle_order_save(payload)

        return {
            "status": res.get("status", "error"),
            "intent": "save_order_proxy",
            "http_status": res.get("http_status", 400)
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}








# ✅ 자연어로 작성된 주문 요청을 파싱하여 JSON 구조로 반환
import re
from typing import Dict, Any

def parse_order_natural_text(text: str) -> Dict[str, Any]:
    """
    자연어로 작성된 제품주문 텍스트를 파싱하여 JSON으로 변환합니다.
    - 예시 입력: "이태수 제품주문 저장\n주문일자: 2025-09-27\n회원명: 이태수 ..."
    - 반환 예: {"회원명": "이태수", "제품명": "노니", ...}
    """
    lines = text.strip().split("\n")
    data = {}

    # 1. 첫 줄이 intent 문장인 경우 (예: "이태수 제품주문 저장")
    if lines:
        data["query"] = lines[0].strip()

    # 2. 나머지 줄 파싱
    for line in lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            # 숫자형 필드 자동 변환
            if key in ["제품가격", "PV"]:
                try:
                    value = int(value.replace(",", ""))
                except ValueError:
                    pass

            data[key] = value

    return data


# ✅ 테스트용 실행 예시
if __name__ == "__main__":
    order_text = '''
    이태수 제품주문 저장
    주문일자: 2025-09-27
    회원명: 이태수
    회원번호: 7012507160020129
    휴대폰번호: 010-3925-8255
    제품명: [500만 set 돌파 기념 프로모션] 애터미 오롯이 담은 …
    제품가격: 239000
    PV: 120000
    결재방법: 카드
    주문자_고객명: 김성옥
    주문자_휴대폰번호: 010-3925-8255
    배송처: 대구 북구 산격2동 1659번지, 동아베스트 3층
    수령확인: N
    '''

    parsed = parse_order_natural_text(order_text)
    import json
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
























def addOrders(payload):
    url_primary = os.getenv("MEMBERSLIST_API_URL", "").strip()
    url_fallback = url_primary.replace("addOrders", "add_orders") if "addOrders" in url_primary else ""
    if url_primary:
        try:
            resp = requests.post(url_primary, json=payload, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404 and url_fallback:
                resp2 = requests.post(url_fallback, json=payload, timeout=20)
                resp2.raise_for_status()
                return resp2.json()
            return {"ok": False, "error": "API 오류, 시트에 저장됨"}
        except requests.RequestException:
            return {"ok": False, "error": "네트워크 오류, 시트에 저장됨"}
    return {"ok": False, "error": "API 미설정, 시트에 저장됨"}






# ===================== 주문 처리 함수 =====================
def order_upload_pc_func():
    """PC 업로드"""
    mode = request.form.get("mode") or request.args.get("mode") or "api"
    member_name = request.form.get("회원명")
    image_file = request.files.get("image")
    image_url = request.form.get("image_url")
    message_text = (request.form.get("message") or "").strip()

    if "제품주문 저장" in message_text and not member_name:
        member_name = message_text.replace("제품주문 저장", "").strip()

    if not member_name:
        return {"status": "error", "message": "회원명이 필요합니다.", "http_status": 400}

    try:
        if image_file:
            image_bytes = io.BytesIO(image_file.read())
        elif image_url:
            resp = requests.get(image_url, timeout=20)
            if resp.status_code != 200:
                return {"status": "error", "message": "이미지 다운로드 실패", "http_status": 400}
            image_bytes = io.BytesIO(resp.content)
        else:
            return {"status": "error", "message": "image(파일) 또는 image_url 필요", "http_status": 400}

        orders_list = extract_order_from_uploaded_image(image_bytes)
        for o in orders_list:
            o.setdefault("결재방법", ""); o.setdefault("수령확인", ""); o.setdefault("주문일자", process_order_date(""))

        save_result = addOrders({"회원명": member_name, "orders": orders_list})
        return {"status": "success","mode": mode,"회원명": member_name,"추출된_JSON": orders_list,
                "저장_결과": save_result,"http_status": 200}
    except Exception as e:
        return {"status": "error", "message": str(e), "http_status": 500}






def order_upload_ipad_func():
    """iPad 업로드"""
    mode = request.form.get("mode") or request.args.get("mode") or "api"
    member_name = request.form.get("회원명")
    image_file = request.files.get("image")
    image_url = request.form.get("image_url")
    message_text = (request.form.get("message") or "").strip()
    if "제품주문 저장" in message_text and not member_name:
        member_name = message_text.replace("제품주문 저장", "").strip()
    if not member_name:
        return {"status": "error","message": "회원명이 필요합니다.","http_status": 400}
    try:
        if image_file:
            image_bytes = io.BytesIO(image_file.read())
        elif image_url:
            resp = requests.get(image_url, timeout=20)
            if resp.status_code != 200: return {"status": "error","message": "이미지 다운로드 실패","http_status": 400}
            image_bytes = io.BytesIO(resp.content)
        else:
            return {"status": "error","message": "image 또는 image_url 필요","http_status": 400}

        orders_list = extract_order_from_uploaded_image(image_bytes)
        for o in orders_list:
            o.setdefault("결재방법", ""); o.setdefault("수령확인", ""); o.setdefault("주문일자", process_order_date(""))

        save_result = addOrders({"회원명": member_name, "orders": orders_list})
        return {"status": "success","mode": mode,"회원명": member_name,"추출된_JSON": orders_list,
                "저장_결과": save_result,"http_status": 200}
    except Exception as e:
        return {"status": "error","message": str(e),"http_status": 500}
























