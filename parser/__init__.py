"""
parser 패키지 초기화 파일
공식적으로 공개되는 파서 함수만 __all__에 정의
"""

# --------------------------
# 회원 관련 파서
# --------------------------
from .parser_member import (
    parse_registration,
    parse_request_and_update,
    parse_natural_query,
    parse_deletion_request,
)

# --------------------------
# 주문 관련 파서
# --------------------------
from .parse_order import (
    parse_order_text,
    parse_order_text_rule,
    parse_order_from_text,
)

# --------------------------
# 메모 관련 파서
# --------------------------
from .parser_memo import (
    parse_memo,
    parse_request_line,
)

# --------------------------
# 후원수당 관련 파서
# --------------------------
from .parser_commission import (
    parse_commission,
    process_date,
    clean_commission_data,
)

# --------------------------
# 필드 맵
# --------------------------
from .field_map import field_map


# --------------------------------------------------
# 공식 공개 API 목록 (__all__)
# --------------------------------------------------
__all__ = [
    # 회원
    "parse_registration",
    "parse_request_and_update",
    "parse_natural_query",
    "parse_deletion_request",
    # 주문
    "parse_order_text",
    "parse_order_text_rule",
    "parse_order_from_text",
    # 메모
    "parse_memo",
    "parse_request_line",
    # 후원수당
    "parse_commission",
    "process_date",
    "clean_commission_data",
    # 필드 맵
    "field_map",
]


