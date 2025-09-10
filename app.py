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

# ===== intents (마스터 및 그룹 맵만 임포트) =====
from routes.intent_map import (
    INTENT_MAP,
    MEMBER_INTENTS,
    MEMO_INTENTS,
    ORDER_INTENTS,
    COMMISSION_INTENTS,
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
# --------------------------------------------------
# 요청 전처리
# --------------------------------------------------
@app.before_request
def preprocess_input():
    """
    1. /postIntent → 그대로 통과
    2. 다른 라우트에 자연어 입력이 들어오면 → /postIntent 로 우회
    """
    if request.endpoint == "post_intent":
        return None

    if request.method == "POST":
        data = request.get_json(silent=True) or {}

        # ✅ 문자열만 안전하게 뽑아서 strip
        q = data.get("text")
        if not isinstance(q, str):
            q = data.get("query") if isinstance(data.get("query"), str) else ""
        q = q.strip()

        # 구조화된 JSON이 아닌 경우 → 자연어로 간주
        if q and not ("회원명" in data or "회원번호" in data):
            return post_intent()  # ✅ postIntent로 강제 우회

    return None


# --------------------------------------------------------------------
# postIntent (자연어 입력 전용 공식 진입점)
# --------------------------------------------------------------------
@app.route("/postIntent", methods=["POST"])
def post_intent():
    data = request.get_json(silent=True) or {}

    # ✅ 문자열만 안전하게 추출
    text = data.get("text")
    if not isinstance(text, str):
        text = data.get("query") if isinstance(data.get("query"), str) else ""
    text = text.strip()

    if not text:
        return jsonify({"status": "error", "message": "❌ text 필드가 필요합니다."}), 400

    # ✅ 자연어 → { intent, query } 변환 (search_member 중심)
    g.query = nlu_to_pc_input(text)

    # ✅ 표준 실행기로 위임 (INTENT_MAP 사용)
    return guess_intent_entry()


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
        return {"query": {"코드": normalized}, "intent": "search_member"}

    # ✅ 회원명 검색 ("홍길동 회원", "회원 홍길동")
    match = re.search(r"([가-힣]{2,4})\s*회원", text)
    if match:
        return {"query": {"회원명": match.group(1)}, "intent": "search_member"}

    # ✅ 회원번호 (12345 ~ 8자리)
    match = re.fullmatch(r"\d{5,8}", text)
    if match:
        return {"query": {"회원번호": match.group(0)}, "intent": "search_member"}

    # ✅ 휴대폰번호 (010 시작, 하이픈 허용)
    match = re.fullmatch(r"(010-\d{3,4}-\d{4}|010\d{7,8})", text)
    if match:
        return {"query": {"휴대폰번호": match.group(0)}, "intent": "search_member"}

    # ✅ 특수번호 검색 ("특수번호 abc123")
    match = re.search(r"특수번호\s*([a-zA-Z0-9!@#]+)", text)
    if match:
        return {"query": {"특수번호": match.group(1)}, "intent": "search_member"}

    # ✅ 단순 이름 입력 ("홍길동", "이수민")
    if re.fullmatch(r"[가-힣]{2,4}", text):
        return {"query": {"회원명": text}, "intent": "search_member"}

    # ✅ 회원 등록
    if text.startswith("회원등록"):
        return {"query": {"raw_text": text}, "intent": "register_member"}

    # ✅ 회원 삭제
    if "삭제" in text:
        match = re.search(r"([가-힣]{2,4}).*삭제", text)
        if match:
            return {"query": {"회원명": match.group(1)}, "intent": "delete_member"}
        return {"query": {"raw_text": text}, "intent": "delete_member"}

    # ✅ 회원 저장 (업서트)
    if "회원 저장" in text or "저장" in text:
        return {"query": {"raw_text": text}, "intent": "save_member"}

    # ✅ 주문
    if "주문" in text:
        match = re.search(r"([가-힣]{2,4}).*주문", text)
        if match:
            return {"query": {"주문회원": match.group(1)}, "intent": "order_auto"}
        return {"query": {"주문": True}, "intent": "order_auto"}

    # ✅ 메모/일지 자동 분기
    if any(k in text for k in ["메모", "상담일지", "개인일지", "활동일지"]):
        # 세부 상황에 따라 intent 분기
        if "저장" in text:
            return {"query": {"요청문": text}, "intent": "memo_save_auto"}
        if "검색" in text:
            return {"query": {"text": text}, "intent": "search_memo_from_text"}
        return {"query": {"text": text}, "intent": "memo_find_auto"}

    # ✅ 후원수당
    if "후원수당" in text or "수당" in text:
        return {"query": {"raw_text": text}, "intent": "commission_find_auto"}

    # ✅ 기본 반환
    return {"query": {"raw_text": text}, "intent": "unknown"}




# ======================================================================================
# ======================================================================================
# ======================================================================================
# ======================================================================================

@app.route("/guess_intent", methods=["POST"])
def guess_intent_entry():
    if not g.query or not g.query.get("intent"):
        return jsonify({"status": "error", "message": "❌ intent를 추출할 수 없습니다."}), 400

    intent = g.query["intent"]
    func = INTENT_MAP.get(intent)   # ✅ 마스터 맵에서 실행 함수 가져옴

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
    - 자연어 입력이면 postIntent로 우회
    """
    # g.query 안전 체크
    data = getattr(g, "query", {}) or {}
    intent = data.get("intent")

    # ✅ intent가 없을 때만 자연어 판별 로직 적용
    if not intent:
        if isinstance(data.get("query"), str) and not any(k in data for k in ("회원명", "회원번호")):
            # 자연어면 postIntent로 강제 우회
            return post_intent()

    # 그 외에는 기존 intent 흐름 사용
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
    - 자연어 입력이면 postIntent로 우회
    """
    try:
        data = getattr(g, "query", {}) or {}

        # query가 문자열이고 JSON 구조화 키(회원명/내용 등)가 없으면 → 자연어로 간주
        if isinstance(data.get("query"), str) and not any(k in data for k in ("회원명", "내용", "일지종류")):
            return post_intent()  # ✅ 자연어라면 postIntent로 우회

        # intent 기반 실행
        intent = data.get("intent")
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
    - 자연어 입력이면 postIntent로 우회
    - 파일 업로드면 order_upload 바로 처리
    """
    try:
        # 0) 파일 업로드 우선 처리 (multipart/form-data)
        if hasattr(request, "files") and request.files:
            # g.query 보정 (없을 수 있음)
            if not hasattr(g, "query") or not isinstance(g.query, dict):
                g.query = {"intent": "order_upload", "query": {}}
            result = ORDER_INTENTS.get("order_upload", order_upload_func)()
            if isinstance(result, dict):
                return jsonify(result), result.get("http_status", 200)
            if isinstance(result, list):
                return jsonify(result), 200
            return jsonify({"status": "error", "message": "알 수 없는 반환 형식"}), 500

        data = getattr(g, "query", {}) or {}
        q = data.get("query")

        # 1) 자연어 판단: 문자열이거나, dict여도 text/요청문/주문문/내용만 있는 경우
        if isinstance(q, str):
            return post_intent()  # ✅ 자연어면 게이트웨이로 우회
        if isinstance(q, dict):
            # 구조화 주문 키 후보
            structured_keys = {"items", "상품", "order", "주문", "주문회원", "member", "수량", "결제", "date"}
            text_like_keys = {"text", "요청문", "주문문", "내용"}
            if any(k in q for k in text_like_keys) and not any(k in q for k in structured_keys):
                return post_intent()  # ✅ 텍스트성 dict → 자연어로 간주하여 우회

        # 2) intent 기반 실행
        intent = data.get("intent")
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
    - before_request 에서 g.query 세팅됨
    - 자연어 입력이면 postIntent로 우회
    """
    try:
        data = getattr(g, "query", {}) or {}
        q = data.get("query")

        # 1) 자연어 판별: 문자열이거나, dict여도 텍스트성 키만 있고 구조화 키가 없으면 자연어
        if isinstance(q, str):
            return post_intent()

        if isinstance(q, dict):
            text_like_keys = {"text", "요청문", "조건", "criteria"}
            structured_keys = {
                "회원", "회원명", "member",
                "월", "연도", "기간", "시작일", "종료일", "from", "to",
                "지급일", "구분", "유형"
            }
            if any(k in q for k in text_like_keys) and not any(k in q for k in structured_keys):
                return post_intent()

        # 2) intent 기반 실행
        intent = data.get("intent")
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
        if isinstance(result, list):
            return jsonify(result), 200

        return jsonify({"status": "error", "message": "알 수 없는 반환 형식"}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"후원수당 처리 중 오류 발생: {str(e)}"
        }), 500










if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)


