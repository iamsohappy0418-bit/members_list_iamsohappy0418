# utils/plugin_client.py
import os
import requests

# ✅ 환경변수에서 API URL 읽기 (예: https://memberslist.onrender.com)
MEMBERSLIST_API_URL = os.getenv("MEMBERSLIST_API_URL")

if not MEMBERSLIST_API_URL:
    raise RuntimeError("❌ 환경변수 MEMBERSLIST_API_URL 이 설정되지 않았습니다. .env 파일을 확인하세요.")


def call_searchMemo(payload: dict):
    """
    searchMemo API 호출 (키워드 기반 검색)
    """
    url = f"{MEMBERSLIST_API_URL.rstrip('/')}/search_memo"
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return r.json().get("results", [])
    except requests.RequestException as e:
        raise RuntimeError(f"❌ call_searchMemo 요청 실패: {e}")


def call_searchMemoFromText(payload: dict):
    """
    searchMemoFromText API 호출 (자연어 검색)
    """
    url = f"{MEMBERSLIST_API_URL.rstrip('/')}/search_memo"
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return r.json().get("results", [])
    except requests.RequestException as e:
        raise RuntimeError(f"❌ call_searchMemoFromText 요청 실패: {e}")


