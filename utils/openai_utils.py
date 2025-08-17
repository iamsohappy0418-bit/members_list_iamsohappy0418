# utils/openai_utils.py
import os
import io
import re
import json
import base64
import requests
from typing import List, Dict, Any

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = os.getenv("OPENAI_API_URL")  # e.g. https://api.openai.com/v1/chat/completions

def _ensure_orders_list(data: Any) -> List[Dict[str, Any]]:
    """응답을 무조건 orders 리스트 형태로 보정"""
    if isinstance(data, dict) and "orders" in data:
        return data["orders"] or []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    return []

def openai_vision_extract_orders(image_bytes: io.BytesIO) -> List[Dict[str, Any]]:
    """
    이미지 → 주문 JSON 추출 (gpt-4o)
    반환: [{'제품명':..., '제품가격':..., 'PV':..., '주문자_고객명':..., '주문자_휴대폰번호':..., '배송처':..., '결재방법': '', '수령확인': ''}, ...]
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY 미설정")
    if not OPENAI_API_URL:
        raise RuntimeError("OPENAI_API_URL 미설정")

    image_b64 = base64.b64encode(image_bytes.getvalue()).decode("utf-8")

    prompt = (
        "이미지를 분석하여 JSON 형식으로 추출하세요. "
        "여러 개의 제품이 있을 경우 'orders' 배열에 모두 담으세요. "
        "질문하지 말고 추출된 orders 전체를 그대로 저장할 준비를 하세요. "
        "(이름, 휴대폰번호, 주소)는 소비자 정보임. "
        "회원명, 결재방법, 수령확인, 주문일자 무시. "
        "필드: 제품명, 제품가격, PV, 주문자_고객명, 주문자_휴대폰번호, 배송처"
    )

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
            ]
        }],
        "temperature": 0
    }

    r = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=60)
    r.raise_for_status()

    content = r.json()["choices"][0]["message"]["content"]
    clean = re.sub(r"```(?:json)?", "", content, flags=re.MULTILINE).strip()

    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        data = {"raw_text": content}

    orders_list = _ensure_orders_list(data)

    # 정책: 결재방법/수령확인은 공란 유지 + 문자열 필드 trim
    for o in orders_list:
        o.setdefault("결재방법", "")
        o.setdefault("수령확인", "")
        for k, v in list(o.items()):
            if isinstance(v, str):
                o[k] = v.strip()

    return orders_list
