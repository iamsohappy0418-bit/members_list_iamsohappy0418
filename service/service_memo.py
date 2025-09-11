import re

import traceback
from datetime import datetime, timedelta
import unicodedata


# ===== project: utils =====
from utils import (
    # 시간/날짜
    now_kst, parse_dt,

    # 문자열 정리
    clean_tail_command, clean_value_expression, clean_content,

    # 시트
    get_counseling_sheet, get_personal_memo_sheet, get_activity_log_sheet, get_worksheet,

    # 키워드 매칭
    is_match, match_condition,
)





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







def normalize_korean(text: str) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFC", text)   # 유니코드 정규화
    t = re.sub(r"\s+", " ", t)               # 연속 공백 정리
    return t.strip().lower()


def keyword_match(content_lower: str, clean_keywords: list, search_mode="any") -> bool:
    if not clean_keywords:
        return False

    normalized_content = normalize_korean(content_lower)
    results = []

    for k in clean_keywords:
        k_norm = normalize_korean(k)
        found = k_norm in normalized_content
        results.append(found)
        print(f"[DEBUG] keyword_match | keyword={k_norm} | "
              f"in_content={found} | content={normalized_content[:50]}...")

    if search_mode == "동시검색":
        return all(results)
    return any(results)





# ======================================================================================
# ✅ 통합 검색 (Core)
# ======================================================================================


def search_memo_core(sheet_name, keywords, search_mode="any", member_name=None,
                     start_date=None, end_date=None, limit=20):
    results = []
    sheet = get_worksheet(sheet_name)
    if not sheet:
        print(f"[ERROR] ❌ 시트를 가져올 수 없습니다: {sheet_name}")
        return []

    rows = sheet.get_all_records()

    start_dt, end_dt = None, None
    try:
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except Exception:
        pass

    for idx, row in enumerate(rows, start=1):
        raw_content = str(row.get("내용", ""))
        content = clean_content(raw_content, member_name)
        content = clean_value_expression(content).lower()

        member = str(row.get("회원명", "")).strip()
        date_str = str(row.get("날짜", "")).strip()

        # ✅ 키워드 준비
        clean_keywords = [k.strip().lower() for k in keywords if k]
        content_lower = content.lower()

        # ✅ 최종 검색 직전 출력
        print("=" * 60)
        print(f"[DEBUG][최종검색 직전] sheet={sheet_name}, row={idx}")
        print(f"  회원명={member}, 날짜={date_str}")
        print(f"  content_lower={content_lower[:200]}")
        print(f"  clean_keywords={clean_keywords}")
        print("=" * 60)

        if member_name and member_name != "전체" and member != member_name:
            continue

        if date_str:
            try:
                row_date = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
                if start_dt and row_date < start_dt:
                    continue
                if end_dt and row_date > end_dt:
                    continue
            except Exception:
                pass

        if not keyword_match(content_lower, clean_keywords, search_mode):
            continue

        appended = {
            "날짜": date_str,
            "회원명": member,
            "내용": content,
            "일지종류": sheet_name
        }
        results.append(appended)

        if len(results) >= limit:
            break

    # ✅ 최종 결과 요약
    print(f"[DEBUG] ✅ 최종 results({sheet_name}) | {len(results)}건")
    return results
