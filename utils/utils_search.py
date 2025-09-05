from datetime import datetime, timedelta
import calendar
import re


# ------------------------------
# 조건에 맞는 데이터 검색
# ------------------------------
def search_members(sheet, search_params):
    results = []
    for row in sheet:
        match = True
        for key, value in search_params.items():
            field = key.split("__")[0]
            field_value = str(row.get(field, ""))

            # 날짜 비교
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
                # OR 조건 + 대소문자 무시
                values = [v.strip().lower() for v in value.split(",")]
                if field_value.lower() not in values:
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

    # 절대 날짜
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

    return conditions


