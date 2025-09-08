# ===== stdlib =====
import os
import re
import json
import traceback
from datetime import datetime, timedelta, timezone

# ===== 3rd party =====
import requests
from flask import Flask, request, jsonify, Response, g, send_from_directory
from flask_cors import CORS

# ===== project: config =====
from config import (
    API_URLS, HEADERS,
    GOOGLE_SHEET_TITLE, SHEET_KEY,
    OPENAI_API_KEY, OPENAI_API_URL, MEMBERSLIST_API_URL, openai_client,
    SHEET_MAP,
)

# ===== routes (intent 기반 공식 API만 import) =====
from routes import (
    # 회원
    search_member_func, register_member_func,
    update_member_func, save_member_func, delete_member_func,

    # 메모
    memo_save_auto_func, add_counseling_func,
    search_memo_func, search_memo_from_text_func, memo_find_auto_func,

    # 주문
    order_auto_func, order_upload_func,
    order_nl_func, save_order_proxy_func,

    # 후원수당
    commission_find_auto_func, find_commission_func, search_commission_by_nl_func,

    # intent 맵
    INTENT_MAP, MEMBER_INTENTS, MEMO_INTENTS,
    ORDER_INTENTS, COMMISSION_INTENTS,
)

# ===== utils (공식 API만 import) =====
from utils import (
    # 날짜/시간
    now_kst, process_order_date, parse_dt,
    # 문자열 정리
    clean_content, clean_tail_command, clean_value_expression,
    remove_josa, remove_spaces, split_to_parts, is_match, match_condition,
    # 시트
    get_sheet, get_worksheet, get_member_sheet, get_product_order_sheet,
    get_commission_sheet, get_counseling_sheet, get_personal_memo_sheet,
    get_activity_log_sheet, append_row, update_cell, safe_update_cell,
    delete_row, get_gsheet_data, get_rows_from_sheet,
    # 메모
    get_memo_results, format_memo_results, filter_results_by_member,
    handle_search_memo,
    # OpenAI
    extract_order_from_uploaded_image, parse_order_from_text,
    # 검색
    searchMemberByNaturalText, fallback_natural_search, find_member_in_text,
)

# ===== parser =====
from parser import (
    parse_registration, parse_request_and_update,
    parse_natural_query, parse_deletion_request,
    parse_memo, parse_commission,
    parse_order_text, parse_order_text_rule, parse_order_from_text,
    parse_request_line, process_date, clean_commission_data,
    field_map,
)

# ===== service =====
from service import (
    # 회원
    find_member_internal, clean_member_data, register_member_internal,
    update_member_internal, delete_member_internal,
    delete_member_field_nl_internal, process_member_query,
    # 주문
    addOrders, handle_order_save, handle_product_order, find_order,
    register_order, update_order, delete_order, delete_order_by_row,
    clean_order_data, save_order_to_sheet,
    # 메모
    save_memo, find_memo, search_in_sheet, search_memo_core,
    # 후원수당
    find_commission, register_commission, update_commission, delete_commission,
)









from utils.text_cleaner import normalize_code_query




# --------------------------------------------------
# Google Sheets
# --------------------------------------------------
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME", "DB")
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT", "credentials.json")

# --------------------------------------------------
# OpenAI
# --------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = os.getenv("OPENAI_API_URL")
PROMPT_ID = os.getenv("PROMPT_ID")
PROMPT_VERSION = os.getenv("PROMPT_VERSION")

# --------------------------------------------------
# Memberslist API
# --------------------------------------------------
MEMBERSLIST_API_URL = os.getenv("MEMBERSLIST_API_URL")


# ✅ Flask 초기화
app = Flask(__name__)
CORS(app)  # ← 추가

# --------------------------------------------------
# 📌 OpenAPI 스펙 반환
# --------------------------------------------------
with open("openapi.json", "r", encoding="utf-8") as f:
    openapi_spec = json.load(f)

@app.route("/openapi.json", methods=["GET"])
def openapi():
    """OpenAPI 스펙(JSON) 반환"""
    return jsonify(openapi_spec)

# --------------------------------------------------
# 📌 플러그인 manifest 반환
# --------------------------------------------------
@app.route('/.well-known/ai-plugin.json')
def serve_ai_plugin():
    """ChatGPT 플러그인 manifest 파일 반환"""
    return send_from_directory('.well-known', 'ai-plugin.json', mimetype='application/json')

# --------------------------------------------------
# 📌 로고 반환
# --------------------------------------------------
@app.route("/logo.png", methods=["GET"])
def plugin_logo():
    """플러그인 로고 이미지 반환"""
    return send_from_directory(".", "logo.png", mimetype="image/png")








# ✅ 확인용 출력 (선택)
if os.getenv("DEBUG", "false").lower() == "true":
    print("✅ GOOGLE_SHEET_TITLE:", os.getenv("GOOGLE_SHEET_TITLE"))
    print("✅ GOOGLE_SHEET_KEY 존재 여부:", "Yes" if os.getenv("GOOGLE_SHEET_KEY") else "No")


# --------------------------------------------------
# 📌 헬스체크
# --------------------------------------------------
# ✅ 홈 라우트
@app.route("/")
def home():
    """
    홈(Health Check) API
    📌 설명:
    서버가 정상 실행 중인지 확인하기 위한 기본 엔드포인트입니다.
    """
    return "Flask 서버가 실행 중입니다."


# ======================================================================================
# 추가 부분
# ======================================================================================
@app.route("/debug_sheets", methods=["GET"])
def debug_sheets():
    """현재 연결된 구글 시트 목록과 특정 시트의 헤더 확인"""
    try:
        sheet = get_sheet()
        sheet_names = [ws.title for ws in sheet.worksheets()]

        # ?sheet=DB 파라미터 있으면 해당 시트의 헤더 반환
        target = request.args.get("sheet")
        headers = []
        if target:
            ws = get_worksheet(target)
            headers = ws.row_values(1)

        return jsonify({
            "sheets": sheet_names,
            "headers": headers
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    




# ======================================================================================
# ======================================================================================
# ======================================================================================
# ======================================================================================
# ======================================================================================
# ======================================================================================
# ===============================================
# intent 추측 함수 (반환값 = 실행 함수 이름과 동일)
# ===============================================
def guess_intent(text: str) -> str:
    """
    자연어 문장에서 intent 추측
    반환값은 실제 실행 함수 이름과 동일하게 반환
    """
    text = (text or "").strip().lower()

    # ✅ 코드 검색
    if text.startswith("코드"):
        return "search_by_code_logic"

    # 회원 조회 (단순 이름)
    if re.fullmatch(r"[가-힣]{2,4}", text):   # 2~4자 한글 이름
        return "find_member_logic"

    # ✅ 회원 등록
    if any(k in text for k in ["회원등록", "회원 추가", "회원가입"]):
        return "register_member_func"

    # ✅ 회원 수정
    if any(k in text for k in ["회원 수정", "변경", "바꿔", "업데이트"]):
        return "update_member_func"

    # ✅ 회원 저장 (업서트)
    if any(k in text for k in ["저장", "업서트", "등록 또는 수정"]):
        return "save_member_func"

    # ✅ 회원 삭제 (전체 행 삭제)
    if any(k in text for k in ["회원 삭제", "삭제", "지워", "제거"]):
        return "delete_member_func"

    # ✅ 회원 필드 삭제 (특정 항목 제거)
    if any(k in text for k in ["필드 삭제", "항목 삭제", "정보 삭제"]):
        return "delete_member_field_nl_func"

    # ✅ 회원 조회 (일반 이름/검색/조회/알려줘)
    if "회원" in text or any(k in text for k in ["조회", "검색", "알려줘"]):
        return "find_member_logic"

    # ✅ 주문
    if "주문" in text:
        return "order_auto_func"

    # ✅ 메모/일지
    if any(k in text for k in ["상담일지", "개인일지", "활동일지", "메모"]):
        return "memo_save_auto_func"

    # ✅ 후원수당
    if any(k in text for k in ["후원수당", "수당"]):
        return "commission_find_auto_func"

    return "unknown"


# ======================================================================================
# ======================================================================================
# ======================================================================================
# ======================================================================================
# --------------------------------------------------
# 요청 전처리
# --------------------------------------------------
@app.before_request
def preprocess_input():
    """
    모든 요청에서 text/query 입력을 정규화해서 g.query 에 저장
    g.query 구조:
    {
        "query": 변환된 쿼리,
        "intent": 추정된 의도,
        "raw_text": 원본 입력
    }
    """
    data = {}
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
    elif request.method == "GET":
        data = request.args.to_dict()

    raw_text = None
    query, intent = None, None

    # ✅ PC 입력 (query 직접 전달)
    if "query" in data:
        query = data.get("query")
        if isinstance(query, str):
            raw_text = query.strip()
        else:
            raw_text = json.dumps(query, ensure_ascii=False)
        intent = None  # PC 입력은 intent 추정 안 함

    # ✅ 자연어 입력 (NLU 처리)
    elif "text" in data and data["text"].strip():
        raw_text = data["text"].strip()
        parsed = nlu_to_pc_input(raw_text)
        query = parsed.get("query")
        intent = parsed.get("intent")

    g.query = {
        "query": query,
        "intent": intent,
        "raw_text": raw_text
    }



# ======================================================================================
# ======================================================================================
# ======================================================================================
# ======================================================================================

def nlu_to_pc_input(text: str) -> dict:
    """
    자연어 입력을 PC 입력 방식(query dict)으로 변환
    query + intent 동시 반환
    """
    text = (text or "").strip()

    # ✅ 코드 검색 (코드a, 코드 b, 코드AA, 코드ABC ...)
    normalized = normalize_code_query(text)
    if normalized.startswith("코드"):
        return {"query": normalized, "intent": "search_member"}

    # ✅ 회원명 검색 ("홍길동 회원", "회원 홍길동")
    match = re.search(r"([가-힣]{2,4})\s*회원", text)
    if match:
        return {"query": {"회원명": match.group(1)}, "intent": "search_member"}

    # ✅ 회원번호 (12345, 1234567, 98765432) - 숫자 5~8자리
    match = re.fullmatch(r"\d{5,8}", text)
    if match:
        return {"query": f"{{ 회원번호: '{match.group(0)}' }}", "intent": "search_member"}

    # ✅ 휴대폰번호 (01012345678, 010-1234-5678) - 010으로 시작, 10~11자리 / 하이픈 허용
    match = re.fullmatch(r"(010-\d{3,4}-\d{4}|010\d{7,8})", text)
    if match:
        return {"query": f"{{ 휴대폰번호: '{match.group(0)}' }}", "intent": "search_member"}

    # ✅ 특수번호 검색 ("특수번호 77", "특수번호 ABC123", "특수번호 @12")
    match = re.search(r"특수번호\s*([a-zA-Z0-9!@#]+)", text)
    if match:
        return {"query": f"{{ 특수번호: '{match.group(1)}' }}", "intent": "search_member"}

    # ✅ 단순 이름 입력 ("홍길동", "이수민")
    if re.fullmatch(r"[가-힣]{2,4}", text):
        return {"query": f"{{ 회원명: '{text}' }}", "intent": "search_member"}

    # ✅ 회원 등록 ("회원등록 홍길동 12345678 010-1234-5678")
    if text.startswith("회원등록"):
        return {"query": text, "intent": "register_member"}

    # ✅ 회원 삭제 ("홍길동 삭제", "회원 홍길동 삭제")
    if "삭제" in text:
        match = re.search(r"([가-힣]{2,4}).*삭제", text)
        if match:
            return {"query": {"회원명": match.group(1)}, "intent": "delete_member"}
        return {"query": text, "intent": "delete_member"}

    # ✅ 회원 저장 (업서트) ("회원 저장 홍길동", "회원 저장 정보 수정")
    if text.startswith("회원 저장") or "회원 저장" in text:
        return {"query": text, "intent": "save_member"}







    # ✅ 주문 ("홍길동 주문", "이수민 제품 주문", "주문 내역")
    if "주문" in text:
        match = re.search(r"([가-힣]{2,4}).*주문", text)
        if match:
            return {"query": f"{{ 주문회원: '{match.group(1)}' }}", "intent": "order_find_auto"}
        return {"query": "{ 주문: true }", "intent": "order"}








    # ✅ 메모/일지 자동 분기 ("홍길동 상담일지 저장 오늘 미팅 진행", "활동일지 등록")
    if any(k in text for k in ["메모", "상담일지", "개인일지", "활동일지"]):
        return {"query": "{ 메모: true }", "intent": "memo_find_auto"}

    # ✅ 메모 저장 (자연어 업서트) ("이태수 메모 저장 운동 시작", "기록 저장 헬스 다녀옴")
    if any(k in text for k in ["메모 저장", "일지 저장", "기록 저장"]):
        return {"query": {"요청문": text}, "intent": "memo_save_auto"}

    # ✅ 메모 저장 (JSON 전용) ("상담일지 저장 고객과 통화", "개인일지 저장 PT 수업")
    if any(k in text for k in ["상담일지", "개인일지", "활동일지"]) and "저장" in text:
        return {"query": {"요청문": text}, "intent": "add_counseling"}

    # ✅ 메모 검색 (자연어) ("홍길동 상담일지 검색", "메모 검색 운동 관련")
    if "메모 검색" in text or "일지 검색" in text:
        return {"query": {"text": text}, "intent": "search_memo_from_text"}

    # ✅ 메모 검색 (JSON 기반) ("메모 조회", "일지 조회", "검색")
    if "메모 조회" in text or "일지 조회" in text or "검색" in text:
        return {"query": {"text": text}, "intent": "search_memo"}

    # ✅ 메모 자동 분기 (저장/검색 혼합 문장) ("홍길동 메모 저장 운동 시작", "홍길동 상담일지 검색")
    if any(k in text for k in ["메모", "상담일지", "개인일지", "활동일지"]):
        return {"query": {"text": text}, "intent": "memo_find_auto"}








    # ✅ 후원수당 조회 ("후원수당 조회", "홍길동 후원수당", "8월 후원수당")
    if "후원수당" in text:
        return {"query": "{ 후원수당: true }", "intent": "commission_find_auto"}

    # ✅ 기본 반환 (그대로 넘김)
    return {"query": text, "intent": "unknown"}



# ======================================================================================
# ======================================================================================
# ======================================================================================
# ======================================================================================

@app.route("/guess_intent", methods=["POST"])
def guess_intent_entry():
    """자연어 intent 추출 후 해당 함수 실행"""
    if not g.query or not g.query.get("intent"):
        return jsonify({"status": "error", "message": "❌ intent를 추출할 수 없습니다."}), 400

    intent = g.query["intent"]
    func = INTENT_MAP.get(intent)

    if not func:
        return jsonify({"status": "error", "message": f"❌ 처리할 수 없는 intent입니다. (intent={intent})"}), 400

    result = func()
    if isinstance(result, dict):
        return jsonify(result), result.get("http_status", 200)
    if isinstance(result, list):
        return jsonify(result), 200
    return jsonify({"status": "error", "message": "알 수 없는 반환 형식"}), 500

















# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

# ======================================================================================
# ✅ 회원 조회 자동 분기 API intent 기반 단일 라우트
# ======================================================================================
# ✅ 회원 조회 자동 분기 API
@app.route("/member", methods=["POST"])
def member_route():
    """
    회원 관련 API (intent 기반 단일 라우트)
    - before_request 에서 g.query["intent"] 세팅됨
    """
    intent = g.query.get("intent")
    func = MEMBER_INTENTS.get(intent)

    if not func:
        result = {
            "status": "error",
            "message": f"❌ 처리할 수 없는 회원 intent입니다. (intent={intent})",
            "http_status": 400
        }
    else:
        result = func()

    return jsonify(result), result.get("http_status", 200)



# ======================================================================================
# ✅ 일지 & 메모 (자동 분기) intent 기반 단일 라우트
# ======================================================================================
@app.route("/memo", methods=["POST"])
def memo_route():
    """
    메모 관련 API (저장/검색 자동 분기)
    - before_request 에서 g.query 세팅됨
    - g.query["intent"] 값에 따라 실행
    """
    try:
        intent = g.query.get("intent")
        func = MEMO_INTENTS.get(intent)

        if not func:
            result = {
                "status": "error",
                "message": f"❌ 처리할 수 없는 메모 intent입니다. (intent={intent})",
                "http_status": 400
            }
        else:
            result = func()

        if isinstance(result, dict):
            return jsonify(result), result.get("http_status", 200)
        
        if isinstance(result, list):
            return jsonify(result), 200

        return jsonify({"status": "error", "message": "알 수 없는 반환 형식"}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"메모 처리 중 오류 발생: {str(e)}"
        }), 500
    






# ======================================================================================
# ✅ 제품주문 (자동 분기) intent 기반 단일 라우트
# ======================================================================================
@app.route("/order", methods=["POST"])
def order_route():
    """
    주문 관련 API (intent 기반 단일 엔드포인트)
    - before_request 에서 g.query["intent"] 세팅됨
    """
    try:
        intent = g.query.get("intent") if hasattr(g, "query") else None
        func = ORDER_INTENTS.get(intent)

        if not func:
            result = {
                "status": "error",
                "message": f"❌ 처리할 수 없는 주문 intent입니다. (intent={intent})",
                "http_status": 400
            }
        else:
            result = func()

        if isinstance(result, dict):
            return jsonify(result), result.get("http_status", 200)
        
        if isinstance(result, list):  # 조회 결과 같은 경우
            return jsonify(result), 200

        return jsonify({"status": "error", "message": "알 수 없는 반환 형식"}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"주문 처리 중 오류 발생: {str(e)}"
        }), 500





# ======================================================================================
# ✅ 후원수당 조회 (자동 분기) intent 기반 단일 라우트
# ======================================================================================


@app.route("/commission", methods=["POST"])
def commission_route():
    """
    후원수당 관련 API (intent 기반 단일 엔드포인트)
    - before_request 에서 g.query["intent"] 세팅됨
    """
    try:
        intent = g.query.get("intent") if hasattr(g, "query") else None
        func = COMMISSION_INTENTS.get(intent)

        if not func:
            result = {
                "status": "error",
                "message": f"❌ 처리할 수 없는 후원수당 intent입니다. (intent={intent})",
                "http_status": 400
            }
        else:
            result = func()

        if isinstance(result, dict):
            return jsonify(result), result.get("http_status", 200)

        return jsonify({"status": "error", "message": "알 수 없는 반환 형식"}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"후원수당 처리 중 오류 발생: {str(e)}"
        }), 500



# 장됨








if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)


