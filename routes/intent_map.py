# intent_groups.py (예시)
from routes.routes_member import (search_member_func,register_member_func, update_member_func,
                                  save_member_func, delete_member_func, search_by_code_logic)
from routes.routes_memo import (memo_save_auto_func, add_counseling_func,
                                  search_memo_func, search_memo_from_text_func, memo_find_auto_func)
from routes.routes_order import (order_auto_func, order_upload_func, order_nl_func, save_order_proxy_func)
from routes.routes_commission import (commission_find_auto_func, find_commission_func, search_commission_by_nl_func)

MEMBER_INTENTS = {
    "search_member": search_member_func,
    "register_member": register_member_func, 
    "update_member": update_member_func,
    "save_member": save_member_func,
    "delete_member": delete_member_func,
    "search_by_code_logic": search_by_code_logic,
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

INTENT_MAP = {
    **MEMBER_INTENTS,
    **MEMO_INTENTS,
    **ORDER_INTENTS,
    **COMMISSION_INTENTS,
}
