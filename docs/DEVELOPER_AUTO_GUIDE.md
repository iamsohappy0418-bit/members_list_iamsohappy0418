# 📑 API Route 자동 문서 (docstring 기반)

이 문서는 `app.py`에서 자동 추출한 라우트 목록 + docstring 설명을 포함합니다.

| 경로(Path) | 함수명(Function) | 설명 (docstring) |
|------------|-----------------|------------------|
| `/` | `home` | 홈(Health Check) API |
| `/debug_sheets` | `debug_sheets` | 시트 디버그 API |
| `/find_member` | `find_member_route` | 회원 조회 API |
| `/members/search-nl` | `search_by_natural_language` | 회원 자연어 검색 API |
| `/update_member` | `update_member_route` | 회원 수정 API |
| `/save_member` | `save_member` | 회원 저장/수정 API |
| `/register_member` | `register_member_route` | 회원 등록 API |
| `/delete_member` | `delete_member_route` | 회원 삭제 API |
| `/delete_member_field_nl` | `delete_member_field_nl` | 회원 필드 삭제 API |
| `/upload_order` | `upload_order_auto` | 제품 주문 업로드 자동 분기 API |
| `/upload_order_ipad` | `upload_order_ipad` | 제품 주문 업로드 API (iPad) |
| `/upload_order_pc` | `upload_order_pc` | 제품 주문 업로드 API (PC) |
| `/upload_order_text` | `upload_order_text` | 자연어 기반 주문 저장 API |
| `/add_orders` | `add_orders` | 주문 JSON 직접 추가 API |
| `/save_order_from_json` | `save_order_from_json` | 주문 JSON 저장 API |
| `/saveOrder` | `saveOrder` | 주문 저장 API (Proxy) |
| `/parse_and_save_order` | `parse_and_save_order` | 자연어 주문 파싱 후 저장 API |
| `/find_order` | `find_order_route` | 주문 조회 API |
| `/register_order` | `register_order_route` | 주문 등록 API |
| `/update_order` | `update_order_route` | 주문 수정 API |
| `/delete_order` | `delete_order_route` | 주문 삭제 API |
| `/delete_order_confirm` | `delete_order_confirm` | 주문 삭제 확정 API |
| `/delete_order_request` | `delete_order_request` | 주문 삭제 요청/확정 API |
| `/add_counseling` | `add_counseling_route` | 상담/개인/활동 일지 저장 API |
| `/search_memo` | `search_memo` | 메모 검색 API |
| `/search_memo_from_text` | `search_memo_from_text` | 자연어 메모 검색 API |
| `/find_memo` | `find_memo_route` | 일지 조회 API |
| `/save_memo` | `save_memo_route` | 일지 저장 API |
| `/register_commission` | `register_commission_route` | 후원수당 등록 API |
| `/find_commission` | `find_commission_route` | 후원수당 등록 API |
| `/update_commission` | `update_commission_route` | 후원수당 수정 API |
| `/delete_commission` | `delete_commission_route` | 후원수당 삭제 API |

## 📄 상세 Docstring
### `/` → `home`
```text
홈(Health Check) API
📌 설명:
서버가 정상 실행 중인지 확인하기 위한 기본 엔드포인트입니다.
```

### `/debug_sheets` → `debug_sheets`
```text
시트 디버그 API
📌 설명:
연결된 Google Sheet의 워크시트 목록을 반환합니다.
📥 입력(JSON 예시):
{}
```

### `/find_member` → `find_member_route`
```text
회원 조회 API
📌 설명:
회원명 또는 회원번호를 기준으로 DB 시트에서 정보를 조회합니다.
📥 입력(JSON 예시):
{
"회원명": "신금자"
}
```

### `/members/search-nl` → `search_by_natural_language`
```text
회원 자연어 검색 API
📌 설명:
자연어 문장에서 (필드, 키워드)를 추출하여 DB 시트에서 회원을 검색합니다.
📥 입력(JSON 예시):
{
"query": "계보도 장천수 우측"
}
```

### `/update_member` → `update_member_route`
```text
회원 수정 API
📌 설명:
자연어 요청문에서 {필드: 값} 쌍을 추출하여 회원 정보를 수정합니다.
📥 입력(JSON 예시):
{
"요청문": "홍길동 주소 부산 해운대구로 변경"
}
```

### `/save_member` → `save_member`
```text
회원 저장/수정 API
📌 설명:
자연어 요청문을 파싱하여 회원을 신규 등록하거나, 기존 회원 정보를 수정합니다.
📥 입력(JSON 예시):
{
"요청문": "홍길동 회원번호 12345 휴대폰 010-1111-2222 주소 서울"
}
```

### `/register_member` → `register_member_route`
```text
회원 등록 API
📌 설명:
회원명, 회원번호, 휴대폰번호를 JSON으로 입력받아 신규 등록합니다.
📥 입력(JSON 예시):
{
"회원명": "홍길동",
"회원번호": "12345",
"휴대폰번호": "010-1111-2222"
}
```

### `/delete_member` → `delete_member_route`
```text
회원 삭제 API
📌 설명:
회원명을 기준으로 해당 회원의 전체 정보를 삭제합니다.
📥 입력(JSON 예시):
{
"회원명": "이판주"
}
```

### `/delete_member_field_nl` → `delete_member_field_nl`
```text
회원 필드 삭제 API
📌 설명:
자연어 문장에서 특정 필드를 추출하여 해당 회원의 필드를 비웁니다.
📥 입력(JSON 예시):
{
"요청문": "이판여 휴대폰번호 삭제"
}
```

### `/upload_order` → `upload_order_auto`
```text
제품 주문 업로드 자동 분기 API
📌 설명:
User-Agent를 기반으로 PC/iPad 업로드 방식을 자동으로 분기 처리합니다.
📥 입력(JSON 예시):
(form-data, PC/iPad 동일)
```

### `/upload_order_ipad` → `upload_order_ipad`
```text
제품 주문 업로드 API (iPad)
📌 설명:
iPad에서 캡처한 주문 이미지를 업로드하여 제품 주문 시트에 저장합니다.
📥 입력(form-data 예시):
회원명=홍길동
message=홍길동 제품주문 저장
image=@order.jpg
```

### `/upload_order_pc` → `upload_order_pc`
```text
제품 주문 업로드 API (PC)
📌 설명:
PC에서 업로드된 주문 이미지를 분석하여 제품 주문 시트에 저장합니다.
📥 입력(form-data 예시):
회원명=홍길동
message=홍길동 제품주문 저장
image=@order.jpg
```

### `/upload_order_text` → `upload_order_text`
```text
자연어 기반 주문 저장 API
📌 설명:
자연어 문장에서 회원명, 제품명, 수량, 결제방법, 배송지를 추출하여 주문을 저장합니다.
📥 입력(JSON 예시):
{
"message": "김지연 노니 2개 카드 주문 저장"
}
```

### `/add_orders` → `add_orders`
```text
주문 JSON 직접 추가 API
📌 설명:
분석된 주문 JSON을 그대로 제품주문 시트에 추가합니다.
📥 입력(JSON 예시):
{
"회원명": "홍길동",
"orders": [
    { "제품명": "홍삼", "제품가격": "50000", "PV": "10", "배송처": "서울" }
]
}
```

### `/save_order_from_json` → `save_order_from_json`
```text
주문 JSON 저장 API
📌 설명:
외부에서 전달된 JSON 리스트를 그대로 제품주문 시트에 저장합니다.
📥 입력(JSON 예시):
[
{ "제품명": "홍삼", "제품가격": "50000", "PV": "10", "배송처": "서울" }
]
```

### `/saveOrder` → `saveOrder`
```text
주문 저장 API (Proxy)
📌 설명:
외부 API(MEMBERSLIST_API_URL)로 주문 데이터를 프록시 전송합니다.
📥 입력(JSON 예시):
{
"회원명": "홍길동",
"orders": [
    { "제품명": "홍삼", "제품가격": "50000", "PV": "10" }
]
}
```

### `/parse_and_save_order` → `parse_and_save_order`
```text
자연어 주문 파싱 후 저장 API
📌 설명:
자연어 문장을 파싱하여 주문 정보를 추출하고, 제품주문 시트에 저장합니다.
📥 입력(JSON 예시):
{
"text": "김지연 노니 2개 카드 주문 저장"
}
```

### `/find_order` → `find_order_route`
```text
주문 조회 API
📌 설명:
회원명과 제품명을 기준으로 주문 내역을 조회합니다.
📥 입력(JSON 예시):
{
"회원명": "김상민",
"제품명": "헤모힘"
}
```

### `/register_order` → `register_order_route`
```text
주문 등록 API
📌 설명:
회원명, 제품명, 가격, PV, 배송지 등 명시적 JSON 입력을 받아 주문을 등록합니다.
📥 입력(JSON 예시):
{
"회원명": "홍길동",
"제품명": "홍삼",
"제품가격": "50000",
"PV": "10",
"배송처": "서울"
}
```

### `/update_order` → `update_order_route`
```text
주문 수정 API
📌 설명:
회원명과 제품명을 기준으로 주문 항목을 찾아 수정합니다.
📥 입력(JSON 예시):
{
"회원명": "홍길동",
"제품명": "홍삼",
"수정목록": { "제품가격": "60000" }
}
```

### `/delete_order` → `delete_order_route`
```text
주문 삭제 API
📌 설명:
회원명과 제품명을 기준으로 주문을 삭제합니다.
📥 입력(JSON 예시):
{
"회원명": "홍길동",
"제품명": "홍삼"
}
```

### `/delete_order_confirm` → `delete_order_confirm`
```text
주문 삭제 확정 API
📌 설명:
삭제 요청 단계에서 선택한 주문 번호를 확정하여 실제 행 삭제를 수행합니다.
📥 입력(JSON 예시):
{
"삭제번호": "1,2"
}
```

### `/delete_order_request` → `delete_order_request`
```text
주문 삭제 요청/확정 API
📌 설명:
- `/delete_order_request`: 최근 주문 목록을 보여주고 삭제할 번호를 요청
- `/delete_order_confirm`: 사용자가 선택한 번호의 주문을 실제 삭제
📥 입력(JSON 예시 - 요청):
{}
📥 입력(JSON 예시 - 확정):
{ "삭제번호": "1,2" }
```

### `/add_counseling` → `add_counseling_route`
```text
상담/개인/활동 일지 저장 API
📌 설명:
자연어 요청문을 파싱하여 상담일지/개인일지/활동일지 시트에 저장합니다.
📥 입력(JSON 예시):
{
"요청문": "김기범 상담일지 저장 헤모힘 24박스를 택배 발송함."
}
```

### `/search_memo` → `search_memo`
```text
메모 검색 API
📌 설명:
키워드 및 검색 조건을 기반으로 상담/개인/활동 일지에서 검색합니다.
📥 입력(JSON 예시):
{
"keywords": ["중국", "공항"],
"mode": "전체",
"search_mode": "동시검색",
"limit": 10
}
```

### `/search_memo_from_text` → `search_memo_from_text`
```text
자연어 메모 검색 API
📌 설명:
자연어 문장에서 키워드를 추출하여 상담/개인/활동 일지를 검색합니다.
📥 입력(JSON 예시):
{
"text": "이태수 개인일지 검색 자동차"
}
```

### `/find_memo` → `find_memo_route`
```text
일지 조회 API
📌 설명:
회원명과 일지 종류(개인/상담/활동)를 기준으로 일지 내용을 조회합니다.
📥 입력(JSON 예시):
{
"일지종류": "개인일지",
"회원명": "홍길동"
}
```

### `/save_memo` → `save_memo_route`
```text
일지 저장 API
📌 설명:
회원명과 일지 종류, 내용을 입력받아 해당 시트에 저장합니다.
📥 입력(JSON 예시):
{
"일지종류": "상담일지",
"회원명": "홍길동",
"내용": "오늘은 제품설명회를 진행했습니다."
}
```

### `/register_commission` → `register_commission_route`
```text
후원수당 등록 API
📌 설명:
회원명을 기준으로 후원수당 데이터를 시트에 등록합니다.
```

### `/find_commission` → `find_commission_route`
```text
후원수당 등록 API
📌 설명:
회원명을 기준으로 후원수당 데이터를 시트에 등록합니다.
```

### `/update_commission` → `update_commission_route`
```text
후원수당 수정 API
```

### `/delete_commission` → `delete_commission_route`
```text
후원수당 삭제 API
```
