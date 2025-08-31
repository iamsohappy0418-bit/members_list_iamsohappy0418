import re
import json
from typing import Any, Dict, List
from flask import jsonify

# utils
from utils.sheets import get_order_sheet, get_worksheet, append_row, delete_row, safe_update_cell
from utils.common import process_order_date, now_kst
from utils.openai_utils import extract_order_from_uploaded_image, parse_order_from_text

# config
from config import MEMBERSLIST_API_URL

# 📌 회원명 보정을 위해 추가
from service.member_service import find_member_in_text  



# ===============================================
# ✅ 규칙 기반 자연어 파서
# ===============================================
def parse_order_text(text: str) -> dict:
    result: Dict[str, Any] = {}

    # 회원명 보정
    member = find_member_in_text(text)
    if member:
        result["회원명"] = member
    else:
        result["회원명"] = None   # 찾지 못하면 None

    # 제품명 + 수량
    prod_match = re.search(r"([\w가-힣]+)[\s]*(\d+)\s*개", text)
    if prod_match:
        result["제품명"] = prod_match.group(1)
        result["수량"] = int(prod_match.group(2))
    else:
        result["제품명"] = "제품"
        result["수량"] = 1

    # 결제방법
    if "카드" in text:
        result["결제방법"] = "카드"
    elif "현금" in text:
        result["결제방법"] = "현금"
    elif "계좌" in text:
        result["결제방법"] = "계좌이체"
    else:
        result["결제방법"] = "카드"

    # 배송지
    address_match = re.search(r"(?:주소|배송지)[:：]\s*(.+?)(\s|$)", text)
    result["배송처"] = address_match.group(1).strip() if address_match else ""

    # 주문일자
    result["주문일자"] = process_order_date(text)

    return result


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


