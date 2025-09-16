import pytest
from datetime import datetime
from service import save_memo, find_memo, search_in_sheet, search_memo_core
from utils import now_kst

def test_memo_lifecycle():
    member = "테스트회원"
    content = "pytest 메모 저장 테스트"

    # 1. 저장
    save_memo("상담일지", member, content)

    # 2. 검색
    results = find_memo("pytest", "상담일지")
    assert any(content in r.get("내용", "") for r in results)

    # 3. 고급 검색 (search_in_sheet)
    today = now_kst().strftime("%Y-%m-%d")
    start_date = datetime.strptime(today, "%Y-%m-%d")
    end_date = datetime.strptime(today, "%Y-%m-%d")

    advanced_results, has_more = search_in_sheet(
        "상담일지",
        keywords=["pytest"],
        start_date=start_date,
        end_date=end_date
    )
    assert any(r["내용"] == content for r in advanced_results)

    # 4. 통합 검색 (search_memo_core)
    core_results = search_memo_core(
        "상담일지",
        keywords=["pytest"],
        member_name=member
    )
    assert any(r["내용"] == content for r in core_results)
