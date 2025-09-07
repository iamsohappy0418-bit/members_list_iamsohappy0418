import re
import calendar
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from utils.sheets import get_gsheet_data, get_member_sheet, get_rows_from_sheet

# ---------------------------------------------------------
# 로거 설정 (중복 방지 포함)
# ---------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:  # ✅ 중복 방지
    handler = logging.StreamHandler()  # 콘솔 출력
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    

# ---------------------------------------------------------
# 1. 쿼리 정규화
# ---------------------------------------------------------
# 🔹 1. 입력 쿼리 정규화 함수
def normalize_query(query: str) -> str:
    # 1) 영문 → 대문자로 통일
    query = query.upper()
    
    # 2) 특수문자 제거 (한글/영문/숫자/공백만 남김)
    query = re.sub(r"[^가-힣A-Z0-9\s]", " ", query)

    # 3) 한글과 영문/숫자가 붙어 있으면 강제 분리
    query = re.sub(r"([가-힣])([A-Z0-9])", r"\1 \2", query)
    query = re.sub(r"([A-Z0-9])([가-힣])", r"\1 \2", query)

    # 4) 중복 공백 제거
    query = re.sub(r"\s+", " ", query).strip()

    return query



# =====================================================================
# ✅ fallback 자연어 검색
# =====================================================================
def fallback_natural_search(query: str) -> Dict[str, str]:
    query = query.strip()

    if re.fullmatch(r"\d{3}-\d{3,4}-\d{4}", query):
        return {"휴대폰번호": query}

    if re.fullmatch(r"\d{5,}", query):
        return {"회원번호": query}

    return {"회원명": query}



# ---------------------------------------------------------
# 1. 범용 검색 엔진 (옵션 지원)
# ---------------------------------------------------------
def search_members(data, search_params, options=None):
    """
    회원 검색 유틸
    - data: Worksheet 객체 또는 list(dict)
    - search_params: {"회원명": "이태수", "가입일__gte": "2024-01-01"} 등
    - options: {"match_mode": {"회원명": "partial", "코드": "exact", ...}}
        - default: 코드/회원번호 = exact, 나머지 = partial
    - 특수 규칙:
        "코드a" 또는 "코드 a" → 무조건 코드 필드에서 A 검색
    """

    # ✅ Worksheet 객체일 경우 자동 변환
    if hasattr(data, "get_all_records"):
        rows = data.get_all_records()
    else:
        rows = data

    results = []

    # ✅ 검색 모드 기본값
    default_match_mode = {
        "코드": "exact",
        "회원번호": "exact"
    }
    if options and "match_mode" in options:
        match_mode = {**default_match_mode, **options["match_mode"]}
    else:
        match_mode = default_match_mode

    # ✅ 특수 처리: search_params 에서 "query" 키워드가 들어왔을 때
    if "query" in search_params:
        query = search_params["query"].strip().lower()

        # "코드a" 또는 "코드 a" → 코드=A 검색
        if query in ["코드a", "코드 a"]:
            search_params = {"코드": "A"}

        # "코드 + 알파벳" 패턴 자동 처리
        elif query.startswith("코드"):
            code_value = query.replace("코드", "").strip().upper()
            if code_value:
                search_params = {"코드": code_value}
            else:
                search_params = {}

        else:
            # query 가 "회원명" 검색어로 들어왔다고 가정
            search_params = {"회원명": query}

    # ✅ 실제 검색 수행
    for row in rows:
        match = True
        for key, value in search_params.items():
            if not key:   # ✅ key가 None이면 스킵
                continue            

            field = key.split("__")[0]
            field_value = str(row.get(field, "")).strip()  # ✅ 공백 제거
            mode = match_mode.get(field, "partial")  # 기본은 부분 일치

            # 날짜 비교 (__gte, __lte)
            if "__gte" in key or "__lte" in key:
                try:
                    field_date = datetime.strptime(field_value, "%Y-%m-%d")
                    search_date = datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    match = False
                    break

                if "__gte" in key and field_date < search_date:
                    match = False
                    break
                if "__lte" in key and field_date > search_date:
                    match = False
                    break
                
            else:
                fv = field_value.lower()
                vv = value.strip().lower()

                if mode == "exact":
                    if fv != vv:
                        match = False
                        break
                elif mode == "partial":
                    if vv not in fv:
                        match = False
                        break
                else:  # 잘못된 옵션 → exact 처리
                    if fv != vv:
                        match = False
                        break

        if match:
            results.append(row)

    return results



# =====================================================================
# ✅ 시트 데이터 검색
# =====================================================================
def find_all_members_from_sheet(sheet_name: str, field: str, value: str) -> List[Dict]:
    results = []
    rows = get_rows_from_sheet(sheet_name)

    for row in rows:
        if str(row.get(field, "")).strip().upper() == value.upper():
            results.append(row)

    return results




# ---------------------------------------------------------
# 2. 자연어 → 조건 변환
# ---------------------------------------------------------
def parse_natural_query(query: str):
    conditions = {}
    today = datetime.today()

    if re.fullmatch(r"[가-힣]{2,4}", query):
        conditions["회원명"] = query
    if re.fullmatch(r"\d{3}-\d{3,4}-\d{4}", query):
        conditions["휴대폰번호"] = query
    if re.fullmatch(r"\d{5,}", query):
        conditions["회원번호"] = query

    if "오늘" in query:
        conditions["가입일"] = today.strftime("%Y-%m-%d")
    if "어제" in query:
        yesterday = today - timedelta(days=1)
        conditions["가입일"] = yesterday.strftime("%Y-%m-%d")
    if "이번 달" in query:
        first_day = today.replace(day=1)
        last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        conditions["가입일__gte"] = first_day.strftime("%Y-%m-%d")
        conditions["가입일__lte"] = last_day.strftime("%Y-%m-%d")
    if "지난 달" in query:
        last_month = today.month - 1 or 12
        year = today.year if today.month > 1 else today.year - 1
        first_day = datetime(year, last_month, 1)
        last_day = datetime(year, last_month, calendar.monthrange(year, last_month)[1])
        conditions["가입일__gte"] = first_day.strftime("%Y-%m-%d")
        conditions["가입일__lte"] = last_day.strftime("%Y-%m-%d")
    if "올해" in query:
        first_day = datetime(today.year, 1, 1)
        last_day = datetime(today.year, 12, 31)
        conditions["가입일__gte"] = first_day.strftime("%Y-%m-%d")
        conditions["가입일__lte"] = last_day.strftime("%Y-%m-%d")

    match = re.search(r"최근\s*(\d+)\s*일", query)
    if match:
        days = int(match.group(1))
        start_date = today - timedelta(days=days)
        conditions["가입일__gte"] = start_date.strftime("%Y-%m-%d")
        conditions["가입일__lte"] = today.strftime("%Y-%m-%d")

    match = re.search(r"최근\s*(\d+)\s*개월", query)
    if match:
        months = int(match.group(1))
        year = today.year
        month = today.month - months
        while month <= 0:
            month += 12
            year -= 1
        start_date = datetime(year, month, 1)
        conditions["가입일__gte"] = start_date.strftime("%Y-%m-%d")
        conditions["가입일__lte"] = today.strftime("%Y-%m-%d")

    match = re.search(r"최근\s*(\d+)\s*년", query)
    if match:
        years = int(match.group(1))
        start_date = today.replace(year=today.year - years)
        conditions["가입일__gte"] = start_date.strftime("%Y-%m-%d")
        conditions["가입일__lte"] = today.strftime("%Y-%m-%d")

    date_pattern = r"(\d{4}-\d{2}-\d{2})"
    match = re.search(r"(가입일|생년월일).*" + date_pattern + r".*이후", query)
    if match:
        field, date_val = match.group(1), match.group(2)
        conditions[f"{field}__gte"] = date_val
    match = re.search(r"(가입일|생년월일).*" + date_pattern + r".*이전", query)
    if match:
        field, date_val = match.group(1), match.group(2)
        conditions[f"{field}__lte"] = date_val
    match = re.search(r"(가입일|생년월일).*" + date_pattern, query)
    if match and not any(k.startswith(match.group(1)) for k in conditions):
        field, date_val = match.group(1), match.group(2)
        conditions[field] = date_val

    return {k: v for k, v in conditions.items() if k}



# =====================================================================
# ✅ 자연어 검색 (특수 규칙 + fallback)
# =====================================================================
def searchMemberByNaturalText(query: str):
    """
    자연어 기반 회원 검색
    - '코드a' 또는 '코드 a' 입력 시 → DB 시트 코드 필드에서 A 검색
    - '코드 b', '코드 c' 등도 동일 적용
    - 그 외 → fallback 자연어 검색 실행
    """

    query = query.strip().lower()
    logger.info(f"searchMemberByNaturalText called with query='{query}'")

    # ✅ "코드a" 또는 "코드 a"
    if query in ["코드a", "코드 a"]:
        logger.info("→ 특수 규칙 매칭: 코드=A")
        return find_all_members_from_sheet("DB", field="코드", value="A")

    # ✅ "코드 + 알파벳" 패턴
    if query.startswith("코드"):
        code_value = query.replace("코드", "").strip().upper()
        if code_value:
            logger.info(f"→ 코드 패턴 매칭: 코드={code_value}")
            return find_all_members_from_sheet("DB", field="코드", value=code_value)

    # ✅ fallback 경로
    conditions = fallback_natural_search(query)
    logger.info(f"→ fallback 경로 실행, conditions={conditions}")
    return search_members(get_gsheet_data(), conditions)



# ---------------------------------------------------------
# 3. 검색 실행 (구글시트 데이터 필터링)
# ---------------------------------------------------------
def search_member(query: str) -> Dict:
    members_data = get_gsheet_data()
    normalized = normalize_query(query)
    conditions = parse_natural_query(normalized)

    results = []
    for row in members_data:
        match = True
        for key, value in conditions.items():
            field = key.replace("__gte", "").replace("__lte", "")
            field_value = row.get(field, "")

            # ✅ 날짜 비교
            if "__gte" in key or "__lte" in key:
                try:
                    field_date = datetime.strptime(str(field_value), "%Y-%m-%d")
                    search_date = datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    match = False
                    break

                if "__gte" in key and field_date < search_date:
                    match = False
                    break
                if "__lte" in key and field_date > search_date:
                    match = False
                    break

            else:
                # ✅ 일반 비교 (대소문자 무시, 코드/회원번호는 exact)
                fv = str(field_value).strip().lower()
                vv = value.strip().lower()
                if field in ["코드", "회원번호"]:
                    if fv != vv:
                        match = False
                        break
                else:
                    if vv not in fv:  # 부분 일치 허용
                        match = False
                        break

        if match:
            results.append(row)

    return {
        "original": query,
        "normalized": normalized,
        "conditions": conditions,
        "results": results
    }




# ====================




