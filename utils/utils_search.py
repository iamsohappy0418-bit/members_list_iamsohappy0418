from datetime import datetime, timedelta
import calendar
import re


# ------------------------------
# 조건에 맞는 데이터 검색
# ------------------------------
from datetime import datetime

def search_members(data, search_params):
    """
    회원 검색 유틸
    - data: Worksheet 객체 또는 list(dict)
    - search_params: {"회원명": "이태수", "가입일자__gte": "2024-01-01"} 등
    """

    # ✅ Worksheet 객체일 경우 자동 변환
    if hasattr(data, "get_all_records"):
        rows = data.get_all_records()
    else:
        rows = data

    results = []
   

    for row in rows:

       

        match = True
        for key, value in search_params.items():

            if not key:   # ✅ key가 None이면 스킵
                continue            

            field = key.split("__")[0]
            field_value = str(row.get(field, "")).strip()  # ✅ 공백 제거

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
                # ✅ 코드/회원번호는 반드시 정확히 일치 (대소문자 무시)
                if field in ["코드", "회원번호"]:
                    if field_value.lower() != value.strip().lower():
                        match = False
                        break
                else:
                    # 일반 문자열 비교 (부분 일치 허용, 대소문자 무시)
                    if value.strip().lower() not in field_value.lower():
                        match = False
                        break

        if match:
            results.append(row)

    
    return results




# ------------------------------
# 자연어 → 검색 조건 변환
# ------------------------------
def parse_natural_query(query: str):
    conditions = {}
    today = datetime.today()

    # ✅ 회원명 / 휴대폰 / 회원번호 직접 검색
    if re.fullmatch(r"[가-힣]{2,4}", query):
        conditions["회원명"] = query
    if re.fullmatch(r"\d{3}-\d{3,4}-\d{4}", query):
        conditions["휴대폰번호"] = query
    if re.fullmatch(r"\d{5,}", query):
        conditions["회원번호"] = query

    # 상대적 날짜
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

    # 최근 N일
    match = re.search(r"최근\s*(\d+)\s*일", query)
    if match:
        days = int(match.group(1))
        start_date = today - timedelta(days=days)
        conditions["가입일__gte"] = start_date.strftime("%Y-%m-%d")
        conditions["가입일__lte"] = today.strftime("%Y-%m-%d")

    # 최근 N개월
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

    # ✅ 최근 N년 (추가)
    match = re.search(r"최근\s*(\d+)\s*년", query)
    if match:
        years = int(match.group(1))
        start_date = today.replace(year=today.year - years)
        conditions["가입일__gte"] = start_date.strftime("%Y-%m-%d")
        conditions["가입일__lte"] = today.strftime("%Y-%m-%d")




    # 절대 날짜 (YYYY-MM-DD)
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


