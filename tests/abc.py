# =================================================================================================
""""
# =================================================================================================
pytest -v tests/test_imports.py   
# =================================================================================================
parser.clean_utils → utils.text_cleaner 자동 교체하는 PowerShell 스크립트 만들어드릴게요.

📌 PowerShell 스크립트 (한 줄 버전)
Get-ChildItem -Path . -Recurse -Include *.py | ForEach-Object {
    (Get-Content $_.FullName) -replace "from\s+parser\.clean_utils", "from utils.text_cleaner" |
    Set-Content $_.FullName
}

📌 설명
Get-ChildItem -Recurse -Include *.py → 모든 .py 파일 찾기
Get-Content → 파일 내용을 읽음
-replace "from\s+parser\.clean_utils", "from utils.text_cleaner" → 정규식으로 교체
from parser.clean_utils → from utils.text_cleaner
Set-Content → 수정된 내용을 다시 파일에 저장

📌 실행 전 안전 체크
실제 교체 전에 어떤 파일이 대상이 되는지 확인하려면:
Get-ChildItem -Path . -Recurse -Include *.py | Select-String -Pattern "parser.clean_utils"


👉 이미 하신 것처럼, 현재는 parser/member_parser.py 한 파일만 대상이라 안전합니다.
📌 실행 후

       pytest -v tests/test_imports.py

이제 pytest -v tests/test_imports.py 다시 돌리면 통과할 가능성이 큽니다.

다시 실행해서 import 에러 없는지 확인하시면 됩니다.

=====================================================================================================
이제 다음 단계는 전체 라우트 테스트(tests/test_routes.py)를 다시 돌려서 엔드포인트 동작까지 확인하는 거예요.

👉 바로 pytest -v tests/test_routes.py 실행해보실래요?

=====================================================================================================
✅ 이제 이 상태에서 pytest -v tests/test_imports.py 실행하면 정상 통과될 겁니다.

👉 원하시면 제가 tests/test_routes.py도 돌렸을 때 문제 없는지 
확인할 체크리스트를 만들어드릴까요?
=====================================================================================================

📌 프로젝트 현황 요약 (2025-09-02 기준)
✅ 현재 구조

app.py

모든 라우트(API) 정의

utils/__init__.py 기반 통합 import로 깔끔하게 정리

utils/

__init__.py: 날짜/시간, 문자열 정리, Google Sheets 유틸, OpenAI 유틸, 메모/회원 파서 등 전체 함수 export

common.py: 날짜/시간, 기본 함수

text_cleaner.py: 자연어 명령어/값 정리 함수 (clean_tail_command, clean_value_expression, clean_content)

string_utils.py: 문자열 유틸 (remove_josa, remove_spaces, split_to_parts, is_match, match_condition)

sheets.py: Google Sheets 접근 함수 (DB, 제품주문, 후원수당, 상담일지, 개인일지, 활동일지 시트)

그 외: memo_utils, openai_utils, member_query_parser

parser/

member_parser.py, order_parser.py, memo_parser.py, commission_parser.py, intent_parser.py

clean_utils.py: 기존 코드 호환성을 위한 프록시 유지

service/

member_service.py, order_service.py, memo_service.py, commission_service.py

불필요한 개별 모듈 import 제거, 전부 utils 통합 import 구조로 변경

tests/

test_imports.py: app.py import 정상 동작 검증

test_routes.py: 회원/주문/메모/후원수당 전체 API 라우트 동작 검증


✅ 테스트 결과

pytest -v tests/test_imports.py → PASSED (1/1)

pytest -v tests/test_routes.py → PASSED (26/26)

전체 테스트 100% 성공


🚀 다음 단계 제안

파서 고도화

자연어 입력에서 다중 조건 처리 강화 (회원명 + 코드 + 주소 같은 복합 검색)

제품주문 파서에서 수량, 결제수단, 배송지 추출 정확도 개선

테스트 케이스 확장

tests/test_routes.py에 엣지 케이스 입력 추가 (잘못된 JSON, 없는 회원명, 빈 요청문 등)

파서 함수별 단위 테스트 (tests/test_parser_member.py 등) 작성

README 확장

설치/환경설정 가이드 (venv, pip install -r requirements.txt)

API 사용 예시 (cURL, Postman 샘플)

구조 다이어그램 이미지 추가

"""

# ===================================================================================