# utils/sheets.py
import os, time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import APIError
from dotenv import load_dotenv



# 🔄 .env 파일 로드 (필요한 경우)
load_dotenv()

# 환경변수 가져오기
# 🔐 gspread 인증 클라이언트 생성
def get_gspread_client():
    """Google Sheets 클라이언트 생성"""
    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    sheet_title = os.getenv("GOOGLE_SHEET_TITLE")

    if not sheet_title:
        raise EnvironmentError("환경변수 GOOGLE_SHEET_TITLE이 설정되지 않았습니다.")
    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"Google credentials 파일을 찾을 수 없습니다: {creds_path}")

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    return gspread.authorize(creds)









# 📑 워크시트 핸들 가져오기
def get_ws(sheet_name: str):
    """
    워크시트(탭) 핸들 반환
    - sheet_name: 'DB', '제품주문' 등 워크시트 이름
    """
    try:
        return get_sheet().worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        raise FileNotFoundError(f"워크시트를 찾을 수 없습니다: {sheet_name}")


# 📋 워크시트 모든 데이터 가져오기
def get_all(ws):
    """
    워크시트에서 모든 행 데이터를 가져오기
    - 반환: (headers, rows)
    """
    rows = ws.get_all_values()
    if not rows:
        return [], []
    headers, data = rows[0], rows[1:]
    return headers, data


# ✅ 호환성을 위해 별칭 제공
get_worksheet = get_ws




# ================================================================================================
# 셀 안전 업데이트 (재시도 포함)
def safe_update_cell(sheet, row: int, col: int, value, clear_first=True, max_retries=3, delay=2):
    for attempt in range(1, max_retries + 1):
        try:
            if clear_first:
                sheet.update_cell(row, col, "")
            sheet.update_cell(row, col, value)
            return True
        except APIError as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status == 429:  # rate limit
                time.sleep(delay); delay *= 2
            else:
                raise
    return False


# 헤더 매핑 (컬럼명 → 인덱스)
def header_maps(sheet):
    headers = [h.strip() for h in sheet.row_values(1)]
    idx = {h: i + 1 for i, h in enumerate(headers)}
    idx_l = {h.lower(): i + 1 for i, h in enumerate(headers)}
    return headers, idx, idx_l




# ==============================
# 📌 전용 워크시트 핸들러
# ==============================

# 📄 회원(DB) 시트 가져오기
def get_member_sheet():
    return get_ws("DB")

# 📄 제품주문 시트 가져오기
def get_order_sheet():
    return get_ws("제품주문")

# 📄 후원수당 시트 가져오기
def get_commission_sheet():
    return get_ws("후원수당")

# 📄 상담일지 시트 가져오기
def get_counseling_sheet():
    return get_ws("상담일지")

# 📄 개인메모 시트 가져오기
def get_personal_memo_sheet():
    return get_ws("개인일지")

# 📄 활동일지 시트 가져오기
def get_activity_log_sheet():
    return get_ws("활동일지")

# ==============================
# 📌 헬퍼 함수
# ==============================
# 📄 DB 시트에서 회원번호/휴대폰번호 조회
def get_member_info(member_name: str):
    ws = get_ws("DB")
    records = ws.get_all_records()
    for row in records:
        if (row.get("회원명") or "").strip() == member_name.strip():
            return row.get("회원번호", ""), row.get("휴대폰번호", "")
    return "", ""




