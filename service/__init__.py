"""
service 패키지 초기화 파일
공식적으로 공개되는 서비스 함수만 __all__에 정의
"""

# --------------------------
# 회원 관련 서비스
# --------------------------
from .service_member import (
    find_member_internal,
    clean_member_data,
    register_member_internal,
    update_member_internal,
    delete_member_internal,
    delete_member_field_nl_internal,
    process_member_query,
)

# --------------------------
# 주문 관련 서비스
# --------------------------
from .service_order import (
    addOrders,
    handle_order_save,
    handle_product_order,
    find_order,
    register_order,
    update_order,
    delete_order,
    delete_order_by_row,
    clean_order_data,
    save_order_to_sheet,
)

# --------------------------
# 메모 관련 서비스
# --------------------------
from .service_memo import (
    save_memo,
    find_memo,
    search_in_sheet,
    search_memo_core,
)

# --------------------------
# 후원수당 관련 서비스
# --------------------------
from .service_commission import (
    find_commission,
    register_commission,
    update_commission,
    delete_commission,
)

# --------------------------------------------------
# 공식 공개 API 목록 (__all__)
# --------------------------------------------------
__all__ = [
    # 회원
    "find_member_internal",
    "clean_member_data",
    "register_member_internal",
    "update_member_internal",
    "delete_member_internal",
    "delete_member_field_nl_internal",
    "process_member_query",

    # 주문
    "addOrders",
    "handle_order_save",
    "handle_product_order",
    "find_order",
    "register_order",
    "update_order",
    "delete_order",
    "delete_order_by_row",
    "clean_order_data",
    "save_order_to_sheet",

    # 메모
    "save_memo",
    "find_memo",
    "search_in_sheet",
    "search_memo_core",

    # 후원수당
    "find_commission",
    "register_commission",
    "update_commission",
    "delete_commission",
]


