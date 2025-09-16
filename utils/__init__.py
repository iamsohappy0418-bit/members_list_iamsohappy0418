"""
utils 패키지 초기화 파일
공식적으로 공개되는 유틸 함수만 __all__에 정의
"""

# =====================================================
# http (외부 API 연동)
# =====================================================
from .http import (
    MemberslistError, ImpactError,
    call_memberslist_add_orders, call_impact_sync,
)

# =====================================================
# sheets (Google Sheets + OpenAI Vision)
# =====================================================
from .sheets import (
    get_sheet,
    get_gspread_client, 
    get_spreadsheet, 
    get_worksheet,
    get_rows_from_sheet, 
    append_row, 
    update_cell, 
    delete_row,
    safe_update_cell, 
    header_maps,
    get_db_sheet, 
    get_member_sheet, 
    get_product_order_sheet,
    get_counseling_sheet, 
    get_personal_memo_sheet,
    get_activity_log_sheet, 
    get_commission_sheet,
    get_image_sheet, 
    get_backup_sheet,
    get_member_info, 
    get_gsheet_data,
    openai_vision_extract_orders,
)

# =====================================================
# utils (날짜/문자열/검색/메모/GPT/실행)
# =====================================================
from .utils import (
    # 날짜/시간
    now_kst, process_order_date, parse_dt,
    # 문자열 처리
    remove_josa, remove_spaces, split_to_parts,
    clean_tail_command, clean_value_expression,
    clean_content, build_member_query,
    normalize_code_query, clean_member_query,
    is_match, match_condition,
    # 검색
    normalize_query, fallback_natural_search,
    search_members, find_all_members_from_sheet,
    parse_natural_query, searchMemberByNaturalText,
    search_member, find_member_in_text,
    # 메모
    get_memo_results, format_memo_results,
    filter_results_by_member, handle_search_memo,
    # Plugin client
    call_searchMemo, call_searchMemoFromText,
    # 회원 파서
    infer_member_field, parse_natural_query_multi,
    # 실행 유틸
    run_intent_func,
    # GPT 활용
    extract_order_from_uploaded_image, parse_order_from_text,
)

# --------------------------------------------------
# 공식 공개 API (__all__)
# --------------------------------------------------
__all__ = [
    # http
    "MemberslistError", "ImpactError",
    "call_memberslist_add_orders", "call_impact_sync",

    # sheets
    "get_sheet","get_gspread_client", "get_spreadsheet", "get_worksheet",
    "get_rows_from_sheet", "append_row", "update_cell", "delete_row",
    "safe_update_cell", "header_maps",
    "get_db_sheet", "get_member_sheet", "get_product_order_sheet",
    "get_counseling_sheet", "get_personal_memo_sheet",
    "get_activity_log_sheet", "get_commission_sheet",
    "get_image_sheet", "get_backup_sheet",
    "get_member_info", "get_gsheet_data",
    "openai_vision_extract_orders",

    # utils
    "now_kst", "process_order_date", "parse_dt",
    "remove_josa", "remove_spaces", "split_to_parts",
    "clean_tail_command", "clean_value_expression",
    "clean_content", "build_member_query",
    "normalize_code_query", "clean_member_query",
    "is_match", "match_condition",
    "normalize_query", "fallback_natural_search",
    "search_members", "find_all_members_from_sheet",
    "parse_natural_query", "searchMemberByNaturalText",
    "search_member", "find_member_in_text",
    "get_memo_results", "format_memo_results",
    "filter_results_by_member", "handle_search_memo",
    "call_searchMemo", "call_searchMemoFromText",
    "infer_member_field", "parse_natural_query_multi",
    "run_intent_func",
    "extract_order_from_uploaded_image", "parse_order_from_text",
]



from .sheets import get_product_order_sheet

def get_order_sheet():
    """구 함수명 호환용"""
    return get_product_order_sheet()

__all__.append("get_order_sheet")

