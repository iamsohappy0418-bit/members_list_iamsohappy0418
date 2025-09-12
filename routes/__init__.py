"""
routes 패키지 초기화 파일
intent 기반 공식 API만 export
"""

# --------------------------
# 회원 관련
# --------------------------
from .routes_member import (
    search_member_func,      # 회원 검색 실행
    register_member_func,    # 회원 등록 실행
    update_member_func,      # 회원 수정 실행
    save_member_func,        # 회원 저장(업서트) 실행
    delete_member_func,      # 회원 삭제 실행
    member_select,
)

# --------------------------
# 메모 관련
# --------------------------
from .routes_memo import (
    memo_save_auto_func,         # 메모 자동 저장
    add_counseling_func,         # 상담일지 추가
    search_memo_func,            # 메모 검색
    search_memo_from_text_func,  # 자연어 기반 메모 검색
    memo_find_auto_func,         # 메모 intent 자동 분기
)

# --------------------------
# 주문 관련
# --------------------------
from .routes_order import (
    order_auto_func,        # 주문 intent 자동 분기
    order_upload_func,      # 주문 이미지 업로드 처리
    order_nl_func,          # 자연어 기반 주문 처리
    save_order_proxy_func,  # 외부 API 프록시 저장
)

# --------------------------
# 후원수당 관련
# --------------------------
from .routes_commission import (
    commission_find_auto_func,  # 후원수당 intent 자동 분기
    find_commission_func,       # 후원수당 JSON 조회
    search_commission_by_nl_func,  # 후원수당 자연어 조회
)

# --------------------------
# intent 맵
# --------------------------
from .intent_map import (
    INTENT_MAP,
    MEMBER_INTENTS,
    MEMO_INTENTS,
    ORDER_INTENTS,
    COMMISSION_INTENTS,
)

# --------------------------------------------------
# 공식 공개 API (__all__)
# --------------------------------------------------
__all__ = [
    # 회원
    "search_member_func", "register_member_func",
    "update_member_func", "save_member_func", "delete_member_func", "member_select",

    # 메모
    "memo_save_auto_func", "add_counseling_func",
    "search_memo_func", "search_memo_from_text_func", "memo_find_auto_func",

    # 주문
    "order_auto_func", "order_upload_func",
    "order_nl_func", "save_order_proxy_func",

    # 후원수당
    "commission_find_auto_func", "find_commission_func", "search_commission_by_nl_func",

    # intent 맵
    "INTENT_MAP", "MEMBER_INTENTS", "MEMO_INTENTS",
    "ORDER_INTENTS", "COMMISSION_INTENTS",
]
