"""
parser/clean_utils.py
문자열 정리 유틸 (parser 전용 wrapper)

⚠️ 실제 구현은 utils.text_cleaner 에 있으며,
   parser 쪽에서 clean_utils 를 import 해도 그대로 동작하도록
   호환성 레이어 역할만 수행합니다.
"""

from utils.text_cleaner import (
    clean_tail_command,
    clean_value_expression,
    clean_content,
)

__all__ = [
    "clean_tail_command",
    "clean_value_expression",
    "clean_content",
]
