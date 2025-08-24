# utils/sheets.py
import os
import time
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import WorksheetNotFound, APIError

# ⬇️ .env 자동 로드 (로컬/파일 존재 시)
if os.getenv("RENDER") is None:
    try:
        from dotenv import load_dotenv
        if os.path.exists(".env"):
            load_dotenv(".env")  # 프로젝트 루트의 .env
    except Exception:
        pass

GOOGLE_SHEET_TITLE = os.getenv("GOOGLE_SHEET_TITLE")

# 내부 캐시(지연 초기화)
_gclient = None
_gsheet = None


def _require_sheet_title():
    if not GOOGLE_SHEET_TITLE:
        raise EnvironmentError("환경변수 GOOGLE_SHEET_TITLE이 설정되지 않았습니다.")


# ✅ Google Sheets 클라이언트 생성
def get_gspread_client():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")

    """
    Render: GOOGLE_CREDENTIALS_JSON 사용
    Local : GOOGLE_CREDENTIALS_PATH(기본 'credentials.json') 파일 사용
    """

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    if creds_json:  # Render 환경
        import json
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:  # 로컬 개발용
        creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Google credentials 파일을 찾을 수 없습니다: {creds_path}")
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)

    return gspread.authorize(creds)


def _ensure_client_and_sheet():
    """모듈 전역 캐시에 gspread client와 sheet 핸들을 지연 초기화."""
    global _gclient, _gsheet
    if _gclient is None:
        _gclient = get_gspread_client()
    if _gsheet is None:
        _require_sheet_title()
        _gsheet = _gclient.open(GOOGLE_SHEET_TITLE)


def get_sheet() -> gspread.Spreadsheet:
    """스프레드시트 핸들 반환 (캐시)."""
    _ensure_client_and_sheet()
    return _gsheet


# ✅ 워크시트 핸들 가져오기
def get_ws(sheet_name: str):
    client = get_gspread_client()
    sheet_title = os.getenv("GOOGLE_SHEET_TITLE")
    if not sheet_title:
        raise EnvironmentError("환경변수 GOOGLE_SHEET_TITLE이 설정되지 않았습니다.")
    try:
        return client.open(sheet_title).worksheet(sheet_name)
    except WorksheetNotFound:
        raise FileNotFoundError(f"워크시트를 찾을 수 없습니다: {sheet_name}")
    

# ✅ 통일된 get_all: dict 리스트 반환 워크시트 모든 데이터 가져오기 (엑셀 원본 구조)
def get_all(ws):
    """
    워크시트의 모든 레코드를 dict 리스트로 반환합니다.
    헤더 행은 자동으로 key 로 사용됩니다.
    """
    return ws.get_all_records()


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
                time.sleep(delay)
                delay *= 2
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
def get_member_sheet():
    return get_ws("DB")

def get_order_sheet():
    return get_ws("제품주문")

def get_commission_sheet():
    return get_ws("후원수당")

def get_counseling_sheet():
    return get_ws("상담일지")

def get_personal_memo_sheet():
    # ✅ 개인메모 시트명을 '개인일지'로 고정
    return get_ws("개인일지")

def get_activity_log_sheet():
    return get_ws("활동일지")


# ==============================
# 📌 헬퍼 함수
# ==============================
def get_member_info(member_name: str):
    """
    DB 시트에서 회원명으로 회원번호/휴대폰번호 조회
    (간편 조회용; dict 레코드 기반)
    """
    ws = get_member_sheet()
    records = ws.get_all_records()
    for row in records:
        if (row.get("회원명") or "").strip() == member_name.strip():
            return row.get("회원번호", ""), row.get("휴대폰번호", "")
    return "", ""




