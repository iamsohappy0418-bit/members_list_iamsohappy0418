# utils/memo_utils.py
from datetime import datetime
import logging

from utils.plugin_client import call_searchMemo, call_searchMemoFromText


# 📌 예시 데이터 (실제 환경에서는 API 결과로 대체)
def get_memo_results(query):
    return [
        {"날짜": "2025-08-27", "내용": "오늘 오후에 비가 온다 했는데 비는 오지 않고 날은 무덥습니다", "회원명": "이태수", "종류": "개인일지"},
        {"날짜": "2025-08-26", "내용": "오늘은 포항으로 후원을 가고 있습니다. 하늘에 구름이 많고 오후에는 비가 온다고 합니다", "회원명": "이태수", "종류": "개인일지"},
        {"날짜": "2025-08-10", "내용": "오늘은 비가 오지 않네요", "회원명": "이판사", "종류": "개인일지"},
        {"날짜": "2025-08-04", "내용": "이경훈을 상담했습니다. 비도 많이 옵니다", "회원명": "이태수", "종류": "상담일지"},
        {"날짜": "2025-08-26", "내용": "오늘 하늘에 구름이 많이 꼈고 저녁에 비가 온다고 하는데 확실하지 않습니다", "회원명": "이태수", "종류": "활동일지"},
    ]


# 📌 결과 포맷터 (개인일지 / 상담일지 / 활동일지 블록 구분)
def format_memo_results(results):
    """
    검색된 메모 결과를 정리해서 문자열 블록과 카테고리별 리스트로 반환
    - 날짜는 YYYY-MM-DD 형식으로 출력
    - 정렬은 하루 단위 최신순
    - 출력 순서: 활동일지 → 상담일지 → 개인일지
    - 출력 형식: · (YYYY-MM-DD, 회원명) 내용
    """
    # ✅ 하루 단위 최신순 정렬
    try:
        results.sort(
            key=lambda r: datetime.strptime(str(r.get("날짜", "1900-01-01")).split()[0], "%Y-%m-%d"),
            reverse=True
        )
    except Exception:
        pass

    personal, counsel, activity = [], [], []

    for r in results:
        date = str(r.get("날짜") or "").split()[0]
        content = r.get("내용") or ""
        member = r.get("회원명") or ""
        mode = r.get("일지종류") or r.get("종류")

        if date and member:
            line = f"· ({date}, {member}) {content}"
        elif date:
            line = f"· ({date}) {content}"
        elif member:
            line = f"· ({member}) {content}"
        else:
            line = f"· {content}"

        if mode == "개인일지":
            personal.append(line)
        elif mode == "상담일지":
            counsel.append(line)
        elif mode == "활동일지":
            activity.append(line)

    output_text = "🔎 검색 결과\n\n"
    if activity:
        output_text += "🗂 활동일지\n" + "\n".join(activity) + "\n\n"
    if counsel:
        output_text += "📂 상담일지\n" + "\n".join(counsel) + "\n\n"
    if personal:
        output_text += "📒 개인일지\n" + "\n".join(personal) + "\n\n"

    # ✅ 항상 text 포함할 변수 생성
    human_readable_text = output_text.strip()

    return {
        "text": human_readable_text,   # 최상위 전체 블록
        "lists": {
            "활동일지": activity,
            "상담일지": counsel,
            "개인일지": personal,
            "text": human_readable_text  # ✅ lists 안에도 text 포함
        }
    }








def filter_results_by_member(results, member_name):
    """
    검색 결과(results) 중 특정 회원명(member_name)만 필터링
    """
    if not member_name:
        return results
    return [r for r in results if r.get("회원명") == member_name]








# 로거 설정
logger = logging.getLogger("memo_utils")
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


def handle_search_memo(data: dict):
    """
    searchMemo와 searchMemoFromText 자동 분기 처리 + 로깅 (동기 버전)
    """
    # 1) 자연어 요청 (text 필드가 있는 경우)
    if "text" in data:
        query = data["text"]
        logger.info(f"[FromText-Direct] text 필드 감지 → searchMemoFromText 실행 | query='{query}'")
        return call_searchMemoFromText({"text": query})

    # 2) keywords가 없는 경우 → 자연어 변환
    if not data.get("keywords"):
        mode = data.get("mode", "전체")
        keywords_text = " ".join(data.get("keywords", [])) if data.get("keywords") else ""
        search_mode_text = "동시" if data.get("search_mode") == "동시검색" else ""
        date_text = ""
        if data.get("start_date") and data.get("end_date"):
            date_text = f"{data['start_date']}부터 {data['end_date']}까지"

        query = f"{mode}일지 검색 {keywords_text} {search_mode_text} {date_text}".strip()
        logger.info(f"[FromText-Converted] keywords 없음 → query 변환 후 searchMemoFromText 실행 | query='{query}'")
        return call_searchMemoFromText({"text": query})

    # 3) 정상 content 기반 요청 → searchMemo 실행
    logger.info(f"[Content-Mode] keywords 감지 → searchMemo 실행 | keywords={data.get('keywords')}, mode={data.get('mode')}")
    return call_searchMemo(data)





