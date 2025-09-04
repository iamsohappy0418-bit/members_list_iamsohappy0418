# utils/plugin_client.py
import os
import requests

MEMBERSLIST_API_URL = os.getenv("MEMBERSLIST_API_URL")  # .env에 추가해야 함, 예: https://memberslist.onrender.com

def call_searchMemo(payload: dict):
    """ searchMemo API 호출 """
    if not MEMBERSLIST_API_URL:
        raise RuntimeError("❌ MEMBERSLIST_API_URL 환경변수가 설정되지 않았습니다.")
    url = f"{MEMBERSLIST_API_URL.rstrip('/')}/search_memo"
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])

def call_searchMemoFromText(payload: dict):
    """ searchMemoFromText API 호출 (자연어) """
    if not MEMBERSLIST_API_URL:
        raise RuntimeError("❌ MEMBERSLIST_API_URL 환경변수가 설정되지 않았습니다.")
    url = f"{MEMBERSLIST_API_URL.rstrip('/')}/search_memo"
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])


