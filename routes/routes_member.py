import re
from flask import g, request

# 시트/서비스/파서 의존성들 (하단 함수에서 사용)
from utils.sheets import (
    get_rows_from_sheet,   # DB 시트 행 조회
    get_member_sheet,      # 회원 시트 접근
    safe_update_cell,      # 안전한 셀 수정
)
from service.service_member import (
    register_member_internal,        # 회원 등록
    update_member_internal,          # 회원 수정
    delete_member_internal,          # 회원 삭제
    delete_member_field_nl_internal, # 회원 필드 삭제 (자연어)
)
from parser import parse_registration  # 회원 등록/수정 파서

SHEET_NAME_DB = "DB"  # 매직스트링 방지





# ────────────────────────────────────────────────────────────────────
# 공통 헬퍼
# ────────────────────────────────────────────────────────────────────
def _norm(s):
    return (s or "").strip()




def _digits(s):
    return re.sub(r"\D", "", s or "")



def _compact_row(r: dict) -> dict:
    """회원 정보를 compact dict 형태로 반환 (DB 시트 기준)"""
    return {
        "회원명": r.get("회원명", ""),
        "회원번호": r.get("회원번호", ""),
        "특수번호": r.get("특수번호", ""),
        "코드": r.get("코드", ""),
        "생년월일": r.get("생년월일", ""),
        "계보도": r.get("계보도", ""),
        "근무처": r.get("근무처", ""),
        "주소": r.get("주소", ""),
        "메모": r.get("메모", ""),
    }


def _line(d: dict) -> str:
    """사람이 읽기 좋은 한 줄 요약 (모든 필드 표시)"""
    parts = [
        f"회원번호: {d.get('회원번호','')}",
        f"특수번호: {d.get('특수번호','')}",
        f"코드: {d.get('코드','')}",
        f"생년월일: {d.get('생년월일','')}",
        f"계보도: {d.get('계보도','')}",        
        f"근무처: {d.get('근무처','')}",
        f"주소: {d.get('주소','')}",
        f"메모: {d.get('메모','')}",
    ]
    # 값이 없는 항목은 제외
    parts = [p for p in parts if not p.endswith(": ")]
    return f"{d.get('회원명','')} ({', '.join(parts)})"




# ────────────────────────────────────────────────────────────────────
# 1) 허브: search_member_func  ← nlu_to_pc_input 가 intent='search_member'로 보냄
# ────────────────────────────────────────────────────────────────────
def search_member_func():
    """
    회원 검색 허브 함수 (라우트 아님)
    - g.query["query"] 가 str이면 '코드...' 여부로 분기
    - 그 외는 find_member_logic()로 처리
    - 결과에 http_status 추가(성공:200 / 실패:400)
    """
    try:
        query = g.query.get("query", None)
        if query is None:
            return {"status": "error", "message": "검색어(query)가 필요합니다.", "http_status": 400}

        # 원본 텍스트 저장
        g.query["raw_text"] = query if isinstance(query, str) else str(query)

        # '코드...' 패턴이면 코드 검색으로
        if isinstance(query, str) and (query.startswith("코드") or query.lower().startswith("code")):
            result = search_by_code_logic()
        else:
            result = find_member_logic()

        http_status = 200 if isinstance(result, dict) and result.get("status") == "success" else 400
        return {**result, "http_status": http_status}

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}


# ────────────────────────────────────────────────────────────────────
# 2) 코드 검색: '코드a', '코드 A', 'code:B' 등
# ────────────────────────────────────────────────────────────────────
def search_by_code_logic():
    """
    코드 컬럼 정확 일치 (대소문자 무시)로 검색
    허용 입력: '코드a', '코드 A', '코드:A', 'code b', 'code: c'
    """
    try:
        raw = g.query.get("query") or ""
        text = str(raw).strip()

        print("=== ENTER search_by_code_logic ===")
        print("raw from g.query:", g.query.get("query"))


        # ✅ 한글/영문 '코드' + 선택적 콜론 + 공백 허용
        m = re.match(r"^(?:코드|code)\s*:?\s*([A-Za-z0-9]+)$", text, re.IGNORECASE)
        
        print("=== DEBUG REGEX ===", "text:", text, "m:", m)

        if not m:
            return {
                "status": "error",
                "message": f"올바른 코드 검색어가 아닙니다. 입력값={text}, 예: 코드a, 코드 A, code:B",
                "http_status": 400
            }

        code_value = m.group(1).upper()
        rows = get_rows_from_sheet("DB")

        # ✅ 코드 컬럼 필터링
        matched = [r for r in rows if str(r.get("코드", "")).strip().upper() == code_value]
       
       
        # 🔽 여기서 디버깅 로그 찍기
        print("=== DEBUG search_by_code_logic ===")
        print("raw:", raw)
        print("text:", text)
        print("code_value:", code_value)
        print("rows 첫 3개:", rows[:3])
        print("matched 개수:", len(matched))       
             
       
        matched.sort(key=lambda r: str(r.get("회원명", "")).strip())

        print("=== DEBUG REGEX ===", "text:", text, "m:", m)   # 👈 여기에 추가



        results = [_compact_row(r) for r in matched]
        display = [_line(d) for d in results]

        return {
            "status": "success",
            "intent": "search_by_code",
            "code": code_value,
            "count": len(results),
            "results": results,
            "display": display,
            "raw_text": raw
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}

    
# ────────────────────────────────────────────────────────────────────
# 3) 일반 검색: 이름/회원번호/휴대폰/특수번호/부분매칭
# ────────────────────────────────────────────────────────────────────
def find_member_logic():
    """
    일반 회원 검색
    - g.query["query"] 가 dict 또는 str
      dict 예: {"회원명":"홍길동"} / {"회원번호":"123456"} / {"휴대폰번호":"010-1234-5678"} / {"특수번호":"A1"}
      str  예: "홍길동" / "1234567" / "01012345678" / "특수번호 A1"
    """
    try:
        q = g.query.get("query")
        rows = get_rows_from_sheet("DB")  # list[dict]

        # 1) 검색 키 추출
        f = {"회원명": None, "회원번호": None, "휴대폰번호": None, "특수번호": None}

        if isinstance(q, dict):
            for k in list(f.keys()):
                if k in q: f[k] = _norm(q.get(k))



        elif isinstance(q, str):
            text = _norm(q)

            if text.startswith("코드") or text.lower().startswith("code"):
                g.query["query"] = text
                return search_by_code_logic()




            if re.fullmatch(r"\d{5,8}", text):
                f["회원번호"] = text
            elif re.fullmatch(r"(010-\d{3,4}-\d{4}|010\d{7,8})", text):
                f["휴대폰번호"] = text
            else:
                m = re.search(r"특수번호\s*([a-zA-Z0-9!@#]+)", text)
                if m:
                    f["특수번호"] = m.group(1)
                elif re.fullmatch(r"[가-힣]{2,4}", text):
                    f["회원명"] = text
                else:
                    # 폴백: 회원명 부분 매칭
                    f["회원명"] = text
        else:
            return {"status": "error", "message": "지원하지 않는 query 형식입니다.", "http_status": 400}

        # 2) 필터링
        def match_row(r: dict) -> bool:
            if f["회원명"]:
                if f["회원명"] not in _norm(r.get("회원명", "")):
                    return False
            if f["회원번호"]:
                if _norm(r.get("회원번호", "")) != f["회원번호"]:
                    return False
            if f["휴대폰번호"]:
                if _digits(r.get("휴대폰번호", "")) != _digits(f["휴대폰번호"]):
                    return False
            if f["특수번호"] is not None:
                if _norm(r.get("특수번호", "")) != f["특수번호"]:
                    return False
            return True

        matched = [r for r in rows if match_row(r)]
        matched.sort(key=lambda r: _norm(r.get("회원명", "")))

        results = [_compact_row(r) for r in matched]
        display = [_line(d) for d in results]


        return {
            "status": "success",
            "intent": "search_member",
            "count": len(results),
            "results": results,
            "display": display
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}




# ======================================================================================
# ✅ 회원 등록 (라우트)
# ======================================================================================
def register_member_func():
    """
    회원 등록 함수 (라우트 아님)
    📌 설명:
    - 자연어 요청문: "회원등록 이판주 12345678 010-2759-9001"
    - JSON 입력: {"회원명": "이판주", "회원번호": "12345678", "휴대폰번호": "010-2759-9001"}
    """
    try:
        query = g.query.get("query")
        raw_text = g.query.get("raw_text")

        name, number, phone = "", "", ""

        # 1) 자연어 입력 기반 파싱
        if raw_text and "회원등록" in raw_text:
            parts = raw_text.split()
            for part in parts:
                if re.fullmatch(r"[가-힣]{2,4}", part):  # 이름
                    name = part
                elif re.fullmatch(r"\d{5,8}", part):   # 회원번호
                    number = part
                elif re.fullmatch(r"(010-\d{3,4}-\d{4}|\d{10,11})", part):  # 휴대폰
                    phone = part

        # 2) JSON 입력 방식
        if isinstance(query, dict):
            name = query.get("회원명", name).strip()
            number = query.get("회원번호", number).strip()
            phone = query.get("휴대폰번호", phone).strip()

        if not name:
            return {
                "status": "error",
                "message": "회원명은 필수 입력 항목입니다.",
                "http_status": 400
            }

        result = register_member_internal(name, number, phone)
        return {**result, "http_status": 201}

    except ValueError as ve:
        return {
            "status": "error",
            "message": str(ve),
            "http_status": 400
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
            "http_status": 500
        }



# ======================================================================================
# ✅ 회원 수정
# ======================================================================================
def update_member_func():
    """
    회원 수정 함수 (라우트 아님)
    📌 설명:
    - g.query["query"] 또는 raw_text 에서 요청문을 추출하여 회원 정보를 수정
    - 자연어 요청문 예: "홍길동 주소 부산 해운대구로 변경"
    - JSON 입력 예: {"요청문": "홍길동 주소 부산 해운대구로 변경"}
    """
    try:
        query = g.query.get("query") if hasattr(g, "query") else None
        raw_text = g.query.get("raw_text") if hasattr(g, "query") else None

        요청문 = ""
        if isinstance(query, dict):
            요청문 = (query.get("요청문") or "").strip()
        elif isinstance(query, str):
            요청문 = query.strip()

        if not 요청문 and raw_text:
            요청문 = raw_text.strip()

        if not 요청문:
            return {
                "status": "error",
                "message": "요청문이 비어 있습니다.",
                "http_status": 400
            }

        result = update_member_internal(요청문)
        return {**result, "http_status": 200}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
            "http_status": 500
        }

    



# ======================================================================================
# ✅ JSON 기반 회원 수정/저장 API
# ======================================================================================
def save_member_func():
    """
    회원 저장/수정 함수 (라우트 아님)
    📌 설명:
    - 자연어 요청문을 파싱하여 회원을 신규 등록하거나, 기존 회원 정보를 수정합니다.
    - 업서트(Upsert) 기능: 없으면 등록, 있으면 수정
    📥 입력 예시:
    {
      "요청문": "홍길동 회원번호 12345 휴대폰 010-1111-2222 주소 서울"
    }
    """
    try:
        query = g.query.get("query") if hasattr(g, "query") else None
        raw_text = g.query.get("raw_text") if hasattr(g, "query") else None

        # ✅ 요청문 추출
        요청문 = ""
        if isinstance(query, dict):
            요청문 = query.get("요청문") or query.get("회원명", "")
        elif isinstance(query, str):
            요청문 = query
        if not 요청문 and raw_text:
            요청문 = raw_text

        if not 요청문:
            return {
                "status": "error",
                "message": "입력 문장이 없습니다.",
                "http_status": 400
            }

        # ✅ 파싱
        name, number, phone, lineage = parse_registration(요청문)
        if not name:
            return {
                "status": "error",
                "message": "회원명을 추출할 수 없습니다.",
                "http_status": 400
            }

        # ✅ 주소 기본값 처리
        address = ""
        if isinstance(query, dict):
            address = query.get("주소") or query.get("address", "")

        # ✅ 시트 접근
        sheet = get_member_sheet()
        headers = [h.strip() for h in sheet.row_values(1)]
        rows = sheet.get_all_records()

        # ✅ 기존 회원 여부 확인 (수정)
        for i, row in enumerate(rows):
            if str(row.get("회원명", "")).strip() == name:
                for key, value in {
                    "회원명": name,
                    "회원번호": number,
                    "휴대폰번호": phone,
                    "계보도": lineage,
                    "주소": address
                }.items():
                    if key in headers and value:
                        row_idx = i + 2
                        col_idx = headers.index(key) + 1
                        safe_update_cell(sheet, row_idx, col_idx, value, clear_first=True)

                return {
                    "status": "success",
                    "message": f"{name} 기존 회원 정보 수정 완료",
                    "http_status": 200
                }

        # ✅ 신규 등록
        new_row = [""] * len(headers)
        for key, value in {
            "회원명": name,
            "회원번호": number,
            "휴대폰번호": phone,
            "계보도": lineage,
            "주소": address
        }.items():
            if key in headers and value:
                new_row[headers.index(key)] = value

        sheet.insert_row(new_row, 2)
        return {
            "status": "success",
            "message": f"{name} 회원 신규 등록 완료",
            "http_status": 201
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
            "http_status": 500
        }



# ======================================================================================
# ✅ 회원 삭제 API
# ======================================================================================
def delete_member_func():
    """
    회원 전체 삭제 함수 (라우트 아님)
    📌 설명:
    - 회원명을 기준으로 DB 시트에서 전체 행을 삭제합니다.
    - before_request 에서 g.query 에 값이 세팅되어 있어야 함.
    📥 입력(JSON 예시):
    {
      "회원명": "홍길동"
    }
    """
    try:
        query = g.query.get("query") if hasattr(g, "query") else None

        if isinstance(query, dict):
            name = (query.get("회원명") or "").strip()
        else:
            name = (query or "").strip()

        if not name:
            return {
                "status": "error",
                "message": "회원명은 필수 입력 항목입니다.",
                "http_status": 400
            }

        result, status = delete_member_internal(name)
        return {**result, "http_status": status}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
            "http_status": 500
        }





# ======================================================================================
# ✅ 자연어 요청 회원 삭제 라우트
# ======================================================================================
def delete_member_field_nl_func():
    """
    회원 필드 삭제 (자연어 기반)
    📌 설명:
    - 자연어 문장에서 특정 필드를 추출하여 해당 회원의 일부 필드를 삭제합니다.
    - '회원명', '회원번호'는 삭제 불가 (삭제 요청 자체를 막음)
    - '홍길동 삭제' → 전체 삭제 방지 (별도 API /delete_member 사용)

    📥 입력(JSON 예시):
    {
      "요청문": "이판여 주소랑 휴대폰번호 삭제"
    }
    """
    try:
        req = request.get_json(force=True)
        text = (req.get("요청문") or "").strip()

        if not text:
            return {"status": "error", "message": "요청문을 입력해야 합니다.", "http_status": 400}

        result, status = delete_member_field_nl_internal(text)
        return {**result, "http_status": status}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e), "http_status": 500}


