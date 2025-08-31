# ===== stdlib =====
import os
import io
import re
import base64
import traceback
from datetime import datetime, timedelta, timezone

# ===== 3rd party =====
import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# ===== project: config =====
from config import (
    API_URLS, HEADERS,
    GOOGLE_SHEET_TITLE, SHEET_KEY,
    OPENAI_API_KEY, OPENAI_API_URL, MEMBERSLIST_API_URL, openai_client,
    SHEET_MAP,
)

# ===== project: utils =====
from utils.common import (
    now_kst,
    process_order_date,
    remove_josa,
    remove_spaces,
    split_to_parts,
)
from utils.sheets import (
    get_sheet,
    get_worksheet,
    get_member_sheet,
    get_product_order_sheet,
    get_commission_sheet,
    append_row,
    update_cell,
    safe_update_cell,
    delete_row,
)
from utils.clean_content import clean_content
from utils.http import call_memberslist_add_orders, call_impact_sync
from utils.openai_utils import (
    extract_order_from_uploaded_image,
    parse_order_from_text,
)

# ===== parser: member =====
# ===== parser =====
from parser import (
    parse_registration,
    parse_request_and_update,
    parse_natural_query,
    parse_deletion_request,
    parse_order_text,
    parse_memo,
    parse_commission,
    guess_intent,
)


from service.member_service import (
    find_member_internal,
    clean_member_data,
    register_member_internal,
# update_member_internal,
# delete_member_internal,
# delete_member_field_nl_internal,
)

# ===== parser: order =====
from parser.order_parser import (
    parse_order_text,
    parse_order_text_rule,
    parse_order_from_text,
)
from service.order_service import (
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

# ===== parser: memo =====
from parser.memo_parser import (
    parse_memo,
    parse_request_line,
)
from service.memo_service import (
    save_memo,
    find_memo,
    search_in_sheet,
    # ⚠ search_memo_core → 구현 필요 (현재 없음)
)

# ===== parser: commission =====
from parser.commission_parser import (
    process_date,
    clean_commission_data,
)
from service.commission_service import (
    find_commission,
    register_commission,
    update_commission,
    delete_commission,
)

# ===== parser: intent =====
from parser.intent_parser import guess_intent

# ===== field map =====
from parser.field_map import field_map





# ✅ Flask 초기화
app = Flask(__name__)
CORS(app)  # ← 추가

# ✅ 확인용 출력 (선택)
if os.getenv("DEBUG", "false").lower() == "true":
    print("✅ GOOGLE_SHEET_TITLE:", os.getenv("GOOGLE_SHEET_TITLE"))
    print("✅ GOOGLE_SHEET_KEY 존재 여부:", "Yes" if os.getenv("GOOGLE_SHEET_KEY") else "No")



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
    """
    시트 디버그 API
    📌 설명:
    연결된 Google Sheet의 워크시트 목록을 반환합니다.
    📥 입력(JSON 예시):
    {}
    """

    try:
        sheet = get_sheet()
        sheet_names = [ws.title for ws in sheet.worksheets()]
        return jsonify({"sheets": sheet_names}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    

# ============================================================
# **주문 업로드(iPad/PC 공통 엔트리)**
# ============================================================












# ======================================================================================
# ✅ 회원 조회
# ======================================================================================
@app.route("/find_member", methods=["POST"])
def find_member_route():
    """
    회원 조회 API
    📌 설명:
    회원명 또는 회원번호를 기준으로 DB 시트에서 정보를 조회합니다.
    📥 입력(JSON 예시):
    {
    "회원명": "신금자"
    }
    """

    try:
        data = request.get_json()
        name = (
            data.get("회원명")
            or data.get("memberName")
            or data.get("name")
            or ""
        ).strip()

        number = (
            data.get("회원번호")
            or data.get("memberId")
            or data.get("id")
            or ""
        ).strip()


        if not name and not number:
            return jsonify({"error": "회원명 또는 회원번호를 입력해야 합니다."}), 400

        matched = find_member_internal(name, number)
        if not matched:
            return jsonify({"error": "해당 회원 정보를 찾을 수 없습니다."}), 404

        if len(matched) == 1:
            return jsonify(clean_member_data(matched[0])), 200
        return jsonify([clean_member_data(m) for m in matched]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


    




# ✅ 자연어 기반 회원 검색 API
@app.route("/members/search-nl", methods=["POST"])
def search_by_natural_language():
    """
    회원 자연어 검색 API
    📌 설명:
    자연어 문장에서 (필드, 키워드)를 추출하여 DB 시트에서 회원을 검색합니다.
    📥 입력(JSON 예시):
    {
    "query": "계보도 장천수 우측"
    }
    """

    data = request.get_json()
    query = data.get("query")
    if not query:
        return Response("query 파라미터가 필요합니다.", status=400)

    offset = int(data.get("offset", 0))  # ✅ 추가된 부분

    field, keyword = parse_natural_query(query)
    print("🔍 추출된 필드:", field)
    print("🔍 추출된 키워드:", keyword)

    if not field or not keyword:
        return Response("자연어에서 검색 필드와 키워드를 찾을 수 없습니다.", status=400)

    try:
        sheet = get_member_sheet()
        records = sheet.get_all_records()


        print("🧾 전체 키 목록:", records[0].keys())  # ← 여기!


        normalized_field = field.strip()
        normalized_keyword = keyword.strip().lower()



        if normalized_field == "계보도":
            normalized_keyword = normalized_keyword.replace(" ", "")





        # ✅ 디버깅 출력
        print("🧾 전체 키 목록:", records[0].keys() if records else "레코드 없음")
        for m in records:
            cell = str(m.get(normalized_field, "")).strip().lower()
            print(f"🔎 '{normalized_keyword}' == '{cell}' → {normalized_keyword == cell}")

        # ✅ 대소문자 구분 없이 정확히 일치
        filtered = [
            m for m in records
            if normalized_keyword == str(m.get(normalized_field, "")).strip().lower().replace(" ", "")
        ]


        # ✅ 이름순 정렬
        filtered.sort(key=lambda m: m.get("회원명", ""))




        lines = [
            f"{m.get('회원명', '')} (회원번호: {m.get('회원번호', '')}" +
            (f", 특수번호: {m.get('특수번호', '')}" if m.get('특수번호', '') else "") +
            (f", 연락처: {m.get('휴대폰번호', '')}" if m.get('휴대폰번호', '') else "") +
            (f", {remove_josa(str(m.get('코드', '')).strip())}" if m.get('코드', '') else "") +
            ")"
            for m in filtered[offset:offset+40]
        ]







        # ✅ 다음 있음 표시
        has_more = offset + 40 < len(filtered)
        if has_more:
            lines.append("--- 다음 있음 ---")

        response_text = "\n".join(lines) if lines else "조건에 맞는 회원이 없습니다."
        return Response(response_text, mimetype='text/plain')

    except Exception as e:
        return Response(f"[서버 오류] {str(e)}", status=500)



    


# ======================================================================================
# ✅ 회원 수정
# ======================================================================================
# ======================================================================================
# ✅ 회원 수정 라우트
# ======================================================================================
@app.route("/update_member", methods=["POST"])
@app.route("/updateMember", methods=["POST"])
def update_member_route():
    """
    회원 수정 API
    📌 설명:
    자연어 요청문에서 {필드: 값} 쌍을 추출하여 회원 정보를 수정합니다.
    📥 입력(JSON 예시):
    {
    "요청문": "홍길동 주소 부산 해운대구로 변경"
    }
    """

    try:
        data = request.get_json(force=True)
        요청문 = data.get("요청문", "").strip()

        if not 요청문:
            return jsonify({"error": "요청문이 비어 있습니다."}), 400

        return update_member_internal(요청문)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    






# ======================================================================================
# ✅ JSON 기반 회원 저장/수정 API
# ======================================================================================
@app.route('/save_member', methods=['POST'])
def save_member():
    """
    회원 저장/수정 API
    📌 설명:
    - 자연어 요청문을 파싱하여 회원을 신규 등록하거나 기존 회원 정보를 수정
    - 등록 시 회원명, 회원번호, 휴대폰번호만 반영
    📥 입력(JSON 예시):
    {
      "요청문": "홍길동 회원번호 12345 휴대폰 010-1111-2222"
    }
    """

    try:
        req = request.get_json()
        print(f"[DEBUG] 📥 요청 수신: {req}")

        요청문 = req.get("요청문") or req.get("회원명", "")
        if not 요청문:
            return jsonify({"error": "입력 문장이 없습니다"}), 400

        # ✅ 파싱 (회원명, 회원번호, 휴대폰번호만 추출)
        name, number, phone = parse_registration(요청문)
        if not name:
            return jsonify({"error": "회원명을 추출할 수 없습니다"}), 400

        # ✅ 시트 접근
        sheet = get_member_sheet()
        headers = [h.strip() for h in sheet.row_values(1)]
        rows = sheet.get_all_records()

        print(f"[DEBUG] 시트 헤더: {headers}")

        # ✅ 기존 회원 여부 확인
        for i, row in enumerate(rows):
            if str(row.get("회원명", "")).strip() == name:
                print(f"[INFO] 기존 회원 '{name}' 발견 → 수정")
                for key, value in {
                    "회원명": name,
                    "회원번호": number,
                    "휴대폰번호": phone,
                }.items():
                    if key in headers and value:
                        row_idx = i + 2
                        col_idx = headers.index(key) + 1
                        safe_update_cell(sheet, row_idx, col_idx, value, clear_first=True)

                return jsonify({"message": f"{name} 기존 회원 정보 수정 완료"}), 200

        # ✅ 신규 등록
        print(f"[INFO] 신규 회원 '{name}' 등록")
        new_row = [''] * len(headers)
        for key, value in {
            "회원명": name,
            "회원번호": number,
            "휴대폰번호": phone,
        }.items():
            if key in headers and value:
                new_row[headers.index(key)] = value

        sheet.insert_row(new_row, 2)
        return jsonify({"message": f"{name} 회원 신규 등록 완료"}), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500










# ======================================================================================
# ✅ 회원 등록 (라우트)
# ======================================================================================
@app.route("/register_member", methods=["POST"])
def register_member_route():
    """
    회원 등록 API
    📌 설명:
    회원명, 회원번호, 휴대폰번호를 JSON으로 입력받아 신규 등록합니다.
    📥 입력(JSON 예시):
    {
    "회원명": "홍길동",
    "회원번호": "12345",
    "휴대폰번호": "010-1111-2222"
    }
    """

    try:
        data = request.get_json()
        name = data.get("회원명", "").strip()
        number = data.get("회원번호", "").strip()
        phone = data.get("휴대폰번호", "").strip()

        if not name:
            return jsonify({"error": "회원명은 필수 입력 항목입니다."}), 400

        register_member_internal(name, number, phone)
        return jsonify({"message": f"{name}님이 성공적으로 등록되었습니다."}), 201

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    







# ======================================================================================
# ✅ 회원 삭제 API
# ======================================================================================
@app.route('/delete_member', methods=['POST'])
def delete_member_route():
    """
    회원 삭제 API
    📌 설명:
    회원명을 기준으로 해당 회원의 전체 정보를 삭제합니다.
    📥 입력(JSON 예시):
    {
    "회원명": "이판주"
    }
    """

    try:
        name = request.get_json().get("회원명")
        return delete_member_internal(name)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500












# ======================================================================================
# ✅ 자연어 요청 회원 삭제 라우트
# ======================================================================================
@app.route('/delete_member_field_nl', methods=['POST'])
def delete_member_field_nl():
    """
    회원 필드 삭제 API
    📌 설명:
    자연어 문장에서 특정 필드를 추출하여 해당 회원의 필드를 비웁니다.
    📥 입력(JSON 예시):
    {
    "요청문": "이판여 휴대폰번호 삭제"
    }
    """

    try:
        req = request.get_json(force=True)
        text = req.get("요청문", "").strip()

        if not text:
            return jsonify({"error": "요청문을 입력해야 합니다."}), 400

        # 삭제 키워드 체크
        delete_keywords = ["삭제", "삭제해줘", "비워", "비워줘", "초기화", "초기화줘", "없애", "없애줘", "지워", "지워줘"]
        parts = split_to_parts(text)
        has_delete_kw = any(remove_spaces(dk) in [remove_spaces(p) for p in parts] for dk in delete_keywords)
        all_field_keywords = list(chain.from_iterable(field_map.values()))
        has_field_kw = any(remove_spaces(fk) in [remove_spaces(p) for p in parts] for fk in all_field_keywords)

        if not (has_delete_kw and has_field_kw):
            return jsonify({"error": "삭제 명령이 아니거나 필드명이 포함되지 않았습니다."}), 400

        # 매칭된 필드 추출
        matched_fields = []
        for field, keywords in sorted(field_map.items(), key=lambda x: -max(len(k) for k in x[1])):
            for kw in keywords:
                if remove_spaces(kw) in [remove_spaces(p) for p in parts] and field not in matched_fields:
                    matched_fields.append(field)

        return delete_member_field_nl_direct(text, matched_fields)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500






# ======================================================================================
# ✅ 회원 조회
# ======================================================================================









# ======================================================================================
# ======================================================================================
# ======================================================================================
# ======================================================================================


# ======================================================================================
# ✅ 제품 주문 루틴
# ======================================================================================
# ======================================================================================
# ✅ 제품 주문 루틴
# ======================================================================================
# ======================================================================================
# ✅ 자동 분기 라우트 (iPad / PC)
# ======================================================================================

# =======================================================================

@app.route("/upload_order", methods=["POST"])
def upload_order_auto():
    """
    제품 주문 업로드 자동 분기 API
    📌 설명:
    User-Agent를 기반으로 PC/iPad 업로드 방식을 자동으로 분기 처리합니다.
    📥 입력(JSON 예시):
    (form-data, PC/iPad 동일)
    """

    user_agent = request.headers.get("User-Agent", "").lower()

    # PC / iPad 판별
    is_pc = ("windows" in user_agent) or ("macintosh" in user_agent)

    if is_pc:
        return upload_order_pc()  # PC 전용
    else:
        return upload_order_ipad()  # iPad 전용




# ======================================================================================
# ✅ 제품 주문 공통 처리 함수
# ======================================================================================
def process_uploaded_order(member_name, image_bytes, mode="api"):
    """iPad/PC 공통 주문 처리 로직"""
    try:
        # GPT Vision 분석
        order_data = extract_order_from_uploaded_image(image_bytes)

        # orders 배열 보정
        if isinstance(order_data, dict) and "orders" in order_data:
            orders_list = order_data["orders"]
        elif isinstance(order_data, dict):
            orders_list = [order_data]
        else:
            return {"error": "GPT 응답이 올바른 JSON 형식이 아닙니다.", "응답": order_data}, 500

        # 공통 처리: 결재방법, 수령확인 무조건 공란
        for order in orders_list:
            order["결재방법"] = ""
            order["수령확인"] = ""

        if mode == "api":
            save_result = addOrders({"회원명": member_name, "orders": orders_list})
            return {
                "mode": "api",
                "message": f"{member_name}님의 주문이 저장되었습니다. (memberslist API)",
                "추출된_JSON": orders_list,
                "저장_결과": save_result
            }, 200

        elif mode == "sheet":
            db_ws = get_worksheet("DB")
            records = db_ws.get_all_records()
            member_info = next((r for r in records if r.get("회원명") == member_name), None)
            if not member_info:
                return {"error": f"회원 '{member_name}'을(를) 찾을 수 없습니다."}, 404

            order_date = now_kst().strftime("%Y-%m-%d %H:%M:%S")
            orders_ws = get_worksheet("제품주문")
            for order in orders_list:
                orders_ws.append_row([
                    order_date,
                    member_name,
                    member_info.get("회원번호"),
                    member_info.get("휴대폰번호"),
                    order.get("제품명"), order.get("제품가격"), order.get("PV"),
                    order.get("주문자_고객명"), order.get("주문자_휴대폰번호"), order.get("배송처"),
                    "", ""  # 결재방법, 수령확인
                ])
            return {"mode": "sheet", "status": "success", "saved_rows": len(orders_list)}, 200

        else:
            return {"error": "mode 값은 'api' 또는 'sheet'여야 합니다."}, 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}, 500



# ======================================================================================
# ✅ 업로드 라우트 (iPad 명령어 자동 감지) iPad 업로드
# ======================================================================================
@app.route("/upload_order_ipad", methods=["POST"])  
def upload_order_ipad():
    """
    제품 주문 업로드 API (iPad)
    📌 설명:
    iPad에서 캡처한 주문 이미지를 업로드하여 제품 주문 시트에 저장합니다.
    📥 입력(form-data 예시):
    회원명=홍길동
    message=홍길동 제품주문 저장
    image=@order.jpg
    """

    mode = request.form.get("mode") or request.args.get("mode")
    member_name = request.form.get("회원명")
    image_file = request.files.get("image")
    image_url = request.form.get("image_url")
    message_text = request.form.get("message", "").strip()

    # 🔹 iPad 명령어 자동 감지
    if not mode and "제품주문 저장" in message_text:
        mode = "api"
        possible_name = message_text.replace("제품주문 저장", "").strip()
        if possible_name:
            member_name = possible_name

    if not mode:
        mode = "api"

    if not member_name:
        return jsonify({"error": "회원명 필드 또는 message에서 회원명을 추출할 수 없습니다."}), 400

    try:
        # 이미지 가져오기
        if image_file:
            image_bytes = io.BytesIO(image_file.read())
        elif image_url:
            img_response = requests.get(image_url)
            if img_response.status_code != 200:
                return jsonify({"error": "이미지 다운로드 실패"}), 400
            image_bytes = io.BytesIO(img_response.content)
        else:
            return jsonify({"error": "image(파일) 또는 image_url이 필요합니다."}), 400

        # ✅ 공통 처리 함수 호출
        result, status = process_uploaded_order(member_name, image_bytes, mode)
        return jsonify(result), status

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    



# ======================================================================================
# ✅ PC 전용 업로드 (회원명 + "제품주문 저장" + 이미지) PC 업로드
# ======================================================================================
@app.route("/upload_order_pc", methods=["POST"])
def upload_order_pc():
    """
    제품 주문 업로드 API (PC)
    📌 설명:
    PC에서 업로드된 주문 이미지를 분석하여 제품 주문 시트에 저장합니다.
    📥 입력(form-data 예시):
    회원명=홍길동
    message=홍길동 제품주문 저장
    image=@order.jpg
    """

    mode = request.form.get("mode") or request.args.get("mode")
    member_name = request.form.get("회원명")
    image_file = request.files.get("image")
    image_url = request.form.get("image_url")
    message_text = request.form.get("message", "").strip()

    # 🔹 PC 명령어 자동 감지
    if not mode and "제품주문 저장" in message_text:
        mode = "api"
        possible_name = message_text.replace("제품주문 저장", "").strip()
        if possible_name:
            member_name = possible_name

    if not mode:
        mode = "api"

    if not member_name:
        return jsonify({"error": "회원명 필드 또는 message에서 회원명을 추출할 수 없습니다."}), 400

    try:
        # 이미지 가져오기
        if image_file:
            image_bytes = io.BytesIO(image_file.read())
        elif image_url:
            img_response = requests.get(image_url)
            if img_response.status_code != 200:
                return jsonify({"error": "이미지 다운로드 실패"}), 400
            image_bytes = io.BytesIO(img_response.content)
        else:
            return jsonify({"error": "image(파일) 또는 image_url이 필요합니다."}), 400

        # ✅ 공통 처리 함수 호출
        result, status = process_uploaded_order(member_name, image_bytes, mode)
        return jsonify(result), status

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ======================================================================================
# ✅ 자동 분기
# ======================================================================================






# ======================================================================================
# ======================================================================================
# ======================================================================================
# ======================================================================================






# ======================================================================================
# ✅ 자연어 주문 저장 (PC 텍스트) 텍스트 기반으로 자연어에서 주문을 추출하는 API.
# ======================================================================================
@app.route("/upload_order_text", methods=["POST"])
def upload_order_text():
    """
    자연어 기반 주문 저장 API
    📌 설명:
    자연어 문장에서 회원명, 제품명, 수량, 결제방법, 배송지를 추출하여 주문을 저장합니다.
    📥 입력(JSON 예시):
    {
    "message": "김지연 노니 2개 카드 주문 저장"
    }
    """

    text = request.form.get("message") or (request.json.get("message") if request.is_json else None)
    if not text:
        return jsonify({"error": "message 필드가 필요합니다."}), 400

    # 회원명 추출 (제품주문 저장 앞부분)
    member_name_match = re.match(r"^(\S+)\s*제품주문\s*저장", text)
    if not member_name_match:
        return jsonify({"error": "회원명을 찾을 수 없습니다."}), 400
    member_name = member_name_match.group(1)

    # GPT로 파싱
    order_data = parse_order_from_text(text)
    if not order_data.get("orders"):
        return jsonify({"error": "주문 정보를 추출하지 못했습니다.", "응답": order_data}), 400

    try:
        # memberslist API 저장
        save_result = addOrders({
            "회원명": member_name,
            "orders": order_data["orders"]
        })
        return jsonify({
            "status": "success",
            "회원명": member_name,
            "추출된_JSON": order_data["orders"],
            "저장_결과": save_result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500





# iPad 업로드 후 GPT Vision으로 뽑은 JSON을 시트에 직접 넣는 엔드포인트
# 현재 upload_order_ipad → addOrders() 호출과 연결돼 있어서 반드시 필요
# ======================================================================================
# ✅ 아이패드에서 이미지 입력으로 제품주문처리 이미지 json으로 처리
# ======================================================================================
@app.route("/add_orders", methods=["POST"])
def add_orders():
    """
    주문 JSON 직접 추가 API
    📌 설명:
    분석된 주문 JSON을 그대로 제품주문 시트에 추가합니다.
    📥 입력(JSON 예시):
    {
    "회원명": "홍길동",
    "orders": [
        { "제품명": "홍삼", "제품가격": "50000", "PV": "10", "배송처": "서울" }
    ]
    }
    """

    data = request.json
    회원명 = data.get("회원명")
    orders = data.get("orders", [])

    try:
        sheet = get_worksheet("제품주문")
        db_sheet = get_worksheet("DB")
        member_records = db_sheet.get_all_records()

        회원번호 = ""
        회원_휴대폰번호 = ""
        for record in member_records:
            if record.get("회원명") == 회원명:
                회원번호 = record.get("회원번호", "")
                회원_휴대폰번호 = record.get("휴대폰번호", "")
                break

        if orders:
            row_index = 2
            for order in orders:
                row = [
                    order.get("주문일자", datetime.now().strftime("%Y-%m-%d")),
                    회원명,
                    회원번호,
                    회원_휴대폰번호,
                    order.get("제품명", ""),
                    order.get("제품가격", ""),
                    order.get("PV", ""),
                    order.get("결재방법", ""),
                    order.get("주문자_고객명", ""),
                    order.get("주문자_휴대폰번호", ""),
                    order.get("배송처", ""),
                    order.get("수령확인", "")
                ]
                sheet.insert_row(row, row_index)
                row_index += 1

        return jsonify({"status": "success", "message": "주문이 저장되었습니다."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    





# 외부에서 구조화된 JSON 데이터를 바로 넣고 싶을 때 유용, 삭제하지 않는 게 좋음
# ======================================================================================
# ✅ JSON 직접 저장 JSON 리스트를 직접 시트에 저장하는 전용 API
# ======================================================================================
@app.route('/save_order_from_json', methods=['POST'])
def save_order_from_json():
    """
    주문 JSON 저장 API
    📌 설명:
    외부에서 전달된 JSON 리스트를 그대로 제품주문 시트에 저장합니다.
    📥 입력(JSON 예시):
    [
    { "제품명": "홍삼", "제품가격": "50000", "PV": "10", "배송처": "서울" }
    ]
    """

    try:
        data = request.get_json()
        sheet = get_worksheet("제품주문")

        if not isinstance(data, list):
            return jsonify({"error": "JSON은 리스트 형식이어야 합니다."}), 400

        for item in data:
            row = [
                "",  # 주문일자 무시
                "",  # 회원명 무시
                "",  # 회원번호 무시
                "",  # 휴대폰번호 무시
                item.get("제품명", ""),
                item.get("제품가격", ""),
                item.get("PV", ""),
                "",  # 결재방법 무시
                item.get("주문자_고객명", ""),
                item.get("주문자_휴대폰번호", ""),
                item.get("배송처", ""),
                "",  # 수령확인 무시
            ]
            append_row(sheet, row)

        return jsonify({"status": "success", "count": len(data)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500





# 스키마 혼용 중이라고 하셨으니 그대로 두셔야 합니다
# 기존 스키마/외부 API(MEMBERSLIST_API_URL)와 호환성을 위해 남겨둔 프록시
# ======================================================================================
# ✅ API 프록시 저장
# ======================================================================================
@app.route('/saveOrder', methods=['POST'])
@app.route('/save_Order', methods=['POST'])
def saveOrder():
    """
    주문 저장 API (Proxy)
    📌 설명:
    외부 API(MEMBERSLIST_API_URL)로 주문 데이터를 프록시 전송합니다.
    📥 입력(JSON 예시):
    {
    "회원명": "홍길동",
    "orders": [
        { "제품명": "홍삼", "제품가격": "50000", "PV": "10" }
    ]
    }
    """

    try:
        payload = request.get_json(force=True)
        resp = requests.post(MEMBERSLIST_API_URL, json=payload)
        resp.raise_for_status()
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500






# GPT 기반 확장 파서 테스트 및 자동화에 필수라 유지해야 합니다
# 자연어 명령어(김지연 노니 2개 카드 주문 저장) → 파싱 → 저장까지 처리
# ======================================================================================
# ✅ 자연어 파서 기반 저장 API 엔드포인트
# ======================================================================================
# 클라이언트로부터 주문 관련 자연어 문장을 받아서 분석(파싱)한 후, Google Sheets 같은 시트에 저장하는 역할
# POST 요청의 JSON body에서 "text" 필드 값을 받아와 user_input 변수에 저장
# 예: "김지연 노니 2개 카드 주문 저장" 같은 자연어 문장

@app.route("/parse_and_save_order", methods=["POST"])
def parse_and_save_order():
    """
    자연어 주문 파싱 후 저장 API
    📌 설명:
    자연어 문장을 파싱하여 주문 정보를 추출하고, 제품주문 시트에 저장합니다.
    📥 입력(JSON 예시):
    {
    "text": "김지연 노니 2개 카드 주문 저장"
    }
    """

    try:
        user_input = request.json.get("text", "")
        parsed = parse_order_text_rule(user_input)
        save_order_to_sheet(parsed)
        return jsonify({
            "status": "success",
            "message": f"{parsed['회원명']}님의 주문이 저장되었습니다.",
            "parsed": parsed
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500








# ======================================================================================
# ✅ 주문 조회
# ======================================================================================
@app.route("/find_order", methods=["POST"])
def find_order_route():
    """
    주문 조회 API
    📌 설명:
    회원명과 제품명을 기준으로 주문 내역을 조회합니다.
    📥 입력(JSON 예시):
    {
    "회원명": "김상민",
    "제품명": "헤모힘"
    }
    """
    try:
        data = request.get_json()
        member = data.get("회원명", "").strip()
        product = data.get("제품명", "").strip()

        if not member and not product:
            return jsonify({"error": "회원명 또는 제품명을 입력해야 합니다."}), 400

        matched = find_order(member, product)
        if not matched:
            return jsonify({"error": "해당 주문을 찾을 수 없습니다."}), 404

        if len(matched) == 1:
            return jsonify(clean_order_data(matched[0])), 200

        return jsonify([clean_order_data(o) for o in matched]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500









# ======================================================================================
# ✅ 주문 등록
# ======================================================================================
@app.route("/register_order", methods=["POST"])
def register_order_route():
    """
    주문 등록 API
    📌 설명:
    회원명, 제품명, 가격, PV, 배송지 등 명시적 JSON 입력을 받아 주문을 등록합니다.
    📥 입력(JSON 예시):
    {
    "회원명": "홍길동",
    "제품명": "홍삼",
    "제품가격": "50000",
    "PV": "10",
    "배송처": "서울"
    }
    """

    try:
        data = request.get_json()
        member = data.get("회원명", "").strip()
        product = data.get("제품명", "").strip()
        price = data.get("제품가격", "").strip()
        pv = data.get("PV", "").strip()
        method = data.get("결재방법", "").strip()
        delivery = data.get("배송처", "").strip()
        date = data.get("주문일자", "").strip()

        if not member or not product:
            return jsonify({"error": "회원명과 제품명은 필수 입력 항목입니다."}), 400

        register_order(member, product, price, pv, method, delivery, date)
        return jsonify({"message": f"{member}님의 '{product}' 주문이 등록되었습니다."}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500






# ======================================================================================
# ✅ 주문 수정
# ======================================================================================
@app.route("/update_order", methods=["POST"])
def update_order_route():
    """
    주문 수정 API
    📌 설명:
    회원명과 제품명을 기준으로 주문 항목을 찾아 수정합니다.
    📥 입력(JSON 예시):
    {
    "회원명": "홍길동",
    "제품명": "홍삼",
    "수정목록": { "제품가격": "60000" }
    }
    """

    try:
        data = request.get_json()
        member = data.get("회원명", "").strip()
        product = data.get("제품명", "").strip()
        updates = data.get("수정목록", {})

        if not member or not product:
            return jsonify({"error": "회원명과 제품명은 필수 입력 항목입니다."}), 400
        if not isinstance(updates, dict) or not updates:
            return jsonify({"error": "수정할 필드를 지정해야 합니다."}), 400

        update_order(member, product, updates)
        return jsonify({"message": f"{member}님의 '{product}' 주문이 수정되었습니다."}), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500




# ======================================================================================
# ✅ 주문 삭제
# ======================================================================================
@app.route("/delete_order", methods=["POST"])
def delete_order_route():
    """
    주문 삭제 API
    📌 설명:
    회원명과 제품명을 기준으로 주문을 삭제합니다.
    📥 입력(JSON 예시):
    {
    "회원명": "홍길동",
    "제품명": "홍삼"
    }
    """

    try:
        data = request.get_json()
        member = data.get("회원명", "").strip()
        product = data.get("제품명", "").strip()

        if not member or not product:
            return jsonify({"error": "회원명과 제품명은 필수 입력 항목입니다."}), 400

        delete_order(member, product)
        return jsonify({"message": f"{member}님의 '{product}' 주문이 삭제되었습니다."}), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500






# ======================================================================================
# ✅ 주문 삭제 확인 API
# ======================================================================================
@app.route("/delete_order_confirm", methods=["POST"])
def delete_order_confirm():
    """
    주문 삭제 확정 API
    📌 설명:
    삭제 요청 단계에서 선택한 주문 번호를 확정하여 실제 행 삭제를 수행합니다.
    📥 입력(JSON 예시):
    {
    "삭제번호": "1,2"
    }
    """

    try:
        data = request.get_json()
        번호들 = data.get("삭제번호", "").strip()

        if 번호들 in ["없음", "취소", ""]:
            return jsonify({"message": "삭제 요청이 취소되었습니다."}), 200

        # 숫자만 추출 → 중복 제거 및 정렬
        번호_리스트 = sorted(set(map(int, re.findall(r'\d+', 번호들))))

        sheet = get_product_order_sheet()
        all_values = sheet.get_all_values()

        if not all_values or len(all_values) < 2:
            return jsonify({"error": "삭제할 주문 데이터가 없습니다."}), 400

        headers, rows = all_values[0], all_values[1:]
        row_count = min(10, len(rows))  # 🔹 최근 10건 기준으로 삭제 가능
        recent_rows = [(i + 2) for i in range(row_count)]  # 실제 행 번호

        # 입력 유효성 검사
        if not 번호_리스트 or any(n < 1 or n > row_count for n in 번호_리스트):
            return jsonify({"error": f"삭제할 주문 번호는 1 ~ {row_count} 사이로 입력해 주세요."}), 400

        # 실제 삭제할 행 번호 목록
        삭제행목록 = [recent_rows[n - 1] for n in 번호_리스트]
        삭제행목록.sort(reverse=True)

        # 행 삭제 수행
        for row_num in 삭제행목록:
            sheet.delete_rows(row_num)

        return jsonify({
            "message": f"✅ {', '.join(map(str, 번호_리스트))}번 주문(행번호: {', '.join(map(str, 삭제행목록))})이 삭제되었습니다.",
            "삭제된_번호": 번호_리스트,
            "삭제된_행번호": 삭제행목록
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500








# ======================================================================================
# ✅ 최근 주문 확인 후 삭제 요청 유도
# ======================================================================================
@app.route("/delete_order_request", methods=["POST"])
def delete_order_request():
    """
    주문 삭제 요청/확정 API
    📌 설명:
    - `/delete_order_request`: 최근 주문 목록을 보여주고 삭제할 번호를 요청
    - `/delete_order_confirm`: 사용자가 선택한 번호의 주문을 실제 삭제
    📥 입력(JSON 예시 - 요청):
    {}
    📥 입력(JSON 예시 - 확정):
    { "삭제번호": "1,2" }
    """

    try:
        sheet = get_product_order_sheet()
        all_values = sheet.get_all_values()

        if not all_values or len(all_values) < 2:
            return jsonify({"message": "등록된 주문이 없습니다."}), 404

        headers, rows = all_values[0], all_values[1:]
        row_count = min(10, len(rows))  # 🔹 최대 10건으로 변경

        # 최신 주문 상단 10건
        recent_orders = [(i + 2, row) for i, row in enumerate(rows[:row_count])]

        response = []
        for idx, (row_num, row_data) in enumerate(recent_orders, start=1):
            try:
                내용 = {
                    "번호(행번호)": f"{idx} (행:{row_num})",
                    "회원명": row_data[headers.index("회원명")],
                    "제품명": row_data[headers.index("제품명")],
                    "가격": row_data[headers.index("제품가격")],
                    "PV": row_data[headers.index("PV")],
                    "주문일자": row_data[headers.index("주문일자")]
                }
                response.append(내용)
            except Exception:
                continue

        return jsonify({
            "message": f"📌 최근 주문 내역 {len(response)}건입니다. "
                       f"삭제할 번호(1~{len(response)})를 선택해 주세요. (행번호 병기됨)",
            "주문목록": response
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


    


















# ======================================================================================
# ✅ 메모(note: 상담일지/개인일지/활동일지) 저장
# ======================================================================================
# ======================================================================================
# ✅ 메모(note: 상담일지/개인일지/활동일지) 저장
# ======================================================================================
# ======================================================================================
# ✅ 메모(note: 상담일지/개인일지/활동일지) 저장
# ======================================================================================
# ======================================================================================
# ✅ 저장 (상담/개인/활동일지)
# ======================================================================================
@app.route("/add_counseling", methods=["POST"])
def add_counseling_route():
    """
    상담/개인/활동 일지 저장 API
    📌 설명:
    자연어 요청문을 파싱하여 상담일지/개인일지/활동일지 시트에 저장합니다.
    📥 입력(JSON 예시):
    {
    "요청문": "김기범 상담일지 저장 헤모힘 24박스를 택배 발송함."
    }
    """

    try:
        data = request.get_json()
        text = data.get("요청문", "").strip()

        match = re.search(r"([가-힣]{2,10})\s*(상담일지|개인일지|활동일지)", text)
        if not match:
            return jsonify({"error": "회원명을 인식할 수 없습니다."}), 400
        member_name = match.group(1).strip()
        sheet_type = match.group(2)

        content = clean_content(text, member_name)
        if not content:
            return jsonify({"error": "저장할 내용이 비어 있습니다."}), 400

        if save_to_sheet(sheet_type, member_name, content):
            return jsonify({"message": f"{member_name}님의 {sheet_type} 저장 완료"}), 201
        return jsonify({"message": "시트 저장에 실패했습니다."}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500




# ======================================================================================
# ✅ API 고급 검색 (content 문자열 기반, 조건식 가능)
# ======================================================================================
@app.route("/search_memo", methods=["POST"])
def search_memo():
    """
    메모 검색 API
    📌 설명:
    키워드 및 검색 조건을 기반으로 상담/개인/활동 일지에서 검색합니다.
    📥 입력(JSON 예시):
    {
    "keywords": ["중국", "공항"],
    "mode": "전체",
    "search_mode": "동시검색",
    "limit": 10
    }
    """

    data = request.get_json(silent=True) or {}

    keywords = data.get("keywords", [])
    mode = data.get("mode", "전체")
    search_mode = data.get("search_mode", "any")
    limit = int(data.get("limit", 20))

    start_dt = parse_date_yyyymmdd(data.get("start_date")) if data.get("start_date") else None
    end_dt = parse_date_yyyymmdd(data.get("end_date")) if data.get("end_date") else None

    if not isinstance(keywords, list) or not keywords:
        return jsonify({"error": "keywords는 비어있지 않은 리스트여야 합니다."}), 400

    results, more_map = {}, {}

    try:
        if mode == "전체":
            for m, sheet_name in SHEET_MAP.items():
                r, more = search_in_sheet(sheet_name, keywords, search_mode, start_dt, end_dt, limit)
                results[m] = r
                if more: more_map[m] = True
        else:
            sheet_name = SHEET_MAP.get(mode)
            if not sheet_name:
                return jsonify({"error": f"잘못된 mode 값입니다: {mode}"}), 400
            r, more = search_in_sheet(sheet_name, keywords, search_mode, start_dt, end_dt, limit)
            results[mode] = r
            if more: more_map[mode] = True

        resp = {
            "status": "success",
            "search_params": {
                "keywords": keywords,
                "mode": mode,
                "search_mode": search_mode,
                "start_date": data.get("start_date"),
                "end_date": data.get("end_date"),
                "limit": limit
            },
            "results": results
        }
        if more_map:
            resp["more_results"] = {k: "더 많은 결과가 있습니다." for k in more_map}
        return jsonify(resp), 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500







# ======================================================================================
# ✅ 자연어 검색 (사람 입력 “검색” 문장)
# ======================================================================================
@app.route("/search_memo_from_text", methods=["POST"])
def search_memo_from_text():
    """
    자연어 메모 검색 API
    📌 설명:
    자연어 문장에서 키워드를 추출하여 상담/개인/활동 일지를 검색합니다.
    📥 입력(JSON 예시):
    {
    "text": "이태수 개인일지 검색 자동차"
    }
    """

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    limit = int(data.get("limit", 20))

    if not text:
        return jsonify({"error": "text가 비어 있습니다."}), 400
    if "검색" not in text:
        return jsonify({"error": "'검색' 키워드가 반드시 포함되어야 합니다."}), 400

    if "개인" in text: sheet_mode = "개인"
    elif "상담" in text: sheet_mode = "상담"
    elif "활동" in text: sheet_mode = "활동"
    else: sheet_mode = "전체"

    search_mode = "AND" if ("동시" in text or "동시검색" in text) else "OR"

    ignore = {"검색","해줘","해주세요","내용","다음","에서","메모","동시","동시검색"}
    tokens = [t for t in text.split() if t not in ignore]

    member_name = None
    for t in tokens:
        if re.match(r"^[가-힣]{2,10}$", t):
            member_name = t
            break

    content_tokens = [t for t in tokens if t != member_name and not any(x in t for x in ["개인","상담","활동","전체"])]
    raw_content = " ".join(content_tokens).strip()
    search_content = clean_content(raw_content, member_name)

    if not search_content:
        return jsonify({"error": "검색할 내용이 없습니다."}), 400

    results = search_memo_core(sheet_mode, search_content, search_mode, member_name, limit)

    return jsonify({
        "status": "success",
        "mode": sheet_mode,
        "member_name": member_name,
        "search_mode": search_mode,
        "content": search_content,
        "results": results
    }), 200






# 조회 (회원명 + 일지종류 전부 불러오기)
# ======================================================================================
# ✅ 일지 조회 (회원 + 일지종류)
# ======================================================================================
@app.route("/find_memo", methods=["POST"])
def find_memo_route():
    """
    일지 조회 API
    📌 설명:
    회원명과 일지 종류(개인/상담/활동)를 기준으로 일지 내용을 조회합니다.
    📥 입력(JSON 예시):
    {
    "일지종류": "개인일지",
    "회원명": "홍길동"
    }
    """

    try:
        data = request.get_json()
        sheet_name = data.get("일지종류", "").strip()
        member = data.get("회원명", "").strip()

        if not sheet_name or not member:
            return jsonify({"error": "일지종류와 회원명은 필수 입력 항목입니다."}), 400

        matched = find_memo(sheet_name, member)
        if not matched:
            return jsonify({"error": "해당 일지를 찾을 수 없습니다."}), 404

        return jsonify(matched), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500






# ======================================================================================
# 메모 저장
# ======================================================================================
@app.route("/save_memo", methods=["POST"])
def save_memo_route():
    """
    일지 저장 API
    📌 설명:
    회원명과 일지 종류, 내용을 입력받아 해당 시트에 저장합니다.
    📥 입력(JSON 예시):
    {
    "일지종류": "상담일지",
    "회원명": "홍길동",
    "내용": "오늘은 제품설명회를 진행했습니다."
    }
    """

    try:
        data = request.get_json()
        sheet_name = data.get("일지종류", "").strip()
        member = data.get("회원명", "").strip()
        content = data.get("내용", "").strip()

        if not sheet_name or not member or not content:
            return jsonify({"error": "일지종류, 회원명, 내용은 필수 입력 항목입니다."}), 400

        save_memo(sheet_name, member, content)
        return jsonify({"message": f"{member}님의 {sheet_name} 저장 완료"}), 201

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    



# ======================================================================================
# ✅ 메모(note: 상담일지/개인일지/활동일지) 저장
# ======================================================================================
# ======================================================================================
# ✅ 메모(note: 상담일지/개인일지/활동일지) 저장
# ======================================================================================
# ======================================================================================
# ✅ 메모(note: 상담일지/개인일지/활동일지) 저장
# ======================================================================================











# ======================================================================================
# ✅ 후원수당 등록
# ======================================================================================
# ======================================================================================
# ✅ 후원수당 등록
# ======================================================================================
# ======================================================================================
# ✅ 후원수당 등록
# ======================================================================================

# ======================================================================================
# 후원 수당
# ======================================================================================
# ✅ 후원수당 조회 후원수당 시트에서 검색
# ==============================
# 후원수당 API
# ==============================

# ======================================================================================

# ==============================
# 후원수당 API
# ==============================

@app.route("/register_commission", methods=["POST"])
def register_commission_route():
    """
    후원수당 등록 API
    📌 설명:
    회원명을 기준으로 후원수당 데이터를 시트에 등록합니다.
    """
    try:
        data = request.get_json()
        member = data.get("회원명", "").strip()
        amount = data.get("후원수당", "").strip()

        if not member or not amount:
            return jsonify({"status": "error", "error": "회원명과 후원수당은 필수 입력 항목입니다."}), 400

        ok = register_commission(data)
        if ok:
            return jsonify({
                "status": "success",
                "message": f"{member}님의 후원수당 {amount}원이 등록되었습니다."
            }), 200
        else:
            return jsonify({"status": "error", "error": "등록 실패"}), 500

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500



@app.route("/find_commission", methods=["POST"])
def find_commission_route():
    """
    후원수당 등록 API
    📌 설명:
    회원명을 기준으로 후원수당 데이터를 시트에 등록합니다.
    """    
    try:
        data = request.get_json()
        member = data.get("회원명", "").strip()
        if not member:
            return jsonify({"status": "error", "error": "회원명이 필요합니다."}), 400

        results = find_commission({"회원명": member})
        return jsonify({"status": "success", "results": results}), 200

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500




@app.route("/update_commission", methods=["POST"])
def update_commission_route():
    """후원수당 수정 API"""
    try:
        data = request.get_json()
        member = data.get("회원명", "").strip()
        date = data.get("지급일자", "").strip()
        updates = data.get("updates", {})

        if not member or not date:
            return jsonify({"status": "error", "error": "회원명과 지급일자는 필수 항목입니다."}), 400

        update_commission(member, date, updates)
        return jsonify({
            "status": "success",
            "message": f"{member}님의 {date} 후원수당 데이터가 수정되었습니다."
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500



@app.route("/delete_commission", methods=["POST"])
def delete_commission_route():
    """후원수당 삭제 API"""
    try:
        data = request.get_json()
        member = data.get("회원명", "").strip()
        date = data.get("지급일자", "").strip()

        if not member:
            return jsonify({"status": "error", "error": "회원명이 필요합니다."}), 400

        result = delete_commission(member, 기준일자=date if date else None)
        return jsonify({
            "status": "success",
            "message": result.get("message", "")
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500



# ============================================================










if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)


