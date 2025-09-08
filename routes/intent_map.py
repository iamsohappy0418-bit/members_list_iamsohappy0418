"""
intent_map.py
각 intent → 실행 함수 매핑
"""

# --------------------------
# 회원 관련
# --------------------------
from .routes_member import (
    search_member_func, register_member_func,
    update_member_func, save_member_func, delete_member_func,find_member_logic,search_by_code_logic,
)

# --------------------------
# 메모 관련
# --------------------------
from .routes_memo import (
    memo_save_auto_func, add_counseling_func,
    search_memo_func, search_memo_from_text_func, memo_find_auto_func,
)

# --------------------------
# 주문 관련
# --------------------------
from .routes_order import (
    order_auto_func, order_upload_func, order_nl_func, save_order_proxy_func,
)

# --------------------------
# 후원수당 관련
# --------------------------
from .routes_commission import (
    commission_find_auto_func, find_commission_func, search_commission_by_nl_func,
)

# --------------------------------------------------
# intent → 함수 매핑
# --------------------------------------------------
INTENT_MAP = {
    # 회원
    "search_member": search_member_func,
    "find_member_logic": find_member_logic,   # ✅ 추가 (단순 이름 검색 지원)
    "search_by_code_logic": search_by_code_logic,
    "register_member": register_member_func,
    "update_member": update_member_func,
    "save_member": save_member_func,
    "delete_member": delete_member_func,

    # 메모
    "memo_save_auto": memo_save_auto_func,
    "add_counseling": add_counseling_func,
    "search_memo": search_memo_func,
    "search_memo_from_text": search_memo_from_text_func,
    "memo_find_auto": memo_find_auto_func,

    # 주문
    "order_auto": order_auto_func,
    "order_upload": order_upload_func,
    "order_nl": order_nl_func,
    "save_order_proxy": save_order_proxy_func,

    # 후원수당
    "commission_find_auto": commission_find_auto_func,
    "find_commission": find_commission_func,
    "search_commission_by_nl": search_commission_by_nl_func,
}

# --------------------------------------------------
# intent 그룹별 세분화
# --------------------------------------------------
MEMBER_INTENTS = {
    "search_member": search_member_func,
    "register_member": register_member_func,
    "update_member": update_member_func,
    "save_member": save_member_func,
    "delete_member": delete_member_func,
}

MEMO_INTENTS = {
    "memo_save_auto": memo_save_auto_func,
    "add_counseling": add_counseling_func,
    "search_memo": search_memo_func,
    "search_memo_from_text": search_memo_from_text_func,
    "memo_find_auto": memo_find_auto_func,
}

ORDER_INTENTS = {
    "order_auto": order_auto_func,
    "order_upload": order_upload_func,
    "order_nl": order_nl_func,
    "save_order_proxy": save_order_proxy_func,
}

COMMISSION_INTENTS = {
    "commission_find_auto": commission_find_auto_func,
    "find_commission": find_commission_func,
    "search_commission_by_nl": search_commission_by_nl_func,
}


