import re
import traceback
from datetime import datetime

# ===== flask =====
from flask import g

# ===== utils =====
from utils import (
    clean_content,   # 불필요한 조사/특수문자 제거
    now_kst,         # KST 기준 현재 시각
)
from utils.utils_memo import (
    format_memo_results,  # 검색 결과 포맷팅
    handle_search_memo,   # 메모 검색 실행기
)

# ===== service =====
from service.service_memo import (
    save_memo,           # 메모 저장
    search_memo_core,    # 메모 검색 핵심 로직
)






def memo_save_auto_func():
    data = g.query.get("query") or {}
    if "요청문" in data or "text" in data:
        return add_counseling_func()
    if "일지종류" in data and "회원명" in data:
        return save_memo_func()

    return {
        "status": "error",
        "message": "❌ 입력이 올바르지 않습니다. 자연어는 '요청문/text', JSON은 '일지종류/회원명/내용'을 포함해야 합니다.",
        "http_status": 400
    }



def save_memo_func():
    try:
        data = g.query.get("query") or {}
        sheet_name = data.get("일지종류", "").strip()
        member = data.get("회원명", "").strip()
        content = data.get("내용", "").strip()

        if not sheet_name or not member or not content:
            return {"status": "error", "message": "일지종류, 회원명, 내용은 필수 입력 항목입니다.", "http_status": 400}

        ok = save_memo(sheet_name, member, content)
        if ok:
            return {"status": "success", "message": f"{member}님의 {sheet_name} 저장 완료", "http_status": 201}
        return {"status": "error", "message": "시트 저장에 실패했습니다.", "http_status": 500}

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}



def add_counseling_func():
    try:
        data = g.query.get("query") or {}
        text = data.get("요청문", "").strip()

        match = re.search(r"([가-힣]{2,10})\s*(상담일지|개인일지|활동일지)\s*저장", text)
        if not match:
            return {"status": "error", "message": "❌ 회원명 또는 일지종류를 인식할 수 없습니다.", "http_status": 400}

        member_name = match.group(1).strip()
        sheet_type = match.group(2)

        pattern = rf"{re.escape(member_name)}\s*{sheet_type}\s*저장\.?"
        raw_content = re.sub(pattern, "", text).strip()
        content = clean_content(raw_content, member_name=member_name)

        if not content:
            return {"status": "error", "message": "❌ 저장할 내용이 비어 있습니다.", "http_status": 400}

        ok = save_memo(sheet_type, member_name, content)
        if ok:
            now_str = now_kst().strftime("%Y-%m-%d %H:%M")
            preview = content if len(content) <= 50 else content[:50] + "…"
            return {
                "status": "success",
                "message": f"✅ {member_name}님의 {sheet_type}가 저장되었습니다.\n날짜: {now_str}\n내용: {preview}",
                "http_status": 201
            }

        return {"status": "error", "message": "❌ 시트 저장에 실패했습니다.", "http_status": 500}

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": f"[서버 오류] {str(e)}", "http_status": 500}



def memo_find_auto_func():
    try:
        text = (g.query.get("raw_text") or "").strip()

        if len(text) <= 10:
            return {"status": "success", "action": "find_memo", "http_status": 200}
        if any(k in text for k in ["저장", "작성", "기록"]):
            return {"status": "success", "action": "save_memo", "http_status": 200}
        if any(k in text for k in ["조회", "검색", "찾아"]):
            return {"status": "success", "action": "find_memo", "http_status": 200}

        return {"status": "error", "message": "❌ 메모 요청 해석 불가", "http_status": 400}
    except Exception as e:
        return {"status": "error", "message": str(e), "http_status": 500}




def search_memo_func():
    try:
        data = g.query.get("query") or {}
        results = handle_search_memo(data) or []
        formatted_report = format_memo_results(results)
        return {"status": "success", "input": data, "results": results, "report": formatted_report, "http_status": 200}
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": f"❌ 메모 검색 중 오류: {str(e)}", "http_status": 500}




def search_memo_from_text_func():
    try:
        data = g.query.get("query") or {}
        text = (data.get("text") or "").strip()

        if not text:
            return {"status": "error", "message": "text가 비어 있습니다.", "http_status": 400}
        if "검색" not in text:
            return {"status": "error", "message": "'검색' 키워드가 반드시 포함되어야 합니다.", "http_status": 400}

        # ✅ 내부 함수 실행
        result, formatted_text = search_memo_from_text_internal(text)

        if result.get("status") == "success":
            return {**result, "http_status": 200}
        else:
            return {**result, "http_status": 400}

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}






























def search_memo_from_text_internal(text: str, detail: bool = False, offset: int = 0, limit: int = 50):
    """
    자연어 기반 메모 검색 내부 로직
    📌 설명:
    - 사람이 입력한 "검색" 문장을 파싱하여 해당 조건에 맞는 메모를 검색
    - detail=True → JSON 상세 결과 반환
    - detail=False → 사람이 읽기 좋은 텍스트 블록 반환
    """

    if not text or "검색" not in text:
        return {
            "status": "error",
            "message": "❌ 검색 문장이 올바르지 않습니다. (예: '홍길동 상담일지 검색')"
        }, ""

    # ✅ 시트 모드 판별
    if "개인" in text:
        sheet_names = ["개인일지"]
    elif "상담" in text:
        sheet_names = ["상담일지"]
    elif "활동" in text:
        sheet_names = ["활동일지"]
    else:
        sheet_names = ["상담일지", "개인일지", "활동일지"]

    # ✅ 검색 모드 판별
    search_mode = "동시검색" if ("동시" in text or "동시검색" in text) else "any"

    # ✅ 불필요한 단어 제거
    ignore = {
        "검색", "해주세요", "내용", "다음", "에서", "메모",
        "동시", "동시검색", "전체메모", "개인일지", "상담일지", "활동일지"
    }
    tokens = [t for t in text.split() if t not in ignore]

    # ✅ 회원명 추출
    member_name = None
    for i in range(len(tokens) - 2):
        if (
            re.match(r"^[가-힣]{2,10}$", tokens[i]) and
            tokens[i+1] in {"개인일지", "상담일지", "활동일지"} and
            "검색" in tokens[i+2]
        ):
            member_name = tokens[i]
            break

    # ✅ 검색 키워드 추출 + clean_content 적용
    content_tokens = [t for t in tokens if t != member_name]
    raw_content = " ".join(content_tokens).strip()
    search_content = clean_content(raw_content, member_name)

    if not search_content:
        return {"status": "error", "message": "검색할 내용이 없습니다."}, ""

    keywords = search_content.split()

    # ✅ 전체 시트 검색
    all_results = []
    for sheet_name in sheet_names:
        partial = search_memo_core(
            sheet_name=sheet_name,
            keywords=keywords,
            search_mode=search_mode,
            member_name=member_name,
            limit=9999
        )
        for p in partial:
            p["일지종류"] = sheet_name
        all_results.extend(partial)

    # ✅ 최신순 정렬
    try:
        all_results.sort(
            key=lambda x: datetime.strptime(
                str(x.get("날짜", "1900-01-01")).split()[0], "%Y-%m-%d"
            ),
            reverse=True
        )
    except Exception:
        pass

    # ✅ 일지별 그룹핑 (출력 순서 고정)
    grouped = {"활동일지": [], "상담일지": [], "개인일지": []}
    for item in all_results:
        if item["일지종류"] in grouped:
            grouped[item["일지종류"]].append(item)

    # ✅ 페이지네이션 적용
    for key in grouped:
        grouped[key] = grouped[key][offset:offset + limit]

    # ✅ 텍스트 블록 변환
    icons = {"활동일지": "🗂", "상담일지": "📂", "개인일지": "📒"}
    text_blocks = []
    for sheet_name in ["활동일지", "상담일지", "개인일지"]:
        entries = grouped.get(sheet_name, [])
        if entries:
            block = [f"{icons[sheet_name]} {sheet_name}"]
            for e in entries:
                line = f"· ({e.get('작성일자')}) {e.get('내용')} — {e.get('회원명')}"
                block.append(line)
            text_blocks.append("\n".join(block))
    response_text = "\n\n".join(text_blocks)

    if detail:
        return {
            "status": "success",
            "sheets": sheet_names,
            "member_name": member_name,
            "search_mode": search_mode,
            "keywords": keywords,
            "results": grouped,
            "has_more": any(len(v) > limit for v in grouped.values())
        }, response_text
    else:
        return {
            "status": "success",
            "keywords": keywords,
            "formatted_text": response_text,
            "has_more": any(len(v) > limit for v in grouped.values())
        }, response_text