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
import pytz
from datetime import datetime


from utils.http import call_memberslist_add_orders, MemberslistError

# app.py

from utils.openai_utils import openai_vision_extract_orders

# ✅ 외부 API 유틸 (유지)
from utils.http import (
    call_memberslist_add_orders,
    MemberslistError
    
   
)

# -------------------- Flask --------------------
app = Flask(__name__)

# ✅ parser.py 에서 필요한 함수만 임포트
from parser import (
    # 기본 intent 관련
    guess_intent,
    parse_natural_query,
    parse_deletion_request,
    # 날짜/시간 처리
    now_kst,
    process_order_date,
    # 문자열/공통 유틸
    clean_tail_command,
    parse_korean_phone,
    parse_member_number,
    remove_josa,
    match_condition,
    # 회원 등록/수정
    parse_registration,
    infer_field_from_value,
    parse_request_and_update,
    # 주문 처리
    parse_order_text_rule,
    # 메모/검색용
    parse_request_line
    
)
from parser.parser import ensure_orders_list

# -------------------- 환경 로드 (.env는 로컬에서만) --------------------
if os.getenv("RENDER") is None:
    from dotenv import load_dotenv
    if not os.path.exists(".env"):
        raise FileNotFoundError(".env 파일이 없습니다.")
    load_dotenv(".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = os.getenv("OPENAI_API_URL")             # e.g. https://api.openai.com/v1/chat/completions
MEMBERSLIST_API_URL = os.getenv("MEMBERSLIST_API_URL")   # 기존 외부 저장 API
IMPACT_API_URL = os.getenv("IMPACT_API_URL")             # (선택) 임팩트 연동
GOOGLE_SHEET_TITLE = os.getenv("GOOGLE_SHEET_TITLE")

if not GOOGLE_SHEET_TITLE:
    raise EnvironmentError("환경변수 GOOGLE_SHEET_TITLE이 설정되지 않았습니다.")

# -------------------- Google Sheets 자동 인증/연결 --------------------
def get_gspread_client():
    """
    Render: GOOGLE_CREDENTIALS_JSON 사용
    Local : GOOGLE_CREDENTIALS_PATH(기본 'credentials.json') 파일 사용
    """
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")  # Render 환경 변수
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Google credentials 파일을 찾을 수 없습니다: {creds_path}")
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)

    return gspread.authorize(creds)

# ✅ 전역 클라이언트/시트 핸들 (앱 시작 시 1회 연결)
gclient = get_gspread_client()
gsheet = gclient.open(GOOGLE_SHEET_TITLE)
print(f"✅ 시트 '{GOOGLE_SHEET_TITLE}'에 연결되었습니다.", flush=True)

# 워크시트/데이터 유틸 (이 파일 내에서 바로 사용)
def get_ws(sheet_name: str):
    """워크시트 핸들을 반환합니다."""
    try:
        return gsheet.worksheet(sheet_name)
    except WorksheetNotFound:
        raise FileNotFoundError(f"워크시트를 찾을 수 없습니다: {sheet_name}")

def get_all(ws):
    """워크시트의 레코드를 dict 리스트로 반환합니다."""
    return ws.get_all_records()

# -------------------- 루트/헬스 --------------------
@app.route("/")
def root():
    return "Flask 서버 실행 중 (app/parser 분리)"

@app.route("/healthz")
def healthz():
    return "ok"

# =======================================================================
# parse-intent
# =======================================================================
@app.route("/parse-intent", methods=["POST"])
def parse_intent_route():
    try:
        data = request.get_json(force=True) or {}
        text = (data.get("text") or data.get("요청문") or "").strip()
        if not text:
            return jsonify({"ok": False, "error": "text(또는 요청문)이 비어 있습니다."}), 400

        intent = guess_intent(text)

        dispatch = {
            # 회원
            "register_member": parse_registration,
            "update_member":   parse_request_and_update,
            "delete_member":   parse_deletion_request,
            "find_member":     parse_natural_query,
            # 주문
            "save_order":      parse_order_text_rule,
            "find_order":      None,  # 추후 구현
            # 메모
            "save_memo":       parse_request_line,
            "find_memo":       None,  # 추후 구현
            # 후원수당
            "save_commission": None,  # parse_commission 연결 예정
            "find_commission": None,
        }

        handler = dispatch.get(intent)
        if not handler:
            return jsonify({"ok": False, "intent": "unknown", "error": f"알 수 없는 intent: {intent}"}), 400

        # 👉 파서 실행
        parsed = handler(text)
        print(">>> DEBUG parsed:", parsed, flush=True)

        # 👉 find_member 반환형 보정 (tuple -> dict)
        if intent == "find_member" and isinstance(parsed, tuple):
            field, keyword = parsed
            if keyword:
                parsed = {"회원명": keyword} if field in (None, "회원명") else {field: keyword}
            else:
                parsed = {}

        return jsonify({"ok": True, "intent": intent, "data": parsed}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

# -------------------- (선택) KST 유틸 --------------------
def now_kst_local():
    return datetime.now(pytz.timezone("Asia/Seoul"))

# -------------------- 디버그 출력 --------------------
print("✅ GOOGLE_SHEET_TITLE:", os.getenv("GOOGLE_SHEET_TITLE"))
print("✅ GOOGLE_SHEET_KEY 존재 여부:", "Yes" if os.getenv("GOOGLE_SHEET_KEY") else "No", flush=True)







    





# ======================================================================================
# 회원 조회
# ======================================================================================
@app.route("/find_member", methods=["POST"])
def find_member_route():
    try:
        data = request.get_json(force=True)
        name = (data.get("회원명") or "").strip()
        number = (data.get("회원번호") or "").strip()

        if not name and not number:
            return jsonify({"error": "회원명 또는 회원번호를 입력해야 합니다."}), 400

        ws = get_ws("DB")
        rows = get_all(ws)   # ✅ dict 리스트 반환

        if not rows:
            return jsonify({"error": "DB 시트에 데이터가 없습니다."}), 404

        matched = []
        for row in rows:   # row는 dict
            if name and (row.get("회원명") or "").strip() == name:
                matched.append(row)
            elif number and (row.get("회원번호") or "").strip() == number:
                matched.append(row)

        if not matched:
            return jsonify({"error": "해당 회원 정보를 찾을 수 없습니다."}), 404

        # 결과가 1건이면 그대로 반환
        if len(matched) == 1:
            return jsonify(matched[0]), 200

        # 여러 건이면 최소 정보만 반환
        mini = [
            {
                "번호": i + 1,
                "회원명": m.get("회원명", ""),
                "회원번호": m.get("회원번호", ""),
                "휴대폰번호": m.get("휴대폰번호", "")
            }
            for i, m in enumerate(matched)
        ]
        return jsonify(mini), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500















# ======================================================================================
# 회원 등록(이름/번호/폰/주소 일부 파싱) + 없으면 생성 / 있으면 갱신
# ======================================================================================
@app.route("/save_member", methods=["POST"])
def save_member_route():
    try:
        req = request.get_json(force=True)
        요청문 = req.get("요청문") or req.get("회원명", "")
        if not 요청문:
            return jsonify({"error": "입력 문장이 없습니다"}), 400

        # 간단 파서 (실제로는 parse_registration 사용 권장)
        name = req.get("회원명") or 요청문.split()[0]
        number = req.get("회원번호") or ""
        phone = req.get("휴대폰번호") or ""
        address = req.get("주소") or ""

        if not name:
            return jsonify({"error": "회원명을 추출할 수 없습니다"}), 400

        ws = get_ws("DB")
        # ✅ 헤더 공백 제거 버전
        headers = [h.strip() for h in ws.row_values(1)]

        records = ws.get_all_records()

        print("📌 headers:", headers)          # 서버 콘솔 확인용
        print("📌 첫 행 row 예시:", records[0] if records else None)

        # ✅ 기존 회원 갱신
        for i, row in enumerate(records):
            if (row.get("회원명") or "").strip() == name:
                row_idx = i + 2  # 헤더 제외 실제 시트 행 번호
                for key, val in {
                    "회원명": name,
                    "회원번호": number,
                    "휴대폰번호": phone,
                    "주소": address,
                }.items():
                    if val and key in headers:
                        ws.update_cell(row_idx, headers.index(key) + 1, val)
                return jsonify({"ok": True, "data": f"{name} 기존 회원 정보 수정 완료"}), 200

        # ✅ 신규 추가
        row = [""] * len(headers)
        for key, val in {
            "회원명": name,
            "회원번호": number,
            "휴대폰번호": phone,
            "주소": address,
        }.items():
            if val and key in headers:
                row[headers.index(key)] = val
        ws.insert_row(row, 2)

        return jsonify({"ok": True, "data": f"{name} 회원 신규 등록 완료"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500







# ======================================================================================
# 회원 필드 다중 수정 (자연어)
# ======================================================================================
@app.route("/update_member", methods=["POST"])
@app.route("/updateMember", methods=["POST"])
def update_member_route():
    try:
        data = request.get_json(force=True)
        요청문 = clean_tail_command((data.get("요청문") or "").strip())
        if not 요청문:
            return jsonify({"error": "요청문이 비어 있습니다."}), 400

        ws = get_ws("DB")
        headers = [h.strip() for h in ws.row_values(1)]  # 헤더만 추출
        records = ws.get_all_records()  # ✅ dict 리스트 방식

        if not records:
            return jsonify({"error": "DB 시트에 레코드가 없습니다."}), 404

        # 회원명 후보 (길이가 긴 것 우선 매칭)
        member_names = sorted(
            {(r.get("회원명") or "").strip() for r in records if r.get("회원명")},
            key=lambda s: -len(s)
        )

        name = None
        for cand in member_names:
            if cand and cand in 요청문:
                name = cand
                break

        if not name:
            return jsonify({"error": "요청문에서 유효한 회원명을 찾을 수 없습니다."}), 400

        # 대상 행 찾기
        target_idx = next(
            (i for i, r in enumerate(records) if (r.get("회원명") or "").strip() == name),
            None
        )
        if target_idx is None:
            return jsonify({"error": f"'{name}' 회원을 찾을 수 없습니다."}), 404

        row_idx = target_idx + 2  # 헤더 제외 → 실제 시트 행 번호
        member = records[target_idx]

        # 파싱 및 변경 적용
        updated_member, changed = parse_request_and_update(요청문, member)

        results = []
        for k, v in changed.items():
            if k in headers:  # 헤더에 해당 필드가 존재해야 업데이트
                col = headers.index(k) + 1
                ok = safe_update_cell(ws, row_idx, col, v, clear_first=True)
                if ok:
                    results.append({"필드": k, "값": v})

        return jsonify({
            "status": "success",
            "회원명": name,
            "수정": results
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500






# ======================================================================================
# 회원 삭제 (백업 후 삭제)
# ======================================================================================
def ensure_backup_sheet():
    try:
        return get_ws("백업")
    except gspread.WorksheetNotFound:
        # 현재 스프레드시트 핸들 얻어서 새 시트 생성
        spreadsheet = get_ws("DB").spreadsheet
        return spreadsheet.add_worksheet(title="백업", rows=1000, cols=3)


@app.route("/delete_member", methods=["POST"])
def delete_member_route():
    try:
        name = (request.get_json(force=True).get("회원명") or "").strip()
        if not name:
            return jsonify({"error": "회원명을 입력해야 합니다."}), 400

        ws = get_ws("DB")
        headers = [h.strip() for h in ws.row_values(1)]
        records = ws.get_all_records()  # ✅ dict 리스트 방식
        if not records:
            return jsonify({"error": "DB 시트에 레코드가 없습니다."}), 404

        for i, row in enumerate(records):
            if (row.get("회원명") or "").strip() == name:
                # ✅ 백업
                backup_ws = ensure_backup_sheet()
                backup_ws.insert_row(
                    [
                        now_kst().strftime("%Y-%m-%d %H:%M"),
                        name,
                        json.dumps(row, ensure_ascii=False),
                    ],
                    index=2,
                )

                # ✅ 삭제 (헤더 포함이므로 +2)
                ws.delete_rows(i + 2)
                return jsonify({"message": f"'{name}' 회원 삭제 및 백업 완료"}), 200

        return jsonify({"error": f"'{name}' 회원을 찾을 수 없습니다."}), 404

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500








# ======================================================================================
# 메모 통합 저장 / 검색
# ======================================================================================
SHEET_KEYS = {"상담일지", "개인일지", "활동일지", "회원메모", "회원주소"}
ACTION_KEYS = {"저장", "기록", "입력"}

def save_to_sheet(sheet_name: str, member_name: str, content: str) -> bool:
    ws = get_ws(sheet_name)
    ws.insert_row(
        [now_kst().strftime("%Y-%m-%d %H:%M"), member_name.strip(), (content or "").strip()],
        index=2
    )
    return True



def update_member_field_strict(member_name: str, field_name: str, value: str) -> bool:
    ws = get_ws("DB")
    headers = [h.strip() for h in ws.row_values(1)]

    if "회원명" not in headers or field_name not in headers:
        raise RuntimeError("DB 시트 헤더에 필드가 없습니다.")

    records = ws.get_all_records()
    for i, row in enumerate(records):
        if (row.get("회원명") or "").strip() == member_name.strip():
            row_idx = i + 2  # 헤더 보정
            col_idx = headers.index(field_name) + 1
            return bool(safe_update_cell(ws, row_idx, col_idx, value, clear_first=True))
    return False



@app.route("/save_note_unified", methods=["POST"])
def save_note_unified():
    try:
        data = request.get_json(force=True)
        raw = data.get("요청문", "")
        member, sheet_key, action, content = parse_request_line(raw)
        if not member:
            return jsonify({"ok": False, "message": "형식 오류: 첫 단어에 회원명을 입력하세요."}), 400
        if sheet_key not in SHEET_KEYS:
            return jsonify({"ok": False, "message": "형식 오류: 두 번째 단어가 유효한 시트키워드가 아닙니다.", "허용": sorted(SHEET_KEYS)}), 400
        if action not in ACTION_KEYS:
            return jsonify({"ok": False, "message": "형식 오류: 세 번째 단어에 '저장/기록/입력' 중 하나를 입력하세요.", "허용": sorted(ACTION_KEYS)}), 400

        if sheet_key in {"상담일지", "개인일지", "활동일지"}:
            save_to_sheet(sheet_key, member, content)
            return jsonify({"ok": True, "message": f"{member}님의 {sheet_key} 저장 완료."}), 200
        if sheet_key == "회원메모":
            ok = update_member_field_strict(member, "메모", content)
            return (jsonify({"ok": True, "message": f"{member}님의 메모가 DB에 저장되었습니다."}), 200) if ok else (jsonify({"ok": False, "message": f"'{member}' 회원을 찾을 수 없습니다."}), 404)
        if sheet_key == "회원주소":
            ok = update_member_field_strict(member, "주소", content)
            return (jsonify({"ok": True, "message": f"{member}님의 주소가 DB에 저장되었습니다."}), 200) if ok else (jsonify({"ok": False, "message": f"'{member}' 회원을 찾을 수 없습니다."}), 404)
        return jsonify({"ok": False, "message": f"처리할 수 없는 시트키워드: {sheet_key}"}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500
    






# ===================== 검색 관련 =====================
# ===================== 검색 관련 =====================
# ===================== 검색 관련 =====================
@app.route("/search_memo_by_text", methods=["POST"])
def search_memo_by_text():
    try:
        data = request.get_json(force=True)
        keywords = data.get("keywords", [])
        limit = int(data.get("limit", 20))
        sort_order = data.get("sort", "desc")
        match_mode = data.get("match_mode", "any")

        ws = get_ws("개인일지")
        records = ws.get_all_records()
        res = []
        for r in records:
            date_str, member, content = r.get("날짜"), r.get("회원명"), r.get("내용")
            if not (date_str and member and content):
                continue
            combined = f"{member} {content}"
            if not match_condition(combined, keywords, match_mode):
                continue
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            res.append({"날짜": date_str, "회원명": member, "내용": content, "_dt": dt})
        res.sort(key=lambda x: x["_dt"], reverse=(sort_order == "desc"))
        for r in res: 
            r.pop("_dt", None)
        return jsonify({
            "검색조건": {"검색어": keywords, "매칭방식": match_mode, "정렬": sort_order, "결과_최대개수": limit},
            "검색결과": res[:limit]
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/search_counseling_by_text_from_natural", methods=["POST"])
def search_counseling_by_text_from_natural():
    try:
        data = request.get_json(force=True)
        keywords = data.get("keywords", [])
        limit = int(data.get("limit", 20))
        sort_order = data.get("sort", "desc")
        match_mode = data.get("match_mode", "any")

        ws = get_ws("상담일지")
        records = ws.get_all_records()
        res = []
        for r in records:
            date_str, member, content = r.get("날짜"), r.get("회원명"), r.get("내용")
            if not (date_str and member and content):
                continue
            comb = f"{member} {content}".lower()
            cond = (all(k.lower() in comb for k in keywords) if match_mode == "all"
                    else any(k.lower() in comb for k in keywords))
            if not cond:
                continue
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            res.append({"날짜": date_str, "회원명": member, "내용": content, "_dt": dt})
        res.sort(key=lambda x: x["_dt"], reverse=(sort_order == "desc"))
        for r in res: 
            r.pop("_dt", None)
        return jsonify({
            "검색조건": {"키워드": keywords, "매칭방식": match_mode, "정렬": sort_order},
            "검색결과": res[:limit]
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/search_activity_by_text_from_natural", methods=["POST"])
def search_activity_by_text_from_natural():
    try:
        data = request.get_json(force=True)
        keywords = data.get("keywords", [])
        limit = int(data.get("limit", 20))
        sort_order = data.get("sort", "desc")
        match_mode = data.get("match_mode", "any")

        ws = get_ws("활동일지")
        records = ws.get_all_records()
        res = []
        for r in records:
            date_str, member, content = r.get("날짜"), r.get("회원명"), r.get("내용")
            if not (date_str and member and content):
                continue
            comb = f"{member} {content}".lower()
            cond = (all(k.lower() in comb for k in keywords) if match_mode == "all"
                    else any(k.lower() in comb for k in keywords))
            if not cond:
                continue
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            res.append({"날짜": date_str, "회원명": member, "내용": content, "_dt": dt})
        res.sort(key=lambda x: x["_dt"], reverse=(sort_order == "desc"))
        for r in res: 
            r.pop("_dt", None)
        return jsonify({
            "검색조건": {"키워드": keywords, "매칭방식": match_mode, "정렬": sort_order},
            "검색결과": res[:limit]
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/search_all_memo_by_text_from_natural", methods=["POST"])
def search_all_memo_by_text_from_natural():
    try:
        data = request.get_json(silent=True) or {}
        raw = data.get("text") or " ".join(data.get("keywords", []))
        if not (raw or "").strip():
            return jsonify({"error": "검색어가 없습니다."}), 400

        words = raw.split()
        has_all = "동시" in words
        keywords = [w for w in words if w != "동시"]

        payload = {"keywords": keywords, "limit": 20, "sort": "desc", "match_mode": "all" if has_all else "any"}

        # 각각 검색 실행 (dict 기반 라우트 재사용)
        with app.test_client() as c:
            a = c.post("/search_memo_by_text", json=payload)
            b = c.post("/search_activity_by_text_from_natural", json=payload)
            d = c.post("/search_counseling_by_text_from_natural", json=payload)

        def ext(resp):
            try:
                j = resp.get_json()
                return j.get("검색결과", [])
            except Exception:
                return []

        lines = []
        for label, resp in [("개인일지", a), ("활동일지", b), ("상담일지", d)]:
            lines.append(f"=== {label} ===")
            for r in ext(resp):
                lines.append(f"{r['날짜']} {r['회원명']} {r['내용']}")
            lines.append("")

        return Response("\n".join(lines), mimetype="text/plain; charset=utf-8")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500





# ======================================================================================
# 자연어 회원 검색(간단 키워드 매핑)
# ======================================================================================
@app.route("/members/search-nl", methods=["POST"])
def search_by_natural_language():
    try:
        data = request.get_json(force=True)
        query = data.get("query")
        if not query:
            return Response("query 파라미터가 필요합니다.", status=400)

        field, keyword = parse_natural_query(query)
        if not field or not keyword:
            return Response("자연어에서 검색 필드와 키워드를 찾을 수 없습니다.", status=400)

        ws = get_ws("DB")
        records = ws.get_all_records()
        if not records:
            return Response("레코드가 없습니다.", status=404)

        fk = field.strip()
        kw = str(keyword).strip().lower().replace(" ", "")
        filtered = [m for m in records if kw == str(m.get(fk, "")).strip().lower().replace(" ", "")]
        filtered.sort(key=lambda m: m.get("회원명", ""))
        if not filtered:
            return Response("조건에 맞는 회원이 없습니다.", status=200)

        lines = [
            f"{m.get('회원명','')} (회원번호: {m.get('회원번호','')}"
            + (f", 특수번호: {m.get('특수번호','')}" if m.get("특수번호") else "")
            + (f", 연락처: {m.get('휴대폰번호','')}" if m.get('휴대폰번호') else "")
            + (f", {remove_josa(str(m.get('코드','')).strip())}" if m.get('코드') else "")
            + ")"
            for m in filtered[:40]
        ]
        if len(filtered) > 40:
            lines.append("--- 다음 있음 ---")
        return Response("\n".join(lines), mimetype="text/plain")
    except Exception as e:
        traceback.print_exc()
        return Response(f"[서버 오류] {str(e)}", status=500)









# ======================================================================================
# 주문 처리 (이미지/텍스트 → JSON → memberslist API 또는 시트 저장)
# ======================================================================================
def call_memberslist_add_orders(payload: dict):
    """
    멤버리스트 API로 주문 데이터 전송
    - 기본 URL: MEMBERSLIST_API_URL (예: /add_orders)
    - 호환성: /addOrders 엔드포인트도 fallback 지원
    """
    if not MEMBERSLIST_API_URL:
        raise RuntimeError("MEMBERSLIST_API_URL 미설정")

    try:
        # 1️⃣ 기본 URL 시도
        r = requests.post(MEMBERSLIST_API_URL, json=payload, timeout=30)
        r.raise_for_status()
        try:
            return r.json()
        except ValueError:
            return {"ok": True, "raw": r.text}

    except requests.HTTPError as e:
        resp = e.response
        if resp is not None and resp.status_code == 404:
            # 2️⃣ 404일 경우 addOrders <-> add_orders fallback
            if "add_orders" in MEMBERSLIST_API_URL:
                fallback_url = MEMBERSLIST_API_URL.replace("add_orders", "addOrders")
            elif "addOrders" in MEMBERSLIST_API_URL:
                fallback_url = MEMBERSLIST_API_URL.replace("addOrders", "add_orders")
            else:
                raise

            r2 = requests.post(fallback_url, json=payload, timeout=30)
            r2.raise_for_status()
            try:
                return r2.json()
            except ValueError:
                return {"ok": True, "raw": r2.text}

        # 다른 HTTP 오류는 그대로 re-raise
        raise
    except requests.RequestException as e:
        raise RuntimeError(f"Memberslist RequestException: {e}") from e











def extract_order_from_uploaded_image(image_bytes: io.BytesIO):
    """
    업로드된 이미지에서 주문 정보를 추출하는 함수
    (GPT Vision / OCR 호출 로직을 여기에 구현)
    """
    try:
        # ✅ 실제 Vision API나 OCR 호출 코드가 들어가야 함
        # 예시: GPT API 호출 결과를 parsed_json으로 받음
        parsed_json = {
            "orders": [
                {"제품명": "노니", "제품가격": "20000", "PV": "20"}
            ]
        }
        return parsed_json
    except Exception as e:
        return {"error": str(e)}



# 👇 함수 정의는 최상위에서 시작
def _handle_image_order_upload(image_bytes: io.BytesIO, member_name: str, mode: str = "api"):
    # GPT Vision
    parsed = extract_order_from_uploaded_image(image_bytes)
    orders_list = ensure_orders_list(parsed)
    if not orders_list:
        return jsonify({"error": "GPT 응답이 올바른 JSON 형식이 아닙니다.", "응답": parsed}), 500

    # 공란 정책 반영
    for o in orders_list:
        o.setdefault("결재방법", "")
        o.setdefault("수령확인", "")
        # 날짜는 비워두면 downstream에서 처리

    if mode == "api":
        saved = call_memberslist_add_orders({"회원명": member_name, "orders": orders_list})
        # ✅ 임팩트 동기화(옵션) — 비활성화
        # call_impact_sync({"type": "order", "member": member_name, "orders": orders_list, "source": "sheet_gpt"})
        return jsonify({
            "mode": "api",
            "message": f"{member_name}님의 주문이 저장되었습니다. (memberslist API)",
            "추출된_JSON": orders_list,
            "저장_결과": saved
        }), 200

    if mode == "sheet":
        db_ws = get_ws("DB")
        recs = db_ws.get_all_records()
        member_info = next((r for r in recs if (r.get("회원명") or "").strip() == member_name), None)
        if not member_info:
            return jsonify({"error": f"회원 '{member_name}'을(를) 찾을 수 없습니다."}), 404

        orders_ws = get_ws("제품주문")
        # 헤더 보장
        values = orders_ws.get_all_values()
        if not values:
            orders_ws.append_row([
                "주문일자","회원명","회원번호","휴대폰번호","제품명",
                "제품가격","PV","결재방법","주문자_고객명","주문자_휴대폰번호",
                "배송처","수령확인"
            ])

        saved_rows = 0
        for od in orders_list:
            row = [
                od.get("주문일자", now_kst().strftime("%Y-%m-%d")),
                member_name,
                member_info.get("회원번호", ""),
                member_info.get("휴대폰번호", ""),
                od.get("제품명", ""),
                od.get("제품가격", ""),
                od.get("PV", ""),
                od.get("결재방법", ""),
                od.get("주문자_고객명", ""),
                od.get("주문자_휴대폰번호", ""),
                od.get("배송처", ""),
                od.get("수령확인", ""),
            ]
            orders_ws.insert_row(row, index=2)
            saved_rows += 1

        # ✅ 임팩트 동기화(옵션) — 비활성화
        # call_impact_sync({"type": "order", "member": member_name, "orders": orders_list, "source": "sheet_gpt"})
        return jsonify({"mode": "sheet", "status": "success", "saved_rows": saved_rows}), 200

    return jsonify({"error": "mode 값은 'api' 또는 'sheet'여야 합니다."}), 400






@app.route("/upload_order", methods=["POST"])
def upload_order_auto():
    # iPad/모바일/PC를 나눠 처리할 필요 없이 공통 핸들러로 통일
    mode = request.form.get("mode") or request.args.get("mode") or "api"
    member_name = (request.form.get("회원명") or "").strip()
    message_text = (request.form.get("message") or "").strip()
    image_file = request.files.get("image")
    image_url = request.form.get("image_url")

    if (not member_name) and "제품주문 저장" in message_text:
        member_name = message_text.replace("제품주문 저장", "").strip()

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

        return _handle_image_order_upload(mode, member_name, image_bytes)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500




# 텍스트 → 주문 JSON (OpenAI)
def parse_order_from_text(text: str):
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    prompt = f"""
다음 문장에서 주문 정보를 JSON 형식으로 추출하세요.
여러 개의 제품이 있을 경우 'orders' 배열에 모두 담으세요.
질문하지 말고 추출된 orders 전체를 그대로 저장할 준비를 하세요.
(이름, 휴대폰번호, 주소)는 소비자 정보임.
회원명, 결재방법, 수령확인, 주문일자 무시.
필드: 제품명, 제품가격, PV, 결재방법, 주문자_고객명, 주문자_휴대폰번호, 배송처.

입력 문장:
{text}

JSON 형식:
{{
  "orders": [
    {{
      "제품명": "...",
      "제품가격": ...,
      "PV": ...,
      "결재방법": "",
      "주문자_고객명": "...",
      "주문자_휴대폰번호": "...",
      "배송처": "..."
    }}
  ]
}}
"""
    payload = {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}], "temperature": 0}
    r = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    result_text = r.json()["choices"][0]["message"]["content"]
    clean_text = re.sub(r"```(?:json)?", "", result_text, flags=re.MULTILINE).strip()
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        return {"raw_text": result_text}




@app.route("/upload_order_text", methods=["POST"])
def upload_order_text():
    text = request.form.get("message") or (request.json.get("message") if request.is_json else None)
    if not text:
        return jsonify({"error": "message 필드가 필요합니다."}), 400

    m = re.match(r"^(\S+)\s*제품주문\s*저장", text)
    if not m:
        return jsonify({"error": "회원명을 찾을 수 없습니다."}), 400
    member_name = m.group(1)

    od = parse_order_from_text(text)
    orders_list = ensure_orders_list(od)
    if not orders_list:
        return jsonify({"error": "주문 정보를 추출하지 못했습니다.", "응답": od}), 400

    try:
        saved = call_memberslist_add_orders({"회원명": member_name, "orders": orders_list})
        # 임팩트 동기화(옵션)
        # call_impact_sync({"type": "order", "member": member_name, "orders": orders_list, "source": "sheet_gpt"})
        return jsonify({"status": "success", "회원명": member_name, "추출된_JSON": orders_list, "저장_결과": saved}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500




def handle_order_save(one_row: dict):
    ws = get_ws("제품주문")
    values = ws.get_all_values()
    if not values:
        ws.append_row(["주문일자","회원명","회원번호","휴대폰번호","제품명","제품가격","PV","결재방법","주문자_고객명","주문자_휴대폰번호","배송처","수령확인"])
    row = [
        process_order_date(one_row.get("주문일자", "")),
        one_row.get("회원명", ""),
        one_row.get("회원번호", ""),
        one_row.get("휴대폰번호", ""),
        one_row.get("제품명", ""),
        float(one_row.get("제품가격", 0) or 0),
        float(one_row.get("PV", 0) or 0),
        one_row.get("결재방법", ""),
        one_row.get("주문자_고객명", ""),
        one_row.get("주문자_휴대폰번호", ""),
        one_row.get("배송처", ""),
        one_row.get("수령확인", ""),
    ]
    ws.insert_row(row, index=2)




@app.route("/parse_and_save_order", methods=["POST"])
def parse_and_save_order():
    try:
        user_input = request.json.get("text", "")
        parsed = parse_order_text_rule(user_input)
        handle_order_save(parsed)
        # 임팩트 동기화(옵션)
        # call_impact_sync({"type": "order", "member": parsed.get("회원명", ""), "orders": [parsed], "source": "sheet_gpt"})
        return jsonify({"status": "success", "message": f"{parsed.get('회원명','')}님의 주문이 저장되었습니다.", "parsed": parsed}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500




# 최근 주문 5건 보여주고 삭제 유도
@app.route("/delete_order_request", methods=["POST"])
def delete_order_request():
    try:
        ws = get_ws("제품주문")
        values = ws.get_all_values()
        if not values or len(values) < 2:
            return jsonify({"message": "등록된 주문이 없습니다."}), 404
        headers = values[0]; rows = values[1:]

        def col(name): 
            return headers.index(name) if name in headers else None

        N = min(5, len(rows))
        response = []
        for i, row in enumerate(rows[:N], start=1):
            try:
                response.append({
                    "번호": i,
                    "회원명": row[col("회원명")] if col("회원명") is not None and len(row) > col("회원명") else "",
                    "제품명": row[col("제품명")] if col("제품명") is not None and len(row) > col("제품명") else "",
                    "가격": row[col("제품가격")] if col("제품가격") is not None and len(row) > col("제품가격") else "",
                    "PV": row[col("PV")] if col("PV") is not None and len(row) > col("PV") else "",
                    "주문일자": row[col("주문일자")] if col("주문일자") is not None and len(row) > col("주문일자") else "",
                })
            except Exception:
                continue
        return jsonify({"message": f"📌 최근 주문 내역 {len(response)}건입니다. 삭제할 번호(1~{len(response)})를 선택해 주세요.", "주문목록": response}), 200
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

        # 실제 행 번호(헤더 제외)
        real_rows = [i + 2 for i in range(N)]
        to_delete_rows = sorted([real_rows[n - 1] for n in nums], reverse=True)
        for r in to_delete_rows:
            ws.delete_rows(r)
        return jsonify({"message": f"{', '.join(map(str, nums))}번 주문이 삭제되었습니다.", "삭제행번호": to_delete_rows}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500











# ======================================================================================
# 헬스체크 & 디버그
# ======================================================================================
@app.route("/debug-intent", methods=["POST"], endpoint="debug_intent_v2")
def debug_intent_route():
    data = request.get_json(force=True) or {}
    text = (data.get("요청문") or data.get("text") or "").strip()
    intent = guess_intent(text)
    return jsonify({"ok": True, "intent": intent, "raw_text": text})





# 정상 작동






# -------------------- 실행 --------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True, use_reloader=False)


