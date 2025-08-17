# app.py
# =============================================================================
# Flask 앱 (I/O 전용)
# - Google Sheets, 외부 API(임팩트/멤버리스트), OpenAI 호출
# - 모든 파싱 로직은 parser.py 에서 import
# =============================================================================
from flask import Flask, request, jsonify, Response
import os, io, re, json, base64, time, traceback, requests
from gspread.exceptions import APIError, WorksheetNotFound
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import Tuple, Optional



# ✅ parser.py 에서 필요한 함수만 임포트
# ✅ 네임스페이스 없이 바로 호출 가능

from parser import (
    now_kst,
    process_order_date,
    parse_registration,
    parse_request_and_update,
    parse_order_text_rule,
    guess_intent,
    parse_natural_query,
    parse_deletion_request,
)


# -------------------- 환경 --------------------
if os.getenv("RENDER") is None:
    from dotenv import load_dotenv
    if not os.path.exists(".env"):
        raise FileNotFoundError(".env 파일이 없습니다.")
    load_dotenv(".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = os.getenv("OPENAI_API_URL")             # e.g. https://api.openai.com/v1/chat/completions
MEMBERSLIST_API_URL = os.getenv("MEMBERSLIST_API_URL")   # 기존 외부 저장 API
IMPACT_API_URL = os.getenv("IMPACT_API_URL")             # ✅ 요청하신 '임팩트' 연동용 (선택)
GOOGLE_SHEET_TITLE = os.getenv("GOOGLE_SHEET_TITLE")
CREDS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")

if not GOOGLE_SHEET_TITLE:
    raise EnvironmentError("환경변수 GOOGLE_SHEET_TITLE이 설정되지 않았습니다.")
if not os.path.exists(CREDS_PATH):
    raise FileNotFoundError(f"Google credentials 파일을 찾을 수 없습니다: {CREDS_PATH}")

# -------------------- 시트 --------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_PATH, scope)
client = gspread.authorize(creds)
spreadsheet = client.open(GOOGLE_SHEET_TITLE)

def get_ws(name: str):
    return spreadsheet.worksheet(name)

def safe_update_cell(sheet, row: int, col: int, value, clear_first=True, max_retries=3, delay=2):
    for attempt in range(1, max_retries + 1):
        try:
            if clear_first:
                sheet.update_cell(row, col, "")
            sheet.update_cell(row, col, value)
            return True
        except APIError as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status == 429:
                time.sleep(delay); delay *= 2
            else:
                raise
    return False


def header_maps(sheet):
    headers = [h.strip() for h in sheet.row_values(1)]
    idx = {h: i + 1 for i, h in enumerate(headers)}
    idx_l = {h.lower(): i + 1 for i, h in enumerate(headers)}
    return headers, idx, idx_l

# -------------------- 외부 API (임팩트/멤버리스트/OpenAI) --------------------
def call_memberslist_add_orders(payload: dict):
    """기존 memberslist API"""
    if not MEMBERSLIST_API_URL:
        raise RuntimeError("MEMBERSLIST_API_URL 미설정")
    r = requests.post(MEMBERSLIST_API_URL, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()



def call_impact_sync(payload: dict):
    """
    ✅ '임팩트' 연동: IMPACT_API_URL이 설정돼 있으면 동일 payload를 전달.
    - 실패해도 전체 트랜잭션은 막지 않음(로깅 수준)
    - payload 예: {"type":"order","member":"홍길동","orders":[...], "source":"sheet_gpt"}
    """
    if not IMPACT_API_URL:
        return {"skipped": True, "reason": "IMPACT_API_URL not set"}
    try:
        r = requests.post(IMPACT_API_URL, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}



def openai_vision_extract_orders(image_bytes: io.BytesIO):
    """이미지 → 주문 JSON 추출 (gpt-4o)"""
    image_b64 = base64.b64encode(image_bytes.getvalue()).decode("utf-8")
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    prompt = (
        "이미지를 분석하여 JSON 형식으로 추출하세요. "
        "여러 개의 제품이 있을 경우 'orders' 배열에 모두 담으세요. "
        "질문하지 말고 추출된 orders 전체를 그대로 저장할 준비를 하세요. "
        "(이름, 휴대폰번호, 주소)는 소비자 정보임. "
        "회원명, 결재방법, 수령확인, 주문일자 무시. "
        "필드: 제품명, 제품가격, PV, 주문자_고객명, 주문자_휴대폰번호, 배송처"
    )
    payload = {
        "model": "gpt-4o",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
            ]
        }],
        "temperature": 0
    }
    r = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    clean = re.sub(r"```(?:json)?", "", content, flags=re.MULTILINE).strip()
    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        data = {"raw_text": content}
    # orders 리스트 보장
    if isinstance(data, dict) and "orders" in data:
        orders_list = data["orders"]
    elif isinstance(data, dict):
        orders_list = [data]
    elif isinstance(data, list):
        orders_list = data
    else:
        orders_list = []
    # 정책: 결재방법/수령확인은 공란 유지 + 문자열 필드 trim
    for o in orders_list:
        o.setdefault("결재방법", "")
        o.setdefault("수령확인", "")
        for k, v in o.items():
            if isinstance(v, str):
                o[k] = v.strip()

    return orders_list

# -------------------- Flask --------------------
app = Flask(__name__)

@app.route("/")
def root():
    return "Flask 서버 실행 중 (app/parser 분리)"

@app.route("/healthz")
def healthz():
    return "ok"



@app.route("/parse-intent", methods=["POST"])
def parse_intent():
    try:
        data = request.get_json(force=True) or {}
        text = (data.get("text") or data.get("요청문") or "").strip()
        if not text:
            return jsonify({"ok": False, "error": "text(또는 요청문)이 비어 있습니다."}), 400

        intent = guess_intent(text)

        # intent → handler 매핑
        def _update_member_handler(t: str):
            member = {}
            _, changed = parse_request_and_update(t, member)
            return {"updated": changed}

        dispatch = {
            "register_member": lambda t: parse_registration(t),
            "update_member":  _update_member_handler,
            "save_order":     lambda t: parse_order_text_rule(t),
            "find_member":    lambda t: parse_natural_query(t),
            "delete_member":  lambda t: parse_deletion_request(t),
        }

        handler = dispatch.get(intent)
        if not handler:
            return jsonify({"ok": False, "intent": "unknown", "error": f"알 수 없는 intent: {intent}"}), 400

        parsed = handler(text)
        return jsonify({"ok": True, "intent": intent, "data": parsed}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500






# --- 회원 찾기 ---------------------------------------------------------------
@app.route("/find_member", methods=["POST"])
def find_member():
    try:
        data = request.get_json(force=True)
        name = (data.get("회원명") or "").strip()
        number = (data.get("회원번호") or "").strip()
        if not name and not number:
            return jsonify({"error": "회원명 또는 회원번호를 입력해야 합니다."}), 400

        ws = get_ws("DB")
        records = ws.get_all_records()
        if not records:
            return jsonify({"error": "DB 시트에 레코드가 없습니다."}), 404

        matched = []
        for r in records:
            if name and (r.get("회원명") or "").strip() == name:
                matched.append(r)
            elif number and (r.get("회원번호") or "").strip() == number:
                matched.append(r)
        if not matched:
            return jsonify({"error": "해당 회원 정보를 찾을 수 없습니다."}), 404
        if len(matched) == 1:
            return jsonify(matched[0]), 200
        mini = [{"번호": i+1, "회원명": m.get("회원명"), "회원번호": m.get("회원번호"), "휴대폰번호": m.get("휴대폰번호")} for i, m in enumerate(matched)]
        return jsonify(mini), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- 회원 저장/수정 -----------------------------------------------------------
@app.route("/save_member", methods=["POST"])
def save_member_route():
    try:
        req = request.get_json(force=True)
        요청문 = req.get("요청문") or req.get("회원명", "")
        if not 요청문:
            return jsonify({"error": "입력 문장이 없습니다"}), 400

        name, number, phone = parse_registration(요청문)
        if not name:
            return jsonify({"error": "회원명을 추출할 수 없습니다"}), 400
        address = req.get("주소") or req.get("address", "")

        ws = get_ws("DB")
        headers, idx, idx_l = header_maps(ws)
        records = ws.get_all_records()

        # 기존 갱신
        for i, row in enumerate(records):
            if (row.get("회원명") or "").strip() == name:
                row_idx = i + 2
                for key, val in {"회원명": name, "회원번호": number, "휴대폰번호": phone, "주소": address}.items():
                    if val:
                        col = idx.get(key) or idx_l.get(key.lower())
                        if col: safe_update_cell(ws, row_idx, col, val, clear_first=True)
                return jsonify({"ok": True, "data": f"{name} 기존 회원 정보 수정 완료"}), 200

        # 신규 추가
        row = [''] * len(headers)
        for key, val in {"회원명": name, "회원번호": number, "휴대폰번호": phone, "주소": address}.items():
            if val and key in headers:
                row[headers.index(key)] = val
        ws.insert_row(row, 2)
        return jsonify({"ok": True, "data": f"{name} 회원 신규 등록 완료"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/update_member", methods=["POST"])
@app.route("/updateMember", methods=["POST"])
def update_member_route():
    try:
        data = request.get_json(force=True)
        요청문 = (data.get("요청문") or "").strip()
        if not 요청문:
            return jsonify({"ok": False, "error": "요청문이 비어 있습니다."}), 400

        ws = get_ws("DB")
        headers, idx, idx_l = header_maps(ws)
        records = ws.get_all_records()
        if not records:
            return jsonify({"error": "DB 시트에 레코드가 없습니다."}), 404

        # 회원명 매칭(길이 긴 이름 우선)
        member_names = sorted({(r.get("회원명") or "").strip() for r in records if r.get("회원명")}, key=lambda s: -len(s))
        name = None
        for cand in member_names:
            if not cand: continue
            if re.search(rf"\b{re.escape(cand)}\b", 요청문):
                name = cand; break
        if not name:
            return jsonify({"error": "요청문에서 유효한 회원명을 찾을 수 없습니다."}), 400

        # 대상 행 로드
        i = next((i for i, r in enumerate(records) if (r.get("회원명") or "").strip() == name), None)
        if i is None:
            return jsonify({"error": f"'{name}' 회원을 찾을 수 없습니다."}), 404
        row_idx = i + 2
        member = records[i]

        updated_member, changed = parse_request_and_update(요청문, member)
        results = []
        for k, v in changed.items():
            col = idx.get(k) or idx_l.get(k.lower())
            if not col: continue
            if safe_update_cell(ws, row_idx, col, v, clear_first=True):
                results.append({"필드": k, "값": v})
        return jsonify({"status": "success", "회원명": name, "수정": results}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- 주문: 이미지 업로드 → OpenAI 파싱 → 저장 + 임팩트 연동 -------------------------
def save_orders_to_sheet(member_name: str, orders_list: list[dict]) -> int:
    db_ws = get_ws("DB")
    recs = db_ws.get_all_records()
    info = next((r for r in recs if (r.get("회원명") or "").strip() == member_name), None)
    if not info:
        raise RuntimeError(f"회원 '{member_name}'을(를) 찾을 수 없습니다.")
    ws = get_ws("제품주문")
    values = ws.get_all_values()
    if not values:
        ws.append_row(["주문일자","회원명","회원번호","휴대폰번호","제품명","제품가격","PV","결재방법","주문자_고객명","주문자_휴대폰번호","배송처","수령확인"])
    saved = 0
    for od in orders_list:
        row = [
            od.get("주문일자", now_kst().strftime("%Y-%m-%d")),
            member_name,
            info.get("회원번호", ""),
            info.get("휴대폰번호", ""),
            od.get("제품명", ""),
            od.get("제품가격", ""),
            od.get("PV", ""),
            od.get("결재방법", ""),
            od.get("주문자_고객명", ""),
            od.get("주문자_휴대폰번호", ""),
            od.get("배송처", ""),
            od.get("수령확인", ""),
        ]
        ws.insert_row(row, index=2)
        saved += 1
    return saved

@app.route("/upload_order", methods=["POST"])
def upload_order():
    """
    mode: api(기본, memberslist로 저장) | sheet(시트에 직접 저장)
    임팩트 연동: 두 모드 모두 성공 시 IMPACT_API_URL 로 payload 전달 (있을 경우)
    """
    mode = request.form.get("mode") or request.args.get("mode") or "api"
    member_name = (request.form.get("회원명") or "").strip()
    message_text = (request.form.get("message") or "").strip()
    image_file = request.files.get("image")
    image_url = request.form.get("image_url")



    if (not member_name) and "제품주문 저장" in message_text:
        member_name = re.sub(r"\s*제품주문\s*저장\s*", "", message_text).strip()



    if not member_name:
        return jsonify({"error": "회원명 필드 또는 message에서 회원명을 추출할 수 없습니다."}), 400
    try:
        if image_file:
            image_bytes = io.BytesIO(image_file.read())
        elif image_url:
            img = requests.get(image_url, timeout=30)
            if img.status_code != 200:
                return jsonify({"error": "이미지 다운로드 실패"}), 400
            image_bytes = io.BytesIO(img.content)
        else:
            return jsonify({"error": "image(파일) 또는 image_url이 필요합니다."}), 400

        orders_list = openai_vision_extract_orders(image_bytes)
        if not orders_list:
            return jsonify({"error": "주문 정보를 추출하지 못했습니다."}), 400

        impact_payload = {"type": "order", "member": member_name, "orders": orders_list, "source": "sheet_gpt"}

        if mode == "api":
            saved = call_memberslist_add_orders({"회원명": member_name, "orders": orders_list})
            impact_res = call_impact_sync(impact_payload)
            return jsonify({"mode": "api", "message": f"{member_name}님의 주문 저장 완료 (memberslist)", "openai_orders": orders_list, "memberslist_result": saved, "impact_result": impact_res}), 200

        if mode == "sheet":
            saved_rows = save_orders_to_sheet(member_name, orders_list)
            impact_res = call_impact_sync(impact_payload)
            return jsonify({"mode": "sheet", "status": "success", "saved_rows": saved_rows, "openai_orders": orders_list, "impact_result": impact_res}), 200

        return jsonify({"ok": False, "data": "mode 값은 'api' 또는 'sheet'여야 합니다."}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

# --- 주문: 텍스트 → 규칙 파서 → 한 줄 저장 + 임팩트 연동 ----------------------------
@app.route("/parse_and_save_order", methods=["POST"])
def parse_and_save_order():
    try:
        user_input = request.json.get("text", "")
        parsed = parse_order_text_rule(user_input)
        if not parsed.get("회원명"):
            return jsonify({"status": "error", "message": "회원명을 찾지 못했습니다."}), 400
        # 시트 한 줄 저장
        ws = get_ws("제품주문")
        if not ws.get_all_values():
            ws.append_row(["주문일자","회원명","회원번호","휴대폰번호","제품명","제품가격","PV","결재방법","주문자_고객명","주문자_휴대폰번호","배송처","수령확인"])
        row = [
            process_order_date(parsed.get("주문일자", "")),
            parsed.get("회원명",""),
            parsed.get("회원번호",""),
            parsed.get("휴대폰번호",""),
            parsed.get("제품명",""),
            float(parsed.get("제품가격", 0) or 0),
            float(parsed.get("PV", 0) or 0),
            parsed.get("결재방법",""),
            parsed.get("주문자_고객명",""),
            parsed.get("주문자_휴대폰번호",""),
            parsed.get("배송처",""),
            parsed.get("수령확인",""),
        ]
        ws.insert_row(row, index=2)

        # 임팩트 연동
        impact_res = call_impact_sync({"type":"order_line","member":parsed.get("회원명",""),"row":row,"source":"sheet_gpt"})
        return jsonify({"status":"success","message":f"{parsed.get('회원명','')}님의 주문이 저장되었습니다.","parsed":parsed,"impact_result":impact_res}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

# --- 최근 주문 삭제 ------------------------------------------------------------
@app.route("/delete_order_request", methods=["POST"])
def delete_order_request():
    try:
        ws = get_ws("제품주문")
        values = ws.get_all_values()
        if not values or len(values) < 2:
            return jsonify({"message": "등록된 주문이 없습니다."}), 404
        headers = values[0]; rows = values[1:]
        def col(name): return headers.index(name) if name in headers else None
        N = min(5, len(rows))
        response = []
        for i, row in enumerate(rows[:N], start=1):
            response.append({
                "번호": i,
                "회원명": row[col("회원명")] if col("회원명") is not None else "",
                "제품명": row[col("제품명")] if col("제품명") is not None else "",
                "가격": row[col("제품가격")] if col("제품가격") is not None else "",
                "PV": row[col("PV")] if col("PV") is not None else "",
                "주문일자": row[col("주문일자")] if col("주문일자") is not None else "",
            })
        return jsonify({"message": f"📌 최근 주문 내역 {len(response)}건입니다. 삭제할 번호(1~{len(response)})를 선택해 주세요.","주문목록": response}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/delete_order_confirm", methods=["POST"])
def delete_order_confirm():
    try:
        data = request.get_json(force=True)
        numbers = (data.get("삭제번호") or "").strip()
        if numbers in ["없음", "취소", ""]:
            return jsonify({"message": "삭제 요청이 취소되었습니다."}), 200

        nums = sorted(set(map(int, re.findall(r"\d+", numbers))))
        ws = get_ws("제품주문")
        values = ws.get_all_values()
        if not values or len(values) < 2:
            return jsonify({"error": "삭제할 주문 데이터가 없습니다."}), 400
        N = min(5, len(values) - 1)
        if not nums or any(n < 1 or n > N for n in nums):
            return jsonify({"error": f"삭제할 주문 번호는 1 ~ {N} 사이로 입력해 주세요."}), 400

        real_rows = [i + 2 for i in range(N)]
        to_delete_rows = sorted([real_rows[n - 1] for n in nums], reverse=True)
        for r in to_delete_rows:
            ws.delete_rows(r)
        return jsonify({"message": f"{', '.join(map(str, nums))}번 주문이 삭제되었습니다.","삭제행번호": to_delete_rows}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500








# -------------------- 실행 --------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=True)





