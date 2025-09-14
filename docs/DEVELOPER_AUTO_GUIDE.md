# 📑 API Route 자동 문서 (docstring 기반)

이 문서는 `app.py`에서 자동 추출한 라우트 목록 + docstring 설명을 포함합니다.

| 경로(Path) | 함수명(Function) | 설명 (docstring) |
|------------|-----------------|------------------|
| `/openapi.json` | `openapi` | OpenAPI 스펙(JSON) 반환 |
| `/.well-known/ai-plugin.json` | `serve_ai_plugin` | ChatGPT 플러그인 manifest 파일 반환 |
| `/logo.png` | `plugin_logo` | 플러그인 로고 이미지 반환 |
| `/` | `home` | 홈(Health Check) API |
| `/debug_sheets` | `debug_sheets` | 현재 연결된 구글 시트 목록과 특정 시트의 헤더 확인 |
| `/postIntent` | `post_intent` | ⚠️ 설명 없음 |
| `/guess_intent` | `guess_intent_entry` | ⚠️ 설명 없음 |
| `/member` | `member_route` | 회원 관련 API (intent 기반 단일 라우트) |
| `/memo` | `memo_route` | 메모 관련 API (저장/검색 자동 분기) |
| `/order` | `order_route` | 주문 관련 API (intent 기반 단일 엔드포인트) |
| `/commission` | `commission_route` | 후원수당 관련 API (intent 기반 단일 엔드포인트) |

## 📄 상세 Docstring
### `/openapi.json` → `openapi`
```text
OpenAPI 스펙(JSON) 반환
```

### `/.well-known/ai-plugin.json` → `serve_ai_plugin`
```text
ChatGPT 플러그인 manifest 파일 반환
```

### `/logo.png` → `plugin_logo`
```text
플러그인 로고 이미지 반환
```

### `/` → `home`
```text
홈(Health Check) API
📌 설명:
서버가 정상 실행 중인지 확인하기 위한 기본 엔드포인트입니다.
```

### `/debug_sheets` → `debug_sheets`
```text
현재 연결된 구글 시트 목록과 특정 시트의 헤더 확인
```

### `/postIntent` → `post_intent`
_⚠️ docstring 없음_

### `/guess_intent` → `guess_intent_entry`
_⚠️ docstring 없음_

### `/member` → `member_route`
```text
회원 관련 API (intent 기반 단일 라우트)
- g.query["intent"] 가 있으면 그대로 실행
- 없으면 자연어 입력 분석해서 search_member / select_member 자동 분기
```

### `/memo` → `memo_route`
```text
메모 관련 API (저장/검색 자동 분기)
- 자연어 입력은 무조건 post_intent() 우회
- JSON 입력은 구조 분석 → 저장 / 검색 분기
```

### `/order` → `order_route`
```text
주문 관련 API (intent 기반 단일 엔드포인트)
- before_request 에서 g.query["intent"] 세팅됨
- 자연어 입력이면 postIntent로 우회
- 파일 업로드면 order_upload 바로 처리
```

### `/commission` → `commission_route`
```text
후원수당 관련 API (intent 기반 단일 엔드포인트)
- before_request 에서 g.query 세팅됨
- 자연어 입력이면 postIntent로 우회
```
