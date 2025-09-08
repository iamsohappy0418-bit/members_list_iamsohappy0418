import io
import traceback
import requests

# ===== flask =====
from flask import request, jsonify, g

# ===== utils =====
from utils.utils_openai import (
    extract_order_from_uploaded_image,   # 업로드된 이미지 → 주문 JSON 추출
)
from parser.parse_order import (
    parse_order_text,        # 자연어 주문 파서 (조회/삭제용)
    parse_order_text_rule,   # 자연어 주문 파서 (저장 규칙 기반)
)

# ===== service =====
from service.service_order import (
    addOrders,            # 주문 리스트 시트 저장
    save_order_to_sheet,  # 단일 주문 시트 저장
    find_order,           # 주문 조회
    register_order,       # 주문 등록
    update_order,         # 주문 수정
    delete_order,         # 주문 삭제
    clean_order_data,     # 주문 데이터 정리
)

# ===== config =====
from config import MEMBERSLIST_API_URL





# --------------------------
# 실제 처리 함수들
# --------------------------
def order_auto_func():
    data = request.get_json(silent=True) or {}
    if "image" in request.files or "image_url" in request.form or "image_url" in data:
        return order_upload_func()
    if "text" in data or "query" in data or "회원명" in data or "제품명" in data:
        return order_nl_func()
    return {"status": "error", "message": "❌ 입력이 올바르지 않습니다.", "http_status": 400}


def order_upload_func():
    user_agent = request.headers.get("User-Agent", "").lower()
    is_pc = ("windows" in user_agent) or ("macintosh" in user_agent)

    member_name = request.form.get("회원명")
    image_file = request.files.get("image")
    image_url = request.form.get("image_url")

    if not member_name:
        return {"status": "error", "message": "회원명이 필요합니다.", "http_status": 400}

    try:
        if image_file:
            image_bytes = io.BytesIO(image_file.read())
        elif image_url:
            resp = requests.get(image_url)
            if resp.status_code != 200:
                return {"status": "error", "message": "이미지 다운로드 실패", "http_status": 400}
            image_bytes = io.BytesIO(resp.content)
        else:
            return {"status": "error", "message": "이미지가 필요합니다.", "http_status": 400}

        order_data = extract_order_from_uploaded_image(image_bytes)

        if isinstance(order_data, dict) and "orders" in order_data:
            orders_list = order_data["orders"]
        elif isinstance(order_data, dict):
            orders_list = [order_data]
        elif isinstance(order_data, list):
            orders_list = order_data
        else:
            return {"status": "error", "message": "GPT 응답이 올바르지 않음", "raw": order_data, "http_status": 500}

        for o in orders_list:
            o["결재방법"] = ""
            o["수령확인"] = ""

        addOrders({"회원명": member_name, "orders": orders_list})

        return {
            "status": "success",
            "mode": "PC" if is_pc else "iPad",
            "회원명": member_name,
            "추출된_JSON": orders_list
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}


def order_nl_func():
    data = request.get_json(silent=True) or {}

    if "text" in data:
        text = data["text"].strip()
        if "저장" in text:
            parsed = parse_order_text_rule(text)
            save_order_to_sheet(parsed)
            return {"status": "success", "action": "저장", "parsed": parsed}
        elif "조회" in text:
            parsed = parse_order_text(text)
            matched = find_order(parsed.get("회원명"), parsed.get("제품명"))
            return [clean_order_data(o) for o in matched]
        elif "삭제" in text:
            parsed = parse_order_text(text)
            member, product = parsed.get("회원명"), parsed.get("제품명")
            if member and product:
                delete_order(member, product)
                return {"status": "success", "message": f"{member}님의 {product} 주문 삭제"}
            return {"status": "error", "message": "삭제할 주문을 찾을 수 없습니다.", "http_status": 404}

    member = data.get("회원명", "").strip()
    product = data.get("제품명", "").strip()

    if "수정목록" in data:
        update_order(member, product, data["수정목록"])
        return {"status": "success", "action": "수정"}

    if all(k in data for k in ["회원명", "제품명", "제품가격"]):
        register_order(
            member, product,
            data.get("제품가격", ""), data.get("PV", ""),
            data.get("결재방법", ""), data.get("배송처", ""),
            data.get("주문일자", "")
        )
        return {"status": "success", "action": "등록"}

    if member or product:
        matched = find_order(member, product)
        if not matched:
            return {"status": "error", "message": "해당 주문 없음", "http_status": 404}
        return [clean_order_data(o) for o in matched]

    return {"status": "error", "message": "유효한 요청 아님", "http_status": 400}


def save_order_proxy_func():
    try:
        payload = request.get_json(force=True)
        resp = requests.post(MEMBERSLIST_API_URL, json=payload)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": str(e), "http_status": 500}







