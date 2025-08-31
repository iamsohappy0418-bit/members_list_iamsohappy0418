import re

def clean_content(text: str, member_name: str = None) -> str:
    """
    저장/검색 공통 내용 정제:
    1) 앞쪽 공백 및 기호 (: . , ' " 등) 제거
    2) 회원명 제거
    3) 마지막 마침표는 그대로 둠
    """
    if not text:
        return ""

    # 1. 앞쪽 불필요 기호 + 공백 제거
    text = re.sub(r'^[\s:：,，\.\'\"“”‘’]+', '', text)

    # 2. 회원명 제거
    if member_name:
        text = text.replace(member_name, "")

    # 3. 앞뒤 공백 정리
    text = text.strip()

    return text
