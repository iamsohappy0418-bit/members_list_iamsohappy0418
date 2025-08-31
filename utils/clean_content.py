def clean_content(text: str, member_name: str = None) -> str:
    print("⚙ 원본 text:", text)

    if not text:
        return ""

    # 🎯 불필요한 앞뒤 공백 및 기호만 제거 (전체 문자열은 유지)
    text = text.strip(" \t:：,，.'\"“”‘’")
    print("⚙ 기호제거 후:", text)

    if member_name:
        text = text.replace(member_name, "")
        print("⚙ 회원명 제거 후:", text)

    text = text.strip()
    print("⚙ 최종 정리 후:", text)

    return text
