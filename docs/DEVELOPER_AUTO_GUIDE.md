# 📑 API Route 자동 문서 (docstring 기반)

이 문서는 프로젝트 전체 `.py` 파일에서 추출한 Flask 라우트와 docstring을 정리한 것입니다.

| 파일(File) | 경로(Path) | 함수명(Function) | 설명 (docstring) |
|------------|------------|-----------------|------------------|
| `app.py` | `/` | `home` | 홈(Health Check) API |
| `app.py` | `/debug_sheets` | `debug_sheets` | ⚠️ 설명 없음 |
| `app.py` | `/guess_intent` | `guess_intent_entry` | 자연어 입력의 진입점 |
| `app.py` | `/member_find_auto` | `member_find_auto` | 회원 조회 자동 분기 API |
| `app.py` | `/find_member` | `find_member` | 회원 조회 API (JSON 전용) |
| `app.py` | `/members/search-nl` | `search_by_natural_language` | 회원 자연어 검색 API (자연어 전용) |
| `app.py` | `/searchMemberByNaturalText` | `search_member_by_natural_text` | ⚠️ 설명 없음 |
| `app.py` | `/update_member` | `update_member_route` | 회원 수정 API |
| `app.py` | `/save_member` | `save_member` | 회원 저장/수정 API |
| `app.py` | `/register_member` | `register_member_route` | 회원 등록 API |
| `app.py` | `/delete_member` | `delete_member_route` | 회원 삭제 API |
| `app.py` | `/delete_member_field_nl` | `delete_member_field_nl` | 회원 필드 삭제 API |
| `app.py` | `/order/auto` | `order_auto` | 제품 주문 자동 분기 API |
| `app.py` | `/order/upload` | `order_upload` | 제품 주문 업로드 API (PC/iPad 자동 분기) |
| `app.py` | `/upload_order` | `compat_upload_order` | 옛 API 호환용 → /order/upload로 리다이렉트 |
| `app.py` | `/upload_order_pc` | `compat_upload_order_pc` | 옛 API 호환용 → /order/upload로 리다이렉트 |
| `app.py` | `/upload_order_ipad` | `compat_upload_order_ipad` | 옛 API 호환용 → /order/upload로 리다이렉트 |
| `app.py` | `/order/nl` | `order_nl` | 자연어 및 JSON 기반 주문 처리 API |
| `app.py` | `/upload_order_text` | `compat_upload_order_text` | 옛 API 호환용 → /order/nl |
| `app.py` | `/parse_and_save_order` | `compat_parse_and_save_order` | 옛 API 호환용 → /order/nl |
| `app.py` | `/find_order` | `compat_find_order` | 옛 API 호환용 → /order/nl |
| `app.py` | `/orders/search-nl` | `compat_orders_search_nl` | 옛 API 호환용 → /order/nl |
| `app.py` | `/order_find_auto` | `compat_order_find_auto` | 옛 API 호환용 → /order/nl |
| `app.py` | `/register_order` | `compat_register_order` | 옛 API 호환용 → /order/nl |
| `app.py` | `/update_order` | `compat_update_order` | 옛 API 호환용 → /order/nl |
| `app.py` | `/delete_order` | `compat_delete_order` | 옛 API 호환용 → /order/nl |
| `app.py` | `/delete_order_confirm` | `compat_delete_order_confirm` | 옛 API 호환용 → /order/nl |
| `app.py` | `/delete_order_request` | `compat_delete_order_request` | 옛 API 호환용 → /order/nl |
| `app.py` | `/saveOrder` | `save_order_proxy` | 외부 API 프록시 (호환용 메인 엔드포인트) |
| `app.py` | `/save_Order` | `compat_save_order` | 옛 API 호환용 → /saveOrder |
| `app.py` | `/memo_save_auto` | `memo_save_auto` | 메모 저장 자동 분기 API |
| `app.py` | `/save_memo` | `save_memo_route` | 일지 저장 API (JSON 전용) |
| `app.py` | `/add_counseling` | `add_counseling_route` | 상담/개인/활동 일지 저장 API (자연어 전용) |
| `app.py` | `/memo_find_auto` | `memo_find_auto` | 메모 검색 자동 분기 API |
| `app.py` | `/search_memo` | `search_memo_route` | 메모 검색 API (자연어 + JSON 파라미터 지원) |
| `app.py` | `/search_memo_from_text` | `search_memo_from_text` | 자연어 메모 검색 API |
| `app.py` | `/register_commission` | `register_commission_route` | 후원수당 등록 API |
| `app.py` | `/update_commission` | `update_commission_route` | 후원수당 수정 API |
| `app.py` | `/delete_commission` | `delete_commission_route` | 후원수당 삭제 API |
| `app.py` | `/order_find_auto` | `order_find_auto` | 주문 조회 자동 분기 API |
| `app.py` | `/find_order` | `find_order_route` | 주문 조회 API (JSON 전용) |
| `app.py` | `/orders/search-nl` | `search_order_by_nl` | 주문 자연어 검색 API (자연어 전용) |
| `app.py` | `/commission_find_auto` | `commission_find_auto` | 후원수당 조회 자동 분기 API |
| `app.py` | `/find_commission` | `find_commission_route` | 후원수당 조회 API (JSON 전용) |
| `app.py` | `/commission/search-nl` | `search_commission_by_nl` | 후원수당 자연어 검색 API (자연어 전용) |
| `app.py` | `/debug_routes` | `debug_routes` | ⚠️ 설명 없음 |
| `app.py` | `/debug_routes_table` | `debug_routes_table` | ⚠️ 설명 없음 |
| `venv310\Lib\site-packages\flask\ctx.py` | `/` | `index` | ⚠️ 설명 없음 |
| `venv310\Lib\site-packages\flask\ctx.py` | `/` | `index` | ⚠️ 설명 없음 |
| `venv310\Lib\site-packages\flask\helpers.py` | `/stream` | `streamed_response` | ⚠️ 설명 없음 |
| `venv310\Lib\site-packages\flask\helpers.py` | `/stream` | `streamed_response` | ⚠️ 설명 없음 |
| `venv310\Lib\site-packages\flask\helpers.py` | `/uploads/<path:name>` | `download_file` | ⚠️ 설명 없음 |
| `venv310\Lib\site-packages\flask\scaffold.py` | `/` | `index` | ⚠️ 설명 없음 |
| `venv310\Lib\site-packages\flask\scaffold.py` | `/` | `index` | ⚠️ 설명 없음 |
| `venv310\Lib\site-packages\oauth2client\contrib\flask_util.py` | `/needs_credentials` | `optional` | ⚠️ 설명 없음 |
| `venv310\Lib\site-packages\oauth2client\contrib\flask_util.py` | `/info` | `login` | ⚠️ 설명 없음 |
| `venv310\Lib\site-packages\oauth2client\contrib\flask_util.py` | `/drive` | `requires_drive` | ⚠️ 설명 없음 |
| `venv310\Lib\site-packages\oauth2client\contrib\flask_util.py` | `/calendar` | `requires_calendar` | ⚠️ 설명 없음 |

## 📄 상세 Docstring
### `/` → `home` (app.py)
```text
홈(Health Check) API
📌 설명:
서버가 정상 실행 중인지 확인하기 위한 기본 엔드포인트입니다.
```

### `/debug_sheets` → `debug_sheets` (app.py)
_⚠️ docstring 없음_

### `/guess_intent` → `guess_intent_entry` (app.py)
```text
자연어 입력의 진입점
- intent를 판별하고 해당 자동 분기 API로 redirect
```

### `/member_find_auto` → `member_find_auto` (app.py)
```text
회원 조회 자동 분기 API
📌 설명:
- 자연어 기반 요청(text, query 포함) → search_by_natural_language
- JSON 기반 요청(회원명, 회원번호 포함) → find_member_route
```

### `/find_member` → `find_member` (app.py)
```text
회원 조회 API (JSON 전용)
📌 설명:
회원명 또는 회원번호를 기준으로 DB 시트에서 정보를 조회합니다.
📥 입력(JSON 예시):
{
  "회원명": "신금자"
}
```

### `/members/search-nl` → `search_by_natural_language` (app.py)
```text
회원 자연어 검색 API (자연어 전용)
📌 설명:
- 자연어 문장에서 (필드, 키워드) 조건들을 추출하여 DB 시트에서 회원 검색
- 조건 여러 개 입력 시 AND 검색
- 기본은 텍스트 리스트 출력 (회원명, 회원번호, 휴대폰번호, 특수번호, 코드만 표시)
- {"detail": true} 옵션 → JSON 상세 응답
- 기본 20건(limit), offset으로 페이지네이션
```

### `/searchMemberByNaturalText` → `search_member_by_natural_text` (app.py)
_⚠️ docstring 없음_

### `/update_member` → `update_member_route` (app.py)
```text
회원 수정 API
📌 설명:
자연어 요청문에서 {필드: 값} 쌍을 추출하여 회원 정보를 수정합니다.
📥 입력(JSON 예시):
{
"요청문": "홍길동 주소 부산 해운대구로 변경"
}
```

### `/save_member` → `save_member` (app.py)
```text
회원 저장/수정 API
📌 설명:
자연어 요청문을 파싱하여 회원을 신규 등록하거나, 기존 회원 정보를 수정합니다.
📥 입력(JSON 예시):
{
"요청문": "홍길동 회원번호 12345 휴대폰 010-1111-2222 주소 서울"
}
```

### `/register_member` → `register_member_route` (app.py)
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

### `/delete_member` → `delete_member_route` (app.py)
```text
회원 삭제 API
📌 설명:
회원명을 기준으로 해당 회원의 전체 정보를 삭제합니다.
📥 입력(JSON 예시):
{
"회원명": "이판주"
}
```

### `/delete_member_field_nl` → `delete_member_field_nl` (app.py)
```text
회원 필드 삭제 API
📌 설명:
자연어 문장에서 특정 필드를 추출하여 해당 회원의 필드를 비웁니다.
📥 입력(JSON 예시):
{
"요청문": "이판여 휴대폰번호 삭제"
}
```

### `/order/auto` → `order_auto` (app.py)
```text
제품 주문 자동 분기 API
📌 설명:
- 이미지 업로드 기반 요청(image, image_url, 파일 포함) → order_upload()
- 자연어/JSON 기반 요청(text, query, 회원명, 제품명 등) → order_nl()
```

### `/order/upload` → `order_upload` (app.py)
```text
제품 주문 업로드 API (PC/iPad 자동 분기)
📌 설명:
- User-Agent 기반으로 PC/iPad 자동 분기
- 이미지 파일/URL 업로드 → GPT Vision 분석 → JSON 추출 → 시트 저장
```

### `/upload_order` → `compat_upload_order` (app.py)
```text
옛 API 호환용 → /order/upload로 리다이렉트
```

### `/upload_order_pc` → `compat_upload_order_pc` (app.py)
```text
옛 API 호환용 → /order/upload로 리다이렉트
```

### `/upload_order_ipad` → `compat_upload_order_ipad` (app.py)
```text
옛 API 호환용 → /order/upload로 리다이렉트
```

### `/order/nl` → `order_nl` (app.py)
```text
자연어 및 JSON 기반 주문 처리 API
📌 기능:
- 자연어 문장 → 파싱 → 등록/조회/삭제
- JSON 입력(회원명, 제품명 등) → 등록/수정/삭제/조회
```

### `/upload_order_text` → `compat_upload_order_text` (app.py)
```text
옛 API 호환용 → /order/nl
```

### `/parse_and_save_order` → `compat_parse_and_save_order` (app.py)
```text
옛 API 호환용 → /order/nl
```

### `/find_order` → `compat_find_order` (app.py)
```text
옛 API 호환용 → /order/nl
```

### `/orders/search-nl` → `compat_orders_search_nl` (app.py)
```text
옛 API 호환용 → /order/nl
```

### `/order_find_auto` → `compat_order_find_auto` (app.py)
```text
옛 API 호환용 → /order/nl
```

### `/register_order` → `compat_register_order` (app.py)
```text
옛 API 호환용 → /order/nl
```

### `/update_order` → `compat_update_order` (app.py)
```text
옛 API 호환용 → /order/nl
```

### `/delete_order` → `compat_delete_order` (app.py)
```text
옛 API 호환용 → /order/nl
```

### `/delete_order_confirm` → `compat_delete_order_confirm` (app.py)
```text
옛 API 호환용 → /order/nl
```

### `/delete_order_request` → `compat_delete_order_request` (app.py)
```text
옛 API 호환용 → /order/nl
```

### `/saveOrder` → `save_order_proxy` (app.py)
```text
외부 API 프록시 (호환용 메인 엔드포인트)
📌 기능:
- 입력된 주문 JSON을 MEMBERSLIST_API_URL로 그대로 전달
```

### `/save_Order` → `compat_save_order` (app.py)
```text
옛 API 호환용 → /saveOrder
```

### `/memo_save_auto` → `memo_save_auto` (app.py)
```text
메모 저장 자동 분기 API
📌 설명:
- JSON 입력(일지종류, 회원명, 내용) → save_memo_route
- 자연어 입력(요청문) → add_counseling_route
📥 입력(JSON 예시1 - JSON 전용):
{
  "일지종류": "상담일지",
  "회원명": "홍길동",
  "내용": "오늘은 제품설명회를 진행했습니다."
}
📥 입력(JSON 예시2 - 자연어 전용):
{
  "요청문": "이태수 상담일지 저장 오늘부터 슬림바디 다시 시작"
}
```

### `/save_memo` → `save_memo_route` (app.py)
```text
일지 저장 API (JSON 전용)
📌 설명:
회원명과 일지 종류, 내용을 JSON 입력으로 받아 시트에 저장합니다.
📥 입력(JSON 예시):
{
  "일지종류": "상담일지",
  "회원명": "홍길동",
  "내용": "오늘은 제품설명회를 진행했습니다."
}
```

### `/add_counseling` → `add_counseling_route` (app.py)
```text
상담/개인/활동 일지 저장 API (자연어 전용)
예: {"요청문": "이태수 상담일지 저장 오늘부터 슬림바디 다시 시작"}
```

### `/memo_find_auto` → `memo_find_auto` (app.py)
```text
메모 검색 자동 분기 API
📌 설명:
- 자연어 기반 요청(text, query 포함) → search_memo_from_text
- JSON 기반 요청(sheet, keywords, member_name 등 포함) → search_memo
```

### `/search_memo` → `search_memo_route` (app.py)
```text
메모 검색 API (자연어 + JSON 파라미터 지원)
- text 필드 있으면 자연어 검색
- keywords 필드 있으면 JSON 기반 검색
```

### `/search_memo_from_text` → `search_memo_from_text` (app.py)
```text
자연어 메모 검색 API
📌 설명:
- 항상 사람이 읽기 좋은 블록(text)과 카테고리별 분리 정보(lists)를 함께 반환
- iPad 화면은 text만 그대로 표시하면 되고
- 카테고리별 필터링/탭 기능은 lists를 사용하면 됨
```

### `/register_commission` → `register_commission_route` (app.py)
```text
후원수당 등록 API
📌 설명:
회원명을 기준으로 후원수당 데이터를 시트에 등록합니다.
```

### `/update_commission` → `update_commission_route` (app.py)
```text
후원수당 수정 API
```

### `/delete_commission` → `delete_commission_route` (app.py)
```text
후원수당 삭제 API
```

### `/order_find_auto` → `order_find_auto` (app.py)
```text
주문 조회 자동 분기 API
📌 설명:
- 자연어 기반 요청(query, text) → search_order_by_nl
- JSON 기반 요청(회원명, 제품명) → find_order_route
```

### `/find_order` → `find_order_route` (app.py)
```text
주문 조회 API (JSON 전용)
📌 설명:
회원명과 제품명을 기준으로 주문 내역을 조회합니다.
📥 입력(JSON 예시):
{
  "회원명": "김상민",
  "제품명": "헤모힘"
}
```

### `/orders/search-nl` → `search_order_by_nl` (app.py)
```text
주문 자연어 검색 API (자연어 전용)
📌 설명:
자연어 문장에서 회원명, 제품명 등을 추출하여 주문 내역을 조회합니다.
📥 입력(JSON 예시):
{
  "query": "김상민 헤모힘 주문 조회"
}
```

### `/commission_find_auto` → `commission_find_auto` (app.py)
```text
후원수당 조회 자동 분기 API
📌 설명:
- 자연어 기반 요청(query, text) → search_commission_by_nl
- JSON 기반 요청(회원명) → find_commission_route
```

### `/find_commission` → `find_commission_route` (app.py)
```text
후원수당 조회 API (JSON 전용)
📌 설명:
회원명을 기준으로 후원수당 데이터를 조회합니다.
📥 입력(JSON 예시):
{
  "회원명": "홍길동"
}
```

### `/commission/search-nl` → `search_commission_by_nl` (app.py)
```text
후원수당 자연어 검색 API (자연어 전용)
📌 설명:
자연어 문장에서 회원명을 추출하여 후원수당을 조회합니다.
📥 입력(JSON 예시):
{
  "query": "홍길동 후원수당 조회"
}
```

### `/debug_routes` → `debug_routes` (app.py)
_⚠️ docstring 없음_

### `/debug_routes_table` → `debug_routes_table` (app.py)
_⚠️ docstring 없음_

### `/` → `index` (venv310\Lib\site-packages\flask\ctx.py)
_⚠️ docstring 없음_

### `/` → `index` (venv310\Lib\site-packages\flask\ctx.py)
_⚠️ docstring 없음_

### `/stream` → `streamed_response` (venv310\Lib\site-packages\flask\helpers.py)
_⚠️ docstring 없음_

### `/stream` → `streamed_response` (venv310\Lib\site-packages\flask\helpers.py)
_⚠️ docstring 없음_

### `/uploads/<path:name>` → `download_file` (venv310\Lib\site-packages\flask\helpers.py)
_⚠️ docstring 없음_

### `/` → `index` (venv310\Lib\site-packages\flask\scaffold.py)
_⚠️ docstring 없음_

### `/` → `index` (venv310\Lib\site-packages\flask\scaffold.py)
_⚠️ docstring 없음_

### `/needs_credentials` → `optional` (venv310\Lib\site-packages\oauth2client\contrib\flask_util.py)
_⚠️ docstring 없음_

### `/info` → `login` (venv310\Lib\site-packages\oauth2client\contrib\flask_util.py)
_⚠️ docstring 없음_

### `/drive` → `requires_drive` (venv310\Lib\site-packages\oauth2client\contrib\flask_util.py)
_⚠️ docstring 없음_

### `/calendar` → `requires_calendar` (venv310\Lib\site-packages\oauth2client\contrib\flask_util.py)
_⚠️ docstring 없음_
