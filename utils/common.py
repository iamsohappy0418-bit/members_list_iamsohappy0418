import time
import re
from datetime import datetime, timedelta, timezone
import pytz
from typing import Optional


# ======================================================================================
# ✅ 디버그용 유틸
# ======================================================================================
def simulate_delay(seconds: int = 1):
    """작업 시작/완료를 출력하며 지정된 시간만큼 대기 (디버그용)"""
    print("작업 시작")
    time.sleep(seconds)
    print("작업 완료")



# ======================================================================================
# ✅ 날짜 유틸 공통 시간 유틸
# ======================================================================================
# ✅ 한국 시간
def now_kst() -> datetime:
    """한국시간(KST) 기준 현재 시각 반환"""
    return datetime.now(timezone(timedelta(hours=9)))


# ========================================================================
# **주문 저장 시 날짜 입력 처리(오늘/어제/내일/포맷 변환)를 담당
# ========================================================================
# ✅ 제품주문시 날짜 입력으로 등록처리 
# ✅ 날짜 처리 통합 함수
def process_order_date(raw_date: str) -> str:
    """
    주문 저장 시 날짜 입력 처리
    - "오늘", "어제", "내일" → 실제 날짜
    - YYYY-MM-DD / YYYY.MM.DD / YYYY/MM/DD → YYYY-MM-DD
    - 실패 시 오늘 날짜 반환
    """
    try:
        if not raw_date or raw_date.strip() == "":
            return now_kst().strftime('%Y-%m-%d')

        text = raw_date.strip()
        today = now_kst()

        # ✅ "오늘", "어제", "내일"
        if "오늘" in text:
            return today.strftime('%Y-%m-%d')
        elif "어제" in text:
            return (today - timedelta(days=1)).strftime('%Y-%m-%d')
        elif "내일" in text:
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')

        # ✅ YYYY-MM-DD 포맷 직접 확인
        try:
            dt = datetime.strptime(text, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

        # ✅ YYYY.MM.DD or YYYY/MM/DD → YYYY-MM-DD 변환
        match = re.search(r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})", text)
        if match:
            y, m, d = match.groups()
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    except Exception as e:
        print(f"[날짜 파싱 오류] {e}")

    # ✅ 실패 시 오늘 날짜 반환
    return now_kst().strftime('%Y-%m-%d')

    




# ======================================================================================
# ✅ 문자열 정리 유틸
# ======================================================================================
def remove_josa(s: str) -> str:
    """단어 끝의 조사(이/가/은/는/을/를/과/와/의/으로/로) 제거"""
    return re.sub(r'(이|가|은|는|을|를|과|와|의|으로|로)$', '', s.strip())


def remove_spaces(s: str) -> str:
    """문자열 내 모든 공백 제거"""
    return re.sub(r'\s+', '', s)


def split_to_parts(s: str) -> list[str]:
    """문자열을 공백 단위로 분리하여 리스트 반환"""
    return re.split(r'\s+', s.strip())


# ✅ 조사 제거 함수 (이게 꼭 필요!)
def remove_josa(text):
    """
    조사 제거 (으로/로/은/는/이/가/을/를)
    """
    return re.sub(r'(으로|로|은|는|이|가|을|를|한|인|에게|에)?$', '', text)




def parse_dt(s: str):
    """
    문자열을 datetime 객체로 변환
    지원 포맷: YYYY-MM-DD HH:MM, YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
    실패하면 None 반환
    """
    if not s:
        return None
    s = s.strip()
    for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def match_condition(text: str, keywords: list[str], mode: str = "any") -> bool:
    """
    주어진 text에 대해 키워드 매칭 검사
    - mode="any": 하나라도 포함되면 True
    - mode="all": 전부 포함되어야 True
    """
    if not text or not keywords:
        return False
    if mode == "all":
        return all(k in text for k in keywords)
    return any(k in text for k in keywords)



