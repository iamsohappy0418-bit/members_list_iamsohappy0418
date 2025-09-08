"""
utils 패키지 초기화 파일
공식적으로 공개되는 유틸 함수만 __all__에 정의
"""

# --------------------------
# 날짜/시간 처리 (utils_date)
# --------------------------
from .utils_date import (
    now_kst,
    process_order_date,
    parse_dt,
)

# --------------------------
# 문자열 처리 (text_cleaner, utils_string)
# --------------------------
from .text_cleaner import (
    clean_content,
    clean_tail_command,
    clean_value_expression,
)
from .utils_string import (
    remove_josa,
    remove_spaces,
    split_to_parts,
    is_match,
    match_condition,
)

# --------------------------
# Google Sheets 관련 (sheets)
# --------------------------
from .sheets import (
    get_sheet,
    get_worksheet,
    get_member_sheet,
    get_product_order_sheet,
    get_counseling_sheet,
    get_personal_memo_sheet,
    get_activity_log_sheet,
    get_commission_sheet,
    append_row,
    update_cell,
    safe_update_cell,
    delete_row,
    get_gsheet_data,
    get_rows_from_sheet,
)

# --------------------------
# 메모 관련 (utils_memo)
# --------------------------
from .utils_memo import (
    get_memo_results,
    format_memo_results,
    filter_results_by_member,
    handle_search_memo,
)

# --------------------------
# OpenAI 관련 (utils_openai)
# --------------------------
from .utils_openai import (
    extract_order_from_uploaded_image,
    parse_order_from_text,
)

# --------------------------
# 검색 관련 (utils_search)
# --------------------------
from .utils_search import (
    searchMemberByNaturalText,
    fallback_natural_search,
    find_member_in_text,
)

# --------------------------------------------------
# 공식 공개 API (__all__)
# --------------------------------------------------
__all__ = [
    # 날짜/시간
    "now_kst", "process_order_date", "parse_dt",

    # 문자열 처리
    "clean_content", "clean_tail_command", "clean_value_expression",
    "remove_josa", "remove_spaces", "split_to_parts",
    "is_match", "match_condition",

    # Google Sheets
    "get_sheet", "get_worksheet", "get_member_sheet",
    "get_product_order_sheet", "get_counseling_sheet",
    "get_personal_memo_sheet", "get_activity_log_sheet",
    "get_commission_sheet", "append_row", "update_cell",
    "safe_update_cell", "delete_row", "get_gsheet_data", "get_rows_from_sheet",

    # 메모
    "get_memo_results", "format_memo_results",
    "filter_results_by_member", "handle_search_memo",

    # OpenAI
    "extract_order_from_uploaded_image", "parse_order_from_text",

    # 검색
    "searchMemberByNaturalText", "fallback_natural_search", "find_member_in_text",
]


