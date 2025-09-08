import re

# ===== service (비즈니스 로직) =====
from service.service_member import (
    find_member_internal,            # 회원 조회 (DB 시트 검색)
    register_member_internal,        # 회원 등록 (DB 추가)
    update_member_internal,          # 회원 수정 (DB 갱신)
    delete_member_internal,          # 회원 삭제 (DB 행 제거)
    delete_member_field_nl_internal, # 회원 필드 삭제 (자연어 기반)
    process_member_query,            # 회원 질의 처리 (NLU 결과 해석)
)

# ===== app (전역 함수) =====
from utils.text_cleaner import normalize_code_query   # 코드 검색 정규화

# ===== utils =====
from utils.sheets import (
    get_rows_from_sheet,   # DB 시트 행 조회
    get_member_sheet,      # 회원 시트 접근
    safe_update_cell       # 안전한 셀 수정
)
from parser import parse_registration   # 회원 등록 파서

# ===== flask =====
from flask import g, request







def search_member_func():
    """
    회원 검색 허브 함수 (라우트 아님)
    - g.query["query"] 값이 '코드...' → search_by_code_logic() 호출
    - 그 외 → find_member_logic() 호출
    """
    try:
        query = g.query.get("query")

        if query is None:
            return {
                "status": "error",
                "message": "검색어(query)가 필요합니다.",
                "http_status": 400
            }

        # 문자열일 경우만 strip()
        if isinstance(query, str):
            query = query.strip()

        # raw_text는 사람이 입력한 원본 → dict는 str로 변환
        g.query["raw_text"] = query if isinstance(query, str) else str(query)

        # 코드 검색 (문자열일 때만 체크)
        if isinstance(query, str) and (query.startswith("코드") or query.lower().startswith("code")):
            result = search_by_code_logic()
        else:
            result = find_member_logic()

        http_status = 200 if result.get("status") == "success" else 400
        return {**result, "http_status": http_status}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
            "http_status": 500
        }


# ======================================================================================
# ✅ 회원 조회 (코드 검색 전용)
# ======================================================================================
def search_by_code_logic() -> dict:
    """
    코드 기반 회원 검색 함수 (항상 리스트 형식 출력)
    - before_request 에서 g.query, g.raw_text 사용
    """
    query = g.query.get("query")
    raw_text = g.query.get("raw_text")

    if not query:
        return {"status": "error", "message": "검색어(query)를 입력하세요.", "http_status": 400}

    # ✅ 코드 정규화
    query = normalize_code_query(query)

    if not query.startswith("코드"):
        return {"status": "error", "message": "올바른 코드 검색어가 아닙니다. 예: 코드a", "http_status": 400}

    code_value = query.replace("코드", "").strip().upper()

    try:
        # ✅ DB 조회
        rows = get_rows_from_sheet("DB")
        results = [
            row for row in rows
            if str(row.get("코드", "")).strip().upper() == code_value
        ]

        # ✅ 결과 포맷
        formatted_results = []
        for r in results:
            member_name = str(r.get("회원명", "")).strip()
            member_number = str(r.get("회원번호", "")).strip()
            special_number = str(r.get("특수번호", "")).strip()
            phone = str(r.get("휴대폰번호", "")).strip()

            parts = []
            if member_number:
                parts.append(f"회원번호: {member_number}")
            if special_number:
                parts.append(f"특수번호: {special_number}")
            if phone:
                parts.append(f"휴대폰: {phone}")

            formatted = f"{member_name} ({', '.join(parts)})" if parts else member_name
            formatted_results.append((member_name, formatted))

        formatted_results.sort(key=lambda x: x[0])

        return {
            "status": "success",
            "query": raw_text,
            "code": code_value,
            "count": len(formatted_results),
            "results": [f for _, f in formatted_results],
            "http_status": 200
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"코드 검색 실패: {str(e)}",
            "http_status": 500
        }


# ======================================================================================
# ✅ 회원 조회 (JSON 전용)
# ======================================================================================
def find_member_logic() -> dict:
    """
    회원 조회 함수 (g.query 기반)
    """
    query = g.query.get("query")
    if not query:
        return {"status": "error", "message": "회원 조회를 위한 query가 필요합니다.", "http_status": 400}

    try:
        if isinstance(query, dict):
            results = find_member_internal(
                name=query.get("회원명", ""),
                number=query.get("회원번호", ""),
                code=query.get("코드", ""),
                phone=query.get("휴대폰번호", ""),
                special=query.get("특수번호", "")
            )
        else:
            results = find_member_internal(name=query)

        return {"status": "success", "results": results, "http_status": 200}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"회원 조회 실패: {str(e)}",
            "http_status": 500
        }





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


