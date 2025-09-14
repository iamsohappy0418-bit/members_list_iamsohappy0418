# =================================================
# 표준 라이브러리
# =================================================
import os
import re
import json
import traceback
import unicodedata
import inspect   # ✅ 이거 추가
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple



# =================================================
# 외부 라이브러리
# =================================================
import requests
from flask import Flask, request, jsonify, Response, g, send_from_directory
from flask_cors import CORS

# =================================================
# 프로젝트: config
# =================================================
from config import (
    API_URLS, HEADERS,
    GOOGLE_SHEET_TITLE, SHEET_KEY,
    OPENAI_API_KEY, OPENAI_API_URL, MEMBERSLIST_API_URL, openai_client,
    SHEET_MAP,
)

# =================================================
# 프로젝트: parser
# =================================================
from parser import (
    guess_intent,
    preprocess_user_input,
)

# =================================================
# 프로젝트: service
# =================================================
from service import (
    # 회원
    find_member_internal, clean_member_data,
    register_member_internal, update_member_internal,
    delete_member_internal, delete_member_field_nl_internal,
    process_member_query,

    # 주문
    addOrders, handle_order_save, handle_product_order,
    find_order, register_order, update_order,
    delete_order, delete_order_by_row, clean_order_data,
    save_order_to_sheet,

    # 메모
    save_memo, find_memo, search_in_sheet, search_memo_core,

    # 후원수당
    find_commission, register_commission,
    update_commission, delete_commission,
)

# =================================================
# 프로젝트: utils
# =================================================
from utils import (
    normalize_code_query,
    clean_member_query,
    now_kst, search_member, run_intent_func,
    call_searchMemo, openai_vision_extract_orders,
)

# =================================================
# 프로젝트: routes
# =================================================
from routes import (
    # 회원
    search_member_func,
    call_member,
    register_member_func,
    update_member_func,
    save_member_func,
    delete_member_func,
    member_select,
    member_select_direct,
    find_member_logic,
    sort_fields_by_field_map,
    get_full_member_info,
    get_summary_info,
    get_compact_info,

    # 메모
    memo_save_auto_func,
    add_counseling_func,
    search_memo_func,
    search_memo_from_text_func,
    memo_find_auto_func,

    # 주문
    order_auto_func,
    order_upload_func,
    order_nl_func,
    save_order_proxy_func,

    # 후원수당
    commission_find_auto_func,
    find_commission_func,
    search_commission_by_nl_func,
)

# intent 매핑은 routes.intent_map 에서만 import
from routes.intent_map import (
    INTENT_MAP,
    MEMBER_INTENTS,
    MEMO_INTENTS,
    ORDER_INTENTS,
    COMMISSION_INTENTS,
)












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











# --------------------------------------------------
# 공통 실행 유틸
# --------------------------------------------------
def run_intent_func(func, query=None, options=None):
    """함수 시그니처 검사 후 안전하게 실행"""
    sig = inspect.signature(func)
    if len(sig.parameters) == 0:
        return func()
    elif len(sig.parameters) == 1:
        return func(query)
    else:
        return func(query, options)







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






def preprocess_member_query(text: str) -> str:
    """
    회원 검색용 전처리
    - 회원번호, 휴대폰번호, 한글 이름 감지
    - 불필요한 접두어("회원검색")는 붙이지 않고 원래 값 그대로 반환
    """
    text = (text or "").strip()

    # 1. 회원번호 (숫자만)
    if text.isdigit():
        print(f"[preprocess_member_query] 회원번호 감지 → {text}")
        return text

    # 2. 휴대폰 번호 (010-xxxx-xxxx or 010xxxxxxxx)
    phone_pattern = r"^010[-]?\d{4}[-]?\d{4}$"
    if re.fullmatch(phone_pattern, text):
        print(f"[preprocess_member_query] 휴대폰번호 감지 → {text}")
        return text

    # 3. 한글 이름 (2~4자)
    name_pattern = r"^[가-힣]{2,4}$"
    if re.fullmatch(name_pattern, text):
        print(f"[preprocess_member_query] 한글이름 감지 → {text}")
        return text

    # 4. 기본 (변경 없음)
    print(f"[preprocess_member_query] 보정 없음 → {text}")
    return text



# --------------------------------------------------------------------
# postIntent (자연어 입력 전용 공식 진입점)
# --------------------------------------------------------------------
@app.route("/postIntent", methods=["POST"])
def post_intent():
    data = request.get_json(silent=True) or {}

    text = data.get("text") if isinstance(data.get("text"), str) else data.get("query")
    if not isinstance(text, str):
        text = ""
    text = text.strip()

    if not text:
        return jsonify({"status": "error", "message": "❌ text 또는 query 필드가 필요합니다."}), 400

    text = clean_member_query(text)
    text = preprocess_member_query(text)

    print(f"[DEBUG] 최종 전처리 query: {text}")

    normalized_query = text
    options = {}
    intent = guess_intent(normalized_query)

    g.query = {
        "query": normalized_query,
        "options": options,
        "intent": intent,
    }

    try:
        # ✅ 전체정보/상세 요청 처리
        if intent == "member_select":
            import re
            # "강소희 전체정보", "강소희 상세" 지원
            name_match = re.match(r"([가-힣]{2,4})(?:\s*(전체정보|상세))?", normalized_query)
            if name_match:
                member_name = name_match.group(1)
                print(f"[AUTO] 세션 없이 '{member_name}' 전체정보 검색 시도")

                results = find_member_logic(member_name)
                if results.get("status") == "success":
                    return jsonify({
                        "status": "success",
                        "message": "회원 전체정보입니다.",
                        "results": results["results"],
                        "http_status": 200
                    }), 200
                else:
                    return jsonify(results), results.get("http_status", 400)




            return jsonify({
                "status": "error",
                "message": "회원 이름을 추출할 수 없습니다.",
                "http_status": 400
            })

        # ✅ 일반 intent 실행
        func = INTENT_MAP.get(intent)
        if not func:
            return jsonify({
                "status": "error",
                "message": f"❌ 처리할 수 없는 intent입니다. (intent={intent})"
            }), 400

        result = run_intent_func(func, normalized_query, options)
        return jsonify(result), result.get("http_status", 200)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"post_intent 처리 중 오류 발생: {str(e)}"
        }), 500







# -------------------------------
# guess_intent 엔드포인트
# -------------------------------
@app.route("/guess_intent", methods=["POST"])
def guess_intent_entry():
    data = request.json
    user_input = data.get("query", "")

    if not user_input:
        return jsonify({"status": "error", "message": "❌ 입력(query)이 비어 있습니다."}), 400

    # 1. 전처리: query 정규화
    processed = preprocess_user_input(user_input)
    normalized_query = processed["query"]
    options = processed["options"]

    # 2. intent 추출
    intent = guess_intent(normalized_query)

    if not intent or intent == "unknown":
        return jsonify({"status": "error", "message": f"❌ intent를 추출할 수 없습니다. (query={normalized_query})"}), 400

    # 3. intent → 실행 함수 매핑
    func = INTENT_MAP.get(intent)
    if not func:
        return jsonify({"status": "error", "message": f"❌ 처리할 수 없는 intent입니다. (intent={intent})"}), 400

    # 4. 실행
    result = run_intent_func(func, normalized_query, options)  # ✅ 올바른 실행

    if isinstance(result, dict):
        return jsonify(result), result.get("http_status", 200)
    if isinstance(result, list):
        return jsonify(result), 200
    return jsonify({"status": "error", "message": "알 수 없는 반환 형식"}), 500

























# ======================================================================================
# ======================================================================================
# ======================================================================================
# ======================================================================================
def nlu_to_pc_input(text: str) -> dict:
    """
    자연어 입력을 intent + query(dict) 구조로 변환
    - guess_intent + nlu_to_pc_input 통합
    - 회원 / 메모 / 주문 intent 지원
    """
    text = (text or "").strip()

    # -------------------------------
    # 회원 관련
    # -------------------------------

    # 회원 등록
    if any(word in text for word in ["회원등록", "회원추가", "회원 등록", "회원 추가"]):
        # 앞쪽에 이름이 붙은 경우 처리: "이판주 회원등록"
        m = re.search(r"([가-힣]{2,4})\s*(회원등록|회원추가|회원 등록|회원 추가)", text)
        if m:
            return {"intent": "register_member", "query": {"회원명": m.group(1)}}
        # 뒷쪽에 이름이 오는 경우 처리: "회원등록 이판주"
        m = re.search(r"(회원등록|회원추가|회원 등록|회원 추가)\s*([가-힣]{2,4})", text)
        if m:
            return {"intent": "register_member", "query": {"회원명": m.group(2)}}
        # 회원명 못 찾으면 raw_text만 전달
        return {"intent": "register_member", "query": {"raw_text": text}}

    # 회원 수정
    if any(word in text for word in ["수정", "회원수정", "회원변경", "회원 수정", "회원 변경"]):
        # 케이스1: "<이름> 수정 <내용>"
        m = re.match(r"^([가-힣]{2,4})\s*(?:회원)?\s*(?:수정|변경)\s+(.+)$", text)
        if m:
            member_name, request_text = m.groups()
            field = None
            value = None

            # 필드 추출 패턴
            if "휴대폰" in request_text or "전화" in request_text:
                field = "휴대폰번호"
                value = re.sub(r"[^0-9\-]", "", request_text)  # 숫자/하이픈만 추출
            elif "주소" in request_text:
                field = "주소"
                value = request_text.replace("주소", "").strip()
            elif "이메일" in request_text or "메일" in request_text:
                field = "이메일"
                value = re.search(r"[\w\.-]+@[\w\.-]+", request_text)
                if value:
                    value = value.group(0)

            query = {"회원명": member_name, "요청문": request_text}
            if field and value:
                query.update({"필드": field, "값": value})

            return {"intent": "update_member", "query": query}

        # 케이스2: "회원수정 <이름> <내용>"
        m = re.match(r"^(?:회원)?\s*(?:수정|변경)\s*([가-힣]{2,4})\s+(.+)$", text)
        if m:
            member_name, request_text = m.groups()
            return {"intent": "update_member", "query": {"회원명": member_name, "요청문": request_text}}

        # fallback
        return {"intent": "update_member", "query": {"raw_text": text}}



    # 회원 삭제
    if any(word in text for word in ["회원삭제", "회원제거", "회원 삭제", "회원 제거"]):
        m = re.search(r"([가-힣]{2,4}).*(삭제|제거)", text)
        if m:
            return {"intent": "delete_member", "query": {"회원명": m.group(1)}}
        return {"intent": "delete_member", "query": {"raw_text": text}}
    
    # 회원 조회 / 검색 (동의어 지원)
    if any(word in text for word in ["회원조회", "회원검색", "검색회원", "조회회원", "회원 조회", "회원 검색", "검색 회원", "조회 회원"]):
    # 이름까지 붙었는지 확인
        m = re.search(r"(회원\s*(검색|조회)\s*)([가-힣]{2,4})", text)
        if m:
            return {"intent": "search_member", "query": {"회원명": m.group(3)}}
        return {"intent": "search_member", "query": {"raw_text": text}}
    
    # 코드 검색 (코드a, 코드 b, 코드AA...)
    normalized = normalize_code_query(text)
    if normalized.startswith("코드"):
        return {"intent": "search_member", "query": {"코드": normalized}}

    # 회원명 + "회원"
    m = re.search(r"([가-힣]{2,4})\s*회원", text)
    if m:
        return {"intent": "search_member", "query": {"회원명": m.group(1)}}

    # 회원번호
    if re.fullmatch(r"\d{5,8}", text):
        return {"intent": "search_member", "query": {"회원번호": text}}

    # 휴대폰번호
    if re.fullmatch(r"(010-\d{3,4}-\d{4}|010\d{7,8})", text):
        return {"intent": "search_member", "query": {"휴대폰번호": text}}

    # 특수번호
    m = re.search(r"특수번호\s*([a-zA-Z0-9!@#]+)", text)
    if m:
        return {"intent": "search_member", "query": {"특수번호": m.group(1)}}

    # 단순 이름
    if re.fullmatch(r"[가-힣]{2,4}", text):
        return {"intent": "search_member", "query": {"회원명": text}}


    # -------------------------------
    # 메모/일지 관련
    # -------------------------------
    # 메모 저장
    m = re.match(r"(\S+)\s+(개인일지|상담일지|활동일지|개인 일지|상담 일지|활동 일지)\s+저장\s+(.+)", text)
    if m:
        member_name, diary_type, content = m.groups()
        return {"intent": "memo_add", "query": {"회원명": member_name, "일지종류": diary_type, "내용": content}}

    # 메모 검색 (회원명 + 일지종류 + 검색)
    m = re.match(r"(\S+)\s+(개인일지|상담일지|활동일지|개인 일지|상담 일지|활동 일지)\s+(검색|조회)\s+(.+)", text)
    if m:
        member_name, diary_type, _, keyword = m.groups()
        return {"intent": "memo_search", "query": {"회원명": member_name, "일지종류": diary_type, "검색어": keyword}}

    # 전체 메모 검색
    m = re.match(r"전체\s*(메모|일지)\s*(검색|조회)\s*(.+)", text)
    if m:
        keyword = m.group(3)
        return {"intent": "memo_search", "query": {"회원명": "전체", "일지종류": "전체", "검색어": keyword}}

    # -------------------------------
    # 주문 관련
    # -------------------------------
    if "주문" in text:
        if "저장" in text:
            return {"intent": "order_auto", "query": {"주문": True}}
        m = re.search(r"([가-힣]{2,4}).*주문", text)
        if m:
            return {"intent": "order_auto", "query": {"주문회원": m.group(1)}}
        return {"intent": "order_auto", "query": {"주문": True}}

    # -------------------------------
    # 회원 저장 (업서트)
    # -------------------------------
    if "회원 저장" in text or "저장" in text:
        return {"intent": "save_member", "query": {"raw_text": text}}

    # -------------------------------
    # 후원수당
    # -------------------------------
    if "후원수당" in text or "수당" in text:
        return {"intent": "commission_find", "query": {"raw_text": text}}

    # -------------------------------
    # 기본 반환
    # -------------------------------
    return {"intent": "unknown", "query": {"raw_text": text}}





























# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

# ======================================================================================
# ✅ 회원 조회 자동 분기 API intent 기반 단일 라우트
# ======================================================================================
# ✅ 회원 조회 자동 분기 API
@app.route("/member", methods=["POST"])
def member_route():
    """
    회원 관련 API (intent 기반 단일 라우트)
    - g.query["intent"] 가 있으면 그대로 실행
    - 없으면 자연어 입력 분석해서 search_member / select_member 자동 분기
    """
    # g.query 안전 체크
    data = getattr(g, "query", {}) or {}
    intent = data.get("intent")

    # ✅ intent가 없을 때만 자연어 판별 로직 적용
    if not intent:
        if isinstance(data.get("query"), str) and not any(k in data for k in ("회원명", "회원번호")):
            query_text = data.get("query", "").strip()

            # ✅ 자연어 자동 분기
            if "전체정보" in query_text or query_text in ["1", "상세", "detail", "info"]:
                intent = "select_member"
                g.query["choice"] = "1"
            elif "종료" in query_text or query_text in ["2", "끝", "exit", "quit"]:
                intent = "select_member"
                g.query["choice"] = "2"
            else:
                # 그 외는 자연어 intent 처리기로 우회
                return post_intent()

    # ✅ intent 기반 실행
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
    - 자연어 입력은 무조건 post_intent() 우회
    - JSON 입력은 구조 분석 → 저장 / 검색 분기
    """
    try:
        data = getattr(g, "query", {}) or {}

        # ✅ 자연어 입력(문자열) → post_intent 우회
        if isinstance(data, str):
            return post_intent()

        # ✅ JSON 입력 처리
        intent = data.get("intent")

        # intent가 없는 경우 JSON 구조로 자동 판별
        if not intent:
            if all(k in data for k in ("회원명", "내용", "일지종류")):
                intent = "memo_save_auto_func"
            elif "keywords" in data and "일지종류" in data:
                intent = "search_memo_func"

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


