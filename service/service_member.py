import gspread
from flask import jsonify

from utils import (
    clean_tail_command, clean_value_expression, remove_spaces,
    get_member_sheet, safe_update_cell, delete_row,
)

from parser.field_map import field_map


from parser.parser_member import parse_conditions

from utils import get_sheet, get_member_sheet, delete_row
from config import SHEET_KEY, GOOGLE_SHEET_TITLE
from utils.sheets import get_worksheet, get_member_sheet, delete_row

from utils.utils_search import find_all_members_from_sheet, fallback_natural_search
from utils.sheets import get_rows_from_sheet
from utils.utils_search import find_all_members_from_sheet



# ==============================
# 회원 등록 (Create)
# ==============================
def register_member(name: str, number: str, phone: str) -> bool:
    """
    DB 시트에 새로운 회원을 등록
    예: register_member("홍길동", "123456", "010-1234-5678")
    """
    sheet = get_member_sheet()
    headers = sheet.row_values(1)

    data = {
        "회원명": name,
        "회원번호": number,
        "휴대폰번호": phone,
    }

    # header 순서에 맞춰서 값 넣기
    row = [data.get(h, "") for h in headers]
    sheet.append_row(row, value_input_option="USER_ENTERED")
    return True


# ==============================
# 회원 조회 (Read)
# ==============================
def find_member(name: str):
    """
    DB 시트에서 회원명으로 회원을 조회
    여러 건일 수 있으므로 list 반환
    예: [{"회원명": "홍길동", "회원번호": "123456", "휴대폰번호": "010-1234-5678"}]
    """
    sheet = get_member_sheet()
    rows = sheet.get_all_records()

    result = []
    for row in rows:
        if str(row.get("회원명", "")).strip() == str(name).strip():
            result.append(row)
    return result


# ==============================
# 회원 수정 (Update)
# ==============================
def update_member(name: str, updates: dict) -> bool:
    """
    특정 회원의 여러 필드 값을 수정
    예: update_member("홍길동", {"주소": "부산", "휴대폰번호": "010-0000-0000"})
    """
    sheet = get_member_sheet()
    headers = sheet.row_values(1)
    rows = sheet.get_all_records()

    updated = False
    for i, row in enumerate(rows, start=2):  # 2행부터 데이터 시작
        if str(row.get("회원명", "")).strip() == str(name).strip():
            for field, value in updates.items():
                if field in headers:
                    col_idx = headers.index(field) + 1
                    safe_update_cell(sheet, i, col_idx, value)
                    updated = True
            break
    return updated


# ==============================
# 회원 삭제 (Delete)
# ==============================
def delete_member(name: str) -> bool:
    """
    DB 시트에서 특정 회원 전체 행 삭제
    예: delete_member("홍길동")
    """
    sheet = get_member_sheet()
    rows = sheet.get_all_records()

    for i, row in enumerate(rows, start=2):  # 2행부터 데이터 시작
        if str(row.get("회원명", "")).strip() == str(name).strip():
            sheet.delete_rows(i)
            return True
    return False


# ==============================
# 회원명 텍스트 탐색 (보정용)
# ==============================
def find_member_in_text(text: str) -> str | None:
    """
    입력 문장에서 DB 시트의 회원명을 탐색하여 반환
    - 여러 명이 매칭되면 긴 이름 우선 반환
    - 없으면 None
    """
    if not text:
        return None

    sheet = get_member_sheet()
    member_names = sheet.col_values(1)[1:]  # 첫 행은 헤더 제외

    # 긴 이름부터 매칭되도록 정렬 (예: '김철수' > '김')
    member_names = sorted([n.strip() for n in member_names if n], key=len, reverse=True)

    for name in member_names:
        if name in text:
            return name
    return None


def find_member_internal(name: str = "", number: str = "", code: str = "") -> list[dict]:
    """
    회원명/회원번호/코드 기반 단순 검색
    - name: 부분일치 허용 (소문자 비교)
    - number: 정확히 일치 (회원번호)
    - code: 정확히 일치 (대소문자 무시)
    """
    sheet = get_member_sheet()
    records = sheet.get_all_records()

    results = []
    seen = set()  # ✅ 중복 제거용

    name = (name or "").strip().lower()
    number = (number or "").strip()
    code = (code or "").strip().lower()

    for row in records:
        member_name = str(row.get("회원명", "")).strip().lower()
        member_number = str(row.get("회원번호", "")).strip()
        member_code = str(row.get("코드", "")).strip().lower()

        matched = False

        # 회원명 부분 일치
        if name and name in member_name:
            matched = True
        # 회원번호 정확 일치
        elif number and number == member_number:
            matched = True
        # 코드 정확 일치 (대소문자 무시)
        elif code and code == member_code:
            matched = True

        if matched:
            key = f"{member_name}:{member_number}:{member_code}"
            if key not in seen:   # ✅ 중복 방지
                results.append(row)
                seen.add(key)

    return results






def clean_member_data(data: dict) -> dict:
    """
    회원 데이터 전처리 함수 (기본 구현)
    - 문자열이면 strip() 처리
    - None 은 "" 로 변환
    - 불필요한 공백 제거
    """
    if not data:
        return {}

    cleaned = {}
    for k, v in data.items():
        if isinstance(v, str):
            cleaned[k] = v.strip()
        elif v is None:
            cleaned[k] = ""
        else:
            cleaned[k] = v
    return cleaned



def register_member_internal(name: str, number: str = "", phone: str = ""):
    """
    회원 등록/조회 내부 로직
    - name: 회원명 (필수)
    - number: 회원번호 (선택, 있으면 중복 체크)
    - phone: 휴대폰번호 (선택)
    """
    sheet = get_member_sheet()
    headers = sheet.row_values(1)
    rows = sheet.get_all_records()

    # ✅ 기존 회원 여부 확인
    for row in rows:
        row_name = str(row.get("회원명", "")).strip()
        row_number = str(row.get("회원번호", "")).strip()

        # 1) 회원명 + 회원번호가 동시에 같은 경우 → 동일인
        if name == row_name and number and number == row_number:
            return {
                "status": "exists",
                "message": f"{name} ({number})님은 이미 등록된 회원입니다.",
                "data": row
            }

        # 2) 회원번호가 같은데 이름이 다른 경우 → 중복 번호 에러
        if number and number == row_number and name != row_name:
            return {
                "status": "error",
                "message": f"⚠️ 회원번호 {number}는 이미 '{row_name}'님에게 등록되어 있습니다."
            }

    # ✅ 신규 등록
    new_row = [""] * len(headers)
    if "회원명" in headers:
        new_row[headers.index("회원명")] = name
    if "회원번호" in headers and number:
        new_row[headers.index("회원번호")] = number
    if "휴대폰번호" in headers and phone:
        new_row[headers.index("휴대폰번호")] = phone

    sheet.insert_row(new_row, 2)
    return {
        "status": "created",
        "message": f"{name} 회원 신규 등록 완료",
        "data": {
            "회원명": name,
            "회원번호": number,
            "휴대폰번호": phone
        }
    }




def update_member_internal(요청문):
    try:
        # ... 파싱 및 시트 업데이트 로직 ...
        return jsonify({
            "status": "success",
            "message": f"요청 처리 완료: {요청문}"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500









def delete_member_internal(name: str):
    """
    회원명 기준으로 DB 시트에서 해당 회원 전체 행 삭제
    삭제 전에 "백업" 시트에 해당 회원 정보 저장
    """
    if not name:
        return {"error": "회원명이 필요합니다."}, 400

    sheet = get_member_sheet()
    rows = sheet.get_all_records()
    headers = sheet.row_values(1)

    for i, row in enumerate(rows, start=2):  # 헤더 제외
        if row.get("회원명", "").strip() == name:
            # ✅ 백업 시트 가져오기
            backup_sheet = get_worksheet("백업")

            if not backup_sheet:
                return {"error": "백업 시트를 찾을 수 없습니다. '백업' 시트를 먼저 생성해주세요."}, 500

            # ✅ 백업 저장
            backup_row = [row.get(h, "") for h in headers]
            backup_sheet.insert_row(backup_row, 2)

            # ✅ 원본 삭제
            delete_row(sheet, i)

            return {"message": f"{name}님의 회원 정보가 '백업' 시트에 저장된 후 삭제되었습니다."}, 200

    return {"error": f"{name} 회원을 찾을 수 없습니다."}, 404








def delete_member_field_nl_internal(text: str, fields: list = None):
    """
    회원 필드 삭제 내부 로직 (자연어 기반)
    - '회원명', '회원번호'는 삭제 불가
    - '회원명 + 삭제'는 전체 삭제 방지
    """
    sheet = get_member_sheet()
    rows = sheet.get_all_records()
    headers = sheet.row_values(1)

    # ✅ 회원명 추출
    name = None
    for row in rows:
        if str(row.get("회원명", "")) in text:
            name = row.get("회원명")
            break
    if not name:
        return {"error": "회원명을 찾을 수 없습니다."}, 404

    # ✅ 전체 삭제 방지
    if text.strip().startswith(name) and text.strip().endswith("삭제"):
        return {"error": "⚠️ 회원 전체 삭제는 별도 API(/delete_member)를 사용하세요."}, 400

    # ✅ 삭제 키워드 체크
    delete_keywords = ["삭제", "삭제해줘", "비워", "비워줘", "초기화", "초기화줘", "없애", "없애줘", "지워", "지워줘"]
    parts = split_to_parts(text)
    has_delete_kw = any(remove_spaces(dk) in [remove_spaces(p) for p in parts] for dk in delete_keywords)
    if not has_delete_kw:
        return {"error": "삭제 명령이 포함되어야 합니다."}, 400

    # ✅ 필드 추출
    matched_fields = []
    for alias, canonical in field_map.items():
        if remove_spaces(alias) in [remove_spaces(p) for p in parts]:
            if canonical in headers and canonical not in matched_fields:
                matched_fields.append(canonical)

    if fields:
        for f in fields:
            if f in headers and f not in matched_fields:
                matched_fields.append(f)

    if not matched_fields:
        return {"error": "삭제할 필드를 찾을 수 없습니다."}, 400

    # ✅ 보호 필드 차단
    protected_fields = {"회원명", "회원번호"}
    if any(f in protected_fields for f in matched_fields):
        return {"error": "⚠️ 회원명, 회원번호는 삭제 불가 필드입니다. 수정 API를 사용하세요."}, 400

    # ✅ 대상 행 찾기
    target_row, row_index = None, None
    for i, row in enumerate(rows, start=2):
        if row.get("회원명") == name:
            target_row, row_index = row, i
            break
    if not target_row:
        return {"error": f"{name} 회원을 찾을 수 없습니다."}, 404

    # ✅ 필드 값 삭제
    for field in matched_fields:
        col_index = headers.index(field) + 1
        sheet.update_cell(row_index, col_index, "")

    return {
        "message": f"{name}님의 {', '.join(matched_fields)} 필드가 삭제되었습니다.",
        "deleted_fields": matched_fields
    }, 200














def process_member_query(user_input: str):
    # 1️⃣ 자연어 → 정제된 쿼리
    processed = build_member_query(user_input)
    search_key = processed["query"]

    # 2️⃣ 쿼리 → 조건 딕셔너리
    conditions = parse_conditions(search_key)

    # 3️⃣ Google Sheets 조회
    sheet = get_member_sheet()
    records = sheet.get_all_records()
    results = []

    for row in records:
        match = True
        for field, value in conditions.items():
            cell_value = str(row.get(field, "")).strip()
            if field == "코드":
                cell_value = cell_value.upper()  # 코드값 대문자 통일
            if cell_value != value:
                match = False
                break
        if match:
            results.append(row)

    return {
        "original": user_input,
        "processed": search_key,
        "conditions": conditions,
        "results": results
    }




def searchMemberByNaturalText(query: str):
    """
    자연어 기반 회원 검색
    - '코드a' 또는 '코드 a' 입력 시 → DB 시트 코드 필드에서 A 검색
    - '코드 b', '코드 c' 등도 동일 적용
    - 그 외 → fallback 자연어 검색
    """

    query = query.strip().lower()  # 입력값 소문자 변환

    # ✅ "코드a" 또는 "코드 a"
    if query in ["코드a", "코드 a"]:
        return find_all_members_from_sheet("DB", field="코드", value="A")

    # ✅ "코드 + 알파벳" 패턴
    if query.startswith("코드"):
        code_value = query.replace("코드", "").strip().upper()
        if code_value:
            return find_all_members_from_sheet("DB", field="코드", value=code_value)

    # ✅ 그 외 → fallback 자연어 검색
    return fallback_natural_search(query)




