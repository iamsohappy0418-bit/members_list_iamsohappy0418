import traceback
from utils.sheets import get_counseling_sheet, get_personal_memo_sheet, get_activity_log_sheet
from utils.common import now_kst, parse_dt, match_condition
from utils.sheets import get_worksheet
from datetime import timedelta
from utils.common import parse_dt, is_match


# ======================================================================================
# ✅ 메모 저장
# ======================================================================================
def save_memo(sheet_name: str, member_name: str, content: str) -> bool:
    """
    상담일지 / 개인일지 / 활동일지 저장
    """
    if not member_name or not content:
        raise ValueError("회원명과 내용은 필수 입력 항목입니다.")

    if sheet_name == "상담일지":
        sheet = get_counseling_sheet()
    elif sheet_name == "개인일지":
        sheet = get_personal_memo_sheet()
    elif sheet_name == "활동일지":
        sheet = get_activity_log_sheet()
    else:
        raise ValueError(f"지원하지 않는 일지 종류: {sheet_name}")

    ts = now_kst().strftime("%Y-%m-%d %H:%M")
    sheet.insert_row([ts, member_name.strip(), content.strip()], index=2)
    return True




# ======================================================================================
# ✅ 기본 검색
# ======================================================================================
def find_memo(keyword: str, sheet_name: str = "상담일지") -> list:
    """
    메모(상담일지/개인일지/활동일지)에서 키워드 검색
    """
    try:
        sheet = get_worksheet(sheet_name)
        if not sheet:
            print(f"[ERROR] ❌ 시트를 가져올 수 없습니다: {sheet_name}")
            return []

        all_records = sheet.get_all_records()
        results = []
        for row in all_records:
            row_text = " ".join(str(v) for v in row.values())
            if keyword in row_text:
                results.append(row)

        print(f"[INFO] ✅ '{sheet_name}' 시트에서 '{keyword}' 검색 결과 {len(results)}건 발견")
        return results
    except Exception as e:
        print(f"[ERROR] find_memo 오류: {e}")
        return []


# ======================================================================================
# ✅ 고급 검색 (날짜 범위 / 여러 키워드)
# ======================================================================================
def search_in_sheet(sheet_name, keywords, search_mode="any",
                    start_date=None, end_date=None, limit=20):
    sheet = get_worksheet(sheet_name)
    rows = sheet.get_all_values()
    if not rows or len(rows[0]) < 3:
        return [], False

    records = rows[1:]
    results = []
    for row in records:
        if len(row) < 3:
            continue

        작성일자, 회원명, 내용 = (row[0] or "").strip(), (row[1] or "").strip(), (row[2] or "").strip()
        작성일_dt = parse_dt(작성일자)
        if 작성일_dt is None:
            continue

        if start_date and 작성일_dt < start_date:
            continue
        if end_date and 작성일_dt > (end_date + timedelta(days=1) - timedelta(seconds=1)):
            continue

        combined_text = f"{회원명} {내용}"
        if match_condition(combined_text, keywords, search_mode):
            results.append({
                "작성일자": 작성일자,
                "회원명": 회원명,
                "내용": 내용,
                "_작성일_dt": 작성일_dt
            })

    results.sort(key=lambda x: x["_작성일_dt"], reverse=True)
    for r in results:
        r.pop("_작성일_dt", None)

    has_more = len(results) > limit
    return results[:limit], has_more




# ======================================================================================
# ✅ 통합 검색 (Core)
# ======================================================================================
def search_memo_core(sheet_name, keywords, search_mode="any", member_name=None, limit=20):
    """
    시트에서 메모를 검색하는 핵심 함수
    - sheet_name: "상담일지", "개인일지", "활동일지"
    - keywords: ["중국", "세미나"]
    - search_mode: "동시검색" 또는 "any"
    - member_name: "이태수" 등
    """
    results = []
    sheet = get_worksheet(sheet_name)
    if not sheet:
        print(f"[ERROR] ❌ 시트를 가져올 수 없습니다: {sheet_name}")
        return []

    rows = sheet.get_all_records()

    for row in rows:
        content = row.get("내용", "").strip().lower()
        member = row.get("회원명", "").strip()

        # ✅ 1. 작성자 일치 필터
        if member_name and author != member_name:
            continue

        # ✅ 2. 키워드/회원명 포함 여부
        if not is_match(content, keywords, member_name, search_mode):
            continue

        results.append(row)


    return results










