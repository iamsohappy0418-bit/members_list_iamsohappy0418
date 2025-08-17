# parser.py
# =============================================================================
# 순수 파싱/유틸 모듈 (외부 I/O 없음)
# - 날짜/시간 처리
# - 회원 등록/수정 파싱
# - 주문(텍스트) 파싱
# =============================================================================
import re
from datetime import datetime, timedelta
import pytz
from typing import Tuple, Optional, List, Dict, Any





# --- 시간/날짜 ----------------------------------------------------------------
def now_kst():
    return datetime.now(pytz.timezone("Asia/Seoul"))

def process_order_date(raw: str | None) -> str:
    """'오늘/어제/내일', YYYY-MM-DD, 2025.8.7 / 2025/08/07 등 → YYYY-MM-DD"""
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
        try:
            dt = datetime.strptime(s, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
        m = re.search(r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})", s)
        if m:
            y, mth, d = m.groups()
            return f"{int(y):04d}-{int(mth):02d}-{int(d):02d}"
    except Exception:
        pass
    return now_kst().strftime("%Y-%m-%d")



def parse_natural_query(text: str):
    return {"query": text}

def parse_deletion_request(text: str):
    return {"삭제대상": text}




# --- 공통 정리 ----------------------------------------------------------------
def clean_tail_command(text: str) -> str:
    phrases = [
        "로 정확히 수정해줘","으로 정확히 수정해줘","정확히 수정해줘",
        "변경해줘","수정해줘","바꿔줘","변경","수정","바꿔",
        "저장해줘","기록","입력","해주세요","해줘","해"
    ]
    s = text
    for p in phrases:
        s = re.sub(rf"(?:\s*(?:으로|로))?\s*{re.escape(p)}\s*[^\w가-힣]*$", "", s)
    return s.strip()

def parse_korean_phone(text: str) -> str | None:
    m = re.search(r"01[016789]-?\d{3,4}-?\d{4}", text)
    if not m:
        return None
    digits = re.sub(r"\D", "", m.group())
    return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"

def parse_member_number(text: str) -> str | None:
    m = re.search(r"\b\d{6,8}\b", text)
    return m.group() if m else None


# parser/parser.py

def guess_intent(text: str) -> str:
    """자연어 문장에서 intent 추측"""
    if "주문" in text and "저장" in text:
        return "save_order"
    if "주문" in text and any(k in text for k in ["조회", "찾아", "검색"]):
        return "find_order"
    if "후원수당" in text and any(k in text for k in ["조회", "알려줘", "검색"]):
        return "find_commission"
    if any(k in text for k in ["상담일지", "개인일지", "활동일지"]):
        return "save_memo"
    if any(k in text for k in ["삭제", "지워", "제거"]):
        return "delete_member"
    if any(k in text for k in ["수정", "변경", "업데이트"]):
        return "update_member"
    if any(k in text for k in ["등록", "추가"]):
        return "register_member"
    if any(k in text for k in ["조회", "찾기", "검색"]):
        return "find_member"
    return "unknown"



# --- 회원 등록 파싱 ------------------------------------------------------------
def parse_registration(text: str):
    """문장에서 (이름, 회원번호, 휴대폰) 추출"""
    s = (text or "").replace("\n", " ").replace("\r", " ").strip()
    name, number, phone = "", "", ""
    m = re.search(r"(?:회원등록\s*)?([가-힣]{2,10})\s*회원번호\s*(\d+)", s)
    if m:
        name = m.group(1).strip()
        number = re.sub(r"\D", "", m.group(2))
    else:
        m2 = re.search(r"^([가-힣]{2,10})\s*회원등록$", s)
        if m2:
            name = m2.group(1).strip()
        else:
            m3 = re.search(r"[가-힣]{2,10}", s)
            if m3:
                name = m3.group(0)
    p = parse_korean_phone(s)
    phone = p or ""
    return (name or None), (number or None), (phone or None)

# --- 회원 수정 파싱 ------------------------------------------------------------
def infer_field_from_value(v: str) -> str | None:
    v = v.strip()
    if re.match(r"010[-]?\d{3,4}[-]?\d{4}", v):
        return "휴대폰번호"
    if re.fullmatch(r"\d{6,8}", re.sub(r"\D", "", v)):
        return "회원번호"
    if re.search(r"(좌측|우측|라인|왼쪽|오른쪽)", v):
        return "계보도"
    if re.fullmatch(r"[a-zA-Z0-9@!#%^&*]{6,20}", v):
        return "비밀번호"
    return None

def parse_request_and_update(nl: str, member: dict) -> tuple[dict, dict]:
    """
    자연어 요청에서 필드/값을 추출해 member dict 갱신.
    반환: (갱신된 member, 변경된필드 dict)
    """
    changed = {}
    text = (nl or "").strip()
    keys = ["주소","휴대폰번호","회원번호","비밀번호","가입일자","생년월일","통신사",
            "친밀도","근무처","계보도","소개한분","메모","코드","리더님","분류","회원단계","연령/성별","직업"]
    positions = []
    for k in keys:
        for m in re.finditer(rf"{k}\s*(?:를|은|는|이|가|:|：)?", text):
            positions.append((m.start(), k))
    positions.sort()

    def set_field(field, value):
        member[field] = value
        member[f"{field}_기록"] = f"(기록됨: {value})"
        changed[field] = value

    for i, (start, k) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        block = text[start:end]
        m = re.search(rf"{k}(?:를|은|는|이|가|:|：)?\s*(.+)", block)
        if not m: 
            continue
        val = clean_tail_command(m.group(1).strip()).rstrip("'\"“”‘’.,)")
        if k == "휴대폰번호":
            val = parse_korean_phone(val) or re.sub(r"\D", "", val)
            if val and re.fullmatch(r"010\d{8}", re.sub(r"\D", "", val or "")):
                digits = re.sub(r"\D", "", val)
                val = f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
        elif k == "회원번호":
            mm = parse_member_number(val)
            val = mm or re.sub(r"\D", "", val)
        elif k == "가입일자":
            val = process_order_date(val)
        elif k == "생년월일":
            mm = re.search(r"\d{4}-\d{2}-\d{2}", val)
            val = mm.group(0) if mm else ""
        elif k == "통신사":
            val = re.sub(r"(?:을|를|은|는|이|가|으로|로)$", "", val).strip()
        elif k == "친밀도":
            m2 = re.search(r"(상|중|하)", val)
            val = m2.group(1) if m2 else ""
        elif k == "계보도":
            nm = re.search(r"([가-힣]{2,10})\s*(좌측|우측|라인|왼쪽|오른쪽)", val)
            if nm:
                val = f"{nm.group(1)}{nm.group(2)}"
            val = val.replace(" ", "")
        elif k == "소개한분":
            nm = re.search(r"(소개한분|소개자|추천인)[은는을이]?\s*([가-힣]{2,10})", block)
            if nm:
                val = nm.group(2)
            val = re.sub(r"(?:을|를|은|는|이|가|의|으로|로)$", "", val)
        set_field(k, val)

    if not positions:
        tokens = text.split()
        if len(tokens) >= 2:
            value = clean_tail_command(" ".join(tokens[1:]))
            inferred = infer_field_from_value(value)
            if inferred:
                if inferred == "회원번호":
                    value = re.sub(r"\D", "", value)
                elif inferred == "휴대폰번호":
                    digits = re.sub(r"\D", "", value)
                    if len(digits) == 11 and digits.startswith("010"):
                        value = f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
                set_field(inferred, value)
        for tok in tokens:
            if re.fullmatch(r"010[-]?\d{3,4}[-]?\d{4}|010\d{8}", tok):
                digits = re.sub(r"\D", "", tok)
                phone = f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
                set_field("휴대폰번호", phone)
            elif re.fullmatch(r"\d{6,8}", tok):
                set_field("회원번호", tok)
    return member, changed

# --- 주문 텍스트(규칙 기반) ----------------------------------------------------
def parse_order_text_rule(text: str):
    """
    자연어: '김지연 노니 2개 카드 주문 저장'
    반환 dict: 회원명/제품명/수량/결재방법/배송처/주문일자
    """
    res = {}
    m = re.match(r"(\S+)(?:님)?", text)
    if m: res["회원명"] = m.group(1)
    pm = re.search(r"([\w가-힣]+)\s*(\d+)\s*개", text)
    if pm:
        res["제품명"] = pm.group(1); res["수량"] = int(pm.group(2))
    else:
        res["제품명"] = "제품"; res["수량"] = 1
    if "카드" in text: res["결재방법"] = "카드"
    elif "현금" in text: res["결재방법"] = "현금"
    elif "계좌" in text: res["결재방법"] = "계좌이체"
    else: res["결재방법"] = "카드"
    am = re.search(r"(?:주소|배송지)[:：]\s*(.+?)(?:$|\s)", text)
    res["배송처"] = (am.group(1).strip() if am else "")
    res["주문일자"] = process_order_date(text)
    return res




def parse_natural_query(text: str) -> Tuple[Optional[str], Optional[str]]:
    text = text.strip()
    if any(k in text for k in ["조회", "검색", "찾아"]):
        m = re.match(r"^(\S+)\s*(조회|검색|찾아)", text)
        if m:
            return ("회원명", m.group(1))
    return (None, None)



from typing import Tuple, Optional   # ✅ 추가

def parse_natural_query(text: str) -> Tuple[Optional[str], Optional[str]]:
    text = text.strip()
    if any(k in text for k in ["조회", "검색", "찾아"]):
        m = re.match(r"^(\S+)\s*(조회|검색|찾아)", text)
        if m:
            return ("회원명", m.group(1))
    return (None, None)


def parse_deletion_request(text: str) -> dict:
    """
    삭제 요청 문장에서 회원명과 삭제할 필드 추출
    예: "이태수 휴대폰번호 삭제" → {"member": "이태수", "fields": ["휴대폰번호"]}
    """
    text = text.strip()
    result = {"member": None, "fields": []}

    # 회원명 추출 (맨 앞 단어)
    parts = text.split()
    if parts:
        result["member"] = parts[0]

    # 삭제 대상 필드 추출
    for keyword in ["휴대폰번호", "주소", "카드번호", "비밀번호"]:
        if keyword in text:
            result["fields"].append(keyword)

    return result


