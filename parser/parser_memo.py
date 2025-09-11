import re
from typing import Tuple, Optional, Dict

from utils import now_kst, get_worksheet



# ======================================================================================
# ✅ 메모 요청 파서
# ======================================================================================
def parse_request_line(text: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    자연어 문장에서 메모 저장 요청 파싱
    예: '이태수 상담일지 저장 오늘은 비가 옵니다'
    반환: (회원명, 시트명, 액션, 내용)
    """
    if not text or not text.strip():
        return None, None, None, None

    s = text.strip()
    m = re.match(
        r"^\s*(\S+)\s*(상담\s*일지|개인\s*일지|활동\s*일지)\s*(저장|기록|입력)\s*(.*)$",
        s,
    )
    if m:
        member, sheet_raw, action, content = m.groups()
        sheet = sheet_raw.replace(" ", "")
        return member, sheet, action, content

    # fallback: 단순 분리
    parts = s.split(maxsplit=3)
    if len(parts) < 3:
        return None, None, None, None

    member, sheet, action = parts[0], parts[1].replace(" ", ""), parts[2]
    content = parts[3] if len(parts) > 3 else ""
    return member, sheet, action, content


# ======================================================================================
# ✅ 메모 파서 + 저장
# ======================================================================================
def parse_memo(text: str) -> dict:
    text = (text or "").strip()
    diary_types = ["상담일지", "개인일지", "활동일지"]

    result = {"회원명": None, "일지종류": None, "내용": None, "keywords": []}

    # ✅ 전체메모 검색 (띄어쓰기 허용)
    normalized = text.replace(" ", "")
    if normalized.startswith("전체메모") and "검색" in text:
        keyword = text.split("검색", 1)[1].strip()
        result.update({
            "일지종류": "전체",
            "keywords": [keyword] if keyword else []
        })
        return result

    # ✅ 일반 저장/검색
    for dt in diary_types:
        if dt in text:
            before, after = text.split(dt, 1)
            result["회원명"] = before.strip()
            result["일지종류"] = dt

            if "저장" in after:
                result["내용"] = after.replace("저장", "").strip()
            elif "검색" in after:
                keyword = after.replace("검색", "").strip()
                result["keywords"] = [keyword] if keyword else []
            return result

    return result



