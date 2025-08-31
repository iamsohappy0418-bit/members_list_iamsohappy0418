import re

def clean_content(text: str, member_name: str = None) -> str:
    """
    검색 키워드 정제를 위한 함수
    1) 특수문자 제거
    2) 회원명 제거
    3) 불용어 제거
    4) 정제된 키워드 문자열 반환
    """
    import re

    if not text:
        return ""

    # 1. 특수문자 제거 (한글, 영어, 숫자, 공백만 허용)
    text = re.sub(r"[^\w가-힣\s]", " ", text)

    # 2. 회원명 제거
    if member_name:
        text = text.replace(member_name, "")

    # 3. 불용어 제거 (조사, 접속사 등)
    stopwords = {
        "은", "는", "이", "가", "을", "를", "에", "의", "로", "과", "와", "도",
        "그리고", "하지만", "또한", "에서", "까지", "부터", "한", "중"
    }

    tokens = text.lower().split()
    filtered_tokens = [t for t in tokens if t not in stopwords and len(t) > 1]

    return " ".join(filtered_tokens)
