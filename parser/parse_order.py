import re
import json
from typing import Any, Dict, List
from flask import jsonify

from utils import (
    get_product_order_sheet, get_worksheet, append_row, delete_row, safe_update_cell,
    process_order_date, now_kst,
    extract_order_from_uploaded_image, parse_order_from_text,
)

from config import MEMBERSLIST_API_URL


from utils.utils_search import find_member_in_text





# ===============================================
# ✅ 규칙 기반 자연어 파서
# ===============================================
def parse_order_text(text: str) -> Dict[str, Any]:
    """
    자연어 주문 문장을 intent + query 구조로 변환
    예: "이수민 주문 노니 2개 카드 결제 서울 주소 오늘"
    """
    text = (text or "").strip()
    query: Dict[str, Any] = {}

    # ✅ 회원명
    member = find_member_in_text(text)
    query["회원명"] = member if member else None

    # ✅ 제품명 + 수량 (예: 노니 2개, 홍삼 3박스, 치약 1병)
    prod_match = re.search(r"([\w가-힣]+)\s*(\d+)\s*(개|박스|병|포)?", text)
    if prod_match:
        query["제품명"] = prod_match.group(1)
        query["수량"] = int(prod_match.group(2))
    else:
        query["제품명"] = "제품"
        query["수량"] = 1

    # ✅ 결제방법
    if "카드" in text:
        query["결제방법"] = "카드"
    elif "현금" in text:
        query["결제방법"] = "현금"
    elif "계좌" in text or "이체" in text:
        query["결제방법"] = "계좌이체"
    else:
        query["결제방법"] = "카드"

    # ✅ 배송처
    # "주소: 서울", "배송지: 부산", "서울 주소" 같은 패턴 지원
    address_match = re.search(r"(?:주소|배송지)[:：]?\s*([가-힣0-9\s]+)", text)
    query["배송처"] = address_match.group(1).strip() if address_match else ""

    # ✅ 주문일자 (오늘/내일/어제/2025-09-11)
    query["주문일자"] = process_order_date(text)

    return {
        "intent": "order_auto",
        "query": query
    }


# ===============================================
# ✅ GPT 응답 후처리: 안전하게 주문 리스트 변환
# ===============================================
def ensure_orders_list(parsed: Any) -> List[Dict[str, Any]]:
    """
    Vision/GPT 응답(parsed)을 안전하게 '주문 리스트(list of dict)'로 변환
    """
    if not parsed:
        return []

    # 문자열(JSON)인 경우
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except Exception:
            return []

    # dict인 경우
    if isinstance(parsed, dict):
        if "orders" in parsed and isinstance(parsed["orders"], list):
            return parsed["orders"]
        if all(isinstance(v, (str, int, float, type(None))) for v in parsed.values()):
            return [parsed]
        return []

    # list인 경우
    if isinstance(parsed, list):
        if all(isinstance(item, dict) for item in parsed):
            return parsed
        return []

    return []


def parse_order_text_rule(text: str) -> dict:
    """
    예전 버전과의 호환용 더미 함수
    현재는 parse_order_text()를 호출하도록 연결
    """
    return parse_order_text(text)


