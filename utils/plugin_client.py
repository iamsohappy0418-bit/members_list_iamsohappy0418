# utils/plugin_client.py
import os
import importlib

# ✅ .env 에서 모듈 이름 읽기 (기본값: memberslist_onrender_com__jit_plugin)
PLUGIN_MODULE = os.getenv("PLUGIN_MODULE", "memberslist_onrender_com__jit_plugin")

try:
    plugin_module = importlib.import_module(PLUGIN_MODULE)
except ImportError as e:
    raise ImportError(f"❌ 플러그인 모듈을 불러올 수 없습니다: {PLUGIN_MODULE}") from e

# ✅ 모듈에서 함수 가져오기
try:
    searchMemo = getattr(plugin_module, "searchMemo")
    searchMemoFromText = getattr(plugin_module, "searchMemoFromText")
except AttributeError as e:
    raise ImportError(f"❌ {PLUGIN_MODULE} 모듈에서 searchMemo / searchMemoFromText 를 찾을 수 없습니다.") from e


# ✅ 호출 래퍼
def call_searchMemo(payload: dict):
    """ searchMemo API 호출 (동기 래퍼) """
    return searchMemo(payload)


def call_searchMemoFromText(payload: dict):
    """ searchMemoFromText API 호출 (동기 래퍼) """
    return searchMemoFromText(payload)



