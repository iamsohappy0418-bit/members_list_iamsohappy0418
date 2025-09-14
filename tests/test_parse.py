import pytest
from parse import (
    guess_intent,
    preprocess_user_input,
    parse_registration,
    parse_request_and_update,
    parse_deletion_request,
    parse_order_text,
    parse_commission,
)


# -------------------------------
# intent 추론
# -------------------------------
@pytest.mark.parametrize("text,expected", [
    ("회원 등록 이태수", "register_member"),
    ("회원 수정 강소희", "update_member"),
    ("회원 삭제 홍길동", "delete_member"),
    ("회원 검색 이영숙", "search_member"),
    ("강소희", "search_member"),            # 이름만 입력
    ("강소희 전체정보", "member_select"),    # 전체정보
    ("이태수 주문 노니 2개", "order_auto"),
    ("홍길동 후원수당 조회", "search_commission_by_nl"),
])
def test_guess_intent(text, expected):
    assert guess_intent(text) == expected


# -------------------------------
# preprocess
# -------------------------------
def test_preprocess_user_input_name_only():
    result = preprocess_user_input("이태수")
    assert "query" in result
    assert isinstance(result["query"], str)


# -------------------------------
# 회원 등록 파서
# -------------------------------
@pytest.mark.parametrize("text,expected_name,expected_number,expected_phone", [
    ("회원등록 이태수 회원번호 123456 010-1234-5678",
     "이태수", "123456", "010-1234-5678"),
    ("김영희 회원등록", "김영희", None, None),
])
def test_parse_registration(text, expected_name, expected_number, expected_phone):
    name, number, phone = parse_registration(text)
    assert name == expected_name
    assert number == expected_number
    assert phone == expected_phone


# -------------------------------
# 회원 수정 파서
# -------------------------------
def test_parse_request_and_update():
    text = "홍길동 휴대폰번호 010-1111-2222 주소 서울 강남구"
    updates = parse_request_and_update(text)
    assert updates["휴대폰번호"] == "010-1111-2222"
    assert updates["주소"].startswith("서울")


# -------------------------------
# 회원 삭제 파서
# -------------------------------
def test_parse_deletion_request():
    text = "홍길동 주소 삭제"
    parsed = parse_deletion_request(text)
    assert parsed["member"] == "홍길동"
    assert "주소" in parsed["fields"]


# -------------------------------
# 주문 파서
# -------------------------------
def test_parse_order_text():
    text = "이수민 주문 노니 2개 카드 서울 주소 오늘"
    parsed = parse_order_text(text)
    assert parsed["intent"] == "order_auto"
    assert parsed["query"]["제품명"] == "노니"
    assert parsed["query"]["수량"] == 2
    assert parsed["query"]["결제방법"] == "카드"
    assert "서울" in parsed["query"]["배송처"] or parsed["query"]["배송처"] == ""


# -------------------------------
# 후원수당 파서
# -------------------------------
def test_parse_commission():
    text = "홍길동 2025-08-07 좌 10000 우 20000"
    result = parse_commission(text)
    assert result["status"] == "success"
    data = result["data"]
    assert data["회원명"] == "홍길동"
    assert data["합계_좌"] == 10000
    assert data["합계_우"] == 20000


# ======================================================================================
# parser_commission
# ======================================================================================

def process_date(raw: Optional[str]) -> str:
    """
    '오늘/어제/내일', YYYY-MM-DD, 2025.8.7 / 2025/08/07 등 → YYYY-MM-DD
    """
    from datetime import timedelta
    try:
        if not raw:
            return now_kst().strftime("%Y-%m-%d")
        s = raw.strip()
        if "오늘" in s:
            return now_kst().strftime("%Y-%m-%d")
        if "어제" in s:
            return (now_kst() - timedelta(days=1)).strftime("%Y-%m-%d")
        if "내일" in s:
            return (now_kst() + timedelta(days=1)).strftime("%Y-%m-%d")
        m = re.search(r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})", s)
        if m:
            y, mth, d = m.groups()
            return f"{int(y):04d}-{int(mth):02d}-{int(d):02d}"
    except Exception:
        pass
    return now_kst().strftime("%Y-%m-%d")


# -------------------------------
# ✅ 순수 파싱 전용
# -------------------------------
def parse_commission_core(text: str) -> Dict[str, Any]:
    """
    자연어 문장에서 후원수당 정보를 추출 (시트 저장 없음)
    예: "홍길동 2025-08-07 좌 10000 우 20000"
    """
    result = {
        "회원명": None,
        "기준일자": process_date("오늘"),
        "합계_좌": 0,
        "합계_우": 0,
    }

    if not text:
        return result

    tokens = text.split()
    if tokens:
        result["회원명"] = tokens[0]

    # 날짜 추출
    date_match = re.search(r"(20\d{2}[./-]\d{1,2}[./-]\d{1,2})", text)
    if date_match:
        result["기준일자"] = process_date(date_match.group(1))

    # 좌/우 점수 추출
    left = re.search(r"(?:좌|왼쪽)\s*(\d+)", text)
    right = re.search(r"(?:우|오른쪽)\s*(\d+)", text)
    if left:
        result["합계_좌"] = int(left.group(1))
    if right:
        result["합계_우"] = int(right.group(1))

    return result


# -------------------------------
# ✅ 기존 함수 (시트 저장 포함)
# -------------------------------
def parse_commission(text: str) -> Dict[str, Any]:
    """
    자연어 문장에서 후원수당 정보를 추출하고 시트에 저장
    """
    core_data = parse_commission_core(text)

    if not core_data.get("회원명"):
        return {"status": "fail", "reason": "회원명이 비어있습니다."}

    # ✅ 시트에 저장
    ws = get_worksheet("후원수당")
    headers = ws.row_values(1)
    row = [core_data.get(h, "") for h in headers]
    ws.append_row(row, value_input_option="USER_ENTERED")

    return {"status": "success", "data": core_data}


from parse import parse_commission_core

def test_parse_commission_core():
    text = "홍길동 2025-08-07 좌 10000 우 20000"
    data = parse_commission_core(text)
    assert data["회원명"] == "홍길동"
    assert data["기준일자"] == "2025-08-07"
    assert data["합계_좌"] == 10000
    assert data["합계_우"] == 20000


