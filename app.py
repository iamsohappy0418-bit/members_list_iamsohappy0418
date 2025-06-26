import os
import json
import re
import pandas as pd
import gspread
import pytz
import uuid
import openai
from flask import Flask, request, jsonify, render_template
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from gspread.utils import rowcol_to_a1
from datetime import datetime
from collections import Counter
from oauth2client.service_account import ServiceAccountCredentials
 





# ✅ 환경 변수 로드


if os.getenv("RENDER") is None:  # 로컬에서 실행 중일 때만
    from dotenv import load_dotenv
    dotenv_path = os.path.abspath('.env')
    if not os.path.exists(dotenv_path):
        raise FileNotFoundError(f".env 파일이 존재하지 않습니다: {dotenv_path}")
    load_dotenv(dotenv_path)

# 공통 처리
GOOGLE_SHEET_KEY = os.getenv("GOOGLE_SHEET_KEY")
GOOGLE_SHEET_TITLE = os.getenv("GOOGLE_SHEET_TITLE")  # ✅ 시트명 불러오기

# 한국 시간 가져오는 함수
def now_kst():
    return datetime.now(pytz.timezone("Asia/Seoul"))



# ✅ 확인용 출력 (선택)
print("✅ GOOGLE_SHEET_TITLE:", os.getenv("GOOGLE_SHEET_TITLE"))
print("✅ GOOGLE_SHEET_KEY 존재 여부:", "Yes" if os.getenv("GOOGLE_SHEET_KEY") else "No")


app = Flask(__name__)
if not os.getenv("GOOGLE_SHEET_KEY"):
    raise EnvironmentError("환경변수 GOOGLE_SHEET_KEY가 설정되지 않았습니다.")
if not os.getenv("GOOGLE_SHEET_TITLE"):  # ✅ 시트 이름도 환경변수에서 불러옴
    raise EnvironmentError("환경변수 GOOGLE_SHEET_TITLE이 설정되지 않았습니다.")


# 자연어 명령 키워드 매핑
UPDATE_KEYS = {
    "회원": ["회원수정", "회원내용수정", "회원내용을 수정", "회원변경", "회원내용변경", "회원내용을 고쳐", "수정", "변경", "고쳐"],
    "주문": ["주문수정", "주문내용수정", "주문내용을 수정", "주문변경", "주문내용변경", "주문내용을 고쳐"],
    "후원수당": ["후원수당수정", "후원수당내용수정", "후원수당내용을 수정", "후원수당변경", "후원수당내용변경", "후원수당내용을 고쳐"]
}

# ✅ 주문 항목 헤더
ORDER_HEADERS = [
    "주문일자", "회원명", "회원번호", "휴대폰번호", "제품명",
    "제품가격", "PV", "결재방법", "주문자_고객명", "주문자_휴대폰번호",
    "배송처", "수령확인"
]




def parse_request(text):
    result = {"회원명": "", "수정목록": []}

    # 회원명 추출
    name_match = re.search(r"^([가-힣]{2,3})", text)
    if not name_match:
        name_match = re.search(r"([가-힣]{2,3})\s*회원[의은는이가]?", text)
    if name_match:
        result["회원명"] = name_match.group(1)

    # 전체 필드
    필드패턴 = r"(회원명|휴대폰번호|회원번호|비밀번호|가입일자|생년월일|통신사|친밀도|근무처|계보도|소개한분|주소|메모|코드|카드사|카드주인|카드번호|유효기간|비번|카드생년월일|분류|회원단계|연령/성별|직업|가족관계|니즈|애용제품|콘텐츠|습관챌린지|비즈니스시스템|GLC프로젝트|리더님)"
    수정_패턴 = re.findall(rf"{필드패턴}\s*(?:은|는|을|를)?\s*([\w가-힣\d\-\.:/@]+)", text)

    for 필드, 값 in 수정_패턴:
        result["수정목록"].append({"필드": 필드, "값": 값})

    return result





@app.route("/")
def home():
    return "Flask 서버가 실행 중입니다."

def get_db_sheet():
    return get_worksheet("DB")

def get_member_sheet():
    return get_worksheet("DB")

def get_product_order_sheet():
    return get_worksheet("제품주문")

def get_add_order_sheet():
    return get_worksheet("제품주문")

def get_save_order_sheet():
    return get_worksheet("제품주문")

def get_delete_order_request_sheet():
    return get_worksheet("제품주문")

def get_delete_order_confirm_sheet():
    return get_worksheet("제품주문")

def get_ss_sheet():
    return get_worksheet("후원수당")

def get_counseling_sheet():
    return get_worksheet("상담일지")

def get_mymemo_sheet():
    return get_worksheet("개인메모")

def get_search_memo_by_tags_sheet():
    return get_worksheet("개인메모")

def get_dailyrecord_sheet():
    return get_worksheet("활동일지")

def get_product_order_sheet():
    return get_worksheet("제품주문")    

def get_image_sheet():
    return get_worksheet("사진저장")



# ✅ 환경 변수 로드 및 GPT API 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ Google Sheets 인증
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)



# ✅ Google Sheets 연동 함수
def get_worksheet(sheet_name):
    try:
        sheet = client.open(GOOGLE_SHEET_TITLE)
        return sheet.worksheet(sheet_name)
    except Exception as e:
        print(f"[시트 접근 오류] {e}")
        return None




# ✅ 필드 키워드 → 시트의 실제 컬럼명 매핑
field_map = {
    "휴대폰번호": "휴대폰번호",
    "핸드폰": "휴대폰번호",
    "주소": "주소",
    "회원번호": "회원번호",
    "이름": "회원명",
    "생일": "생년월일",
    "생년월일": "생년월일",
    "비밀번호": "비밀번호",
    "직업": "근무처",
    "직장": "근무처",
    # 필요한 항목 계속 추가 가능
}










# ✅ 회원 조회
@app.route("/find_member", methods=["POST"])
def find_member():
    try:
        data = request.get_json()
        name = data.get("회원명", "").strip()
        number = data.get("회원번호", "").strip()

        if not name and not number:
            return jsonify({"error": "회원명 또는 회원번호를 입력해야 합니다."}), 400

        sheet = get_member_sheet()
        db = sheet.get_all_values()
        headers, rows = db[0], db[1:]

        for row in rows:
            row_dict = dict(zip(headers, row))
            if name and row_dict.get("회원명") == name:
                return jsonify(row_dict), 200
            if number and row_dict.get("회원번호") == number:
                return jsonify(row_dict), 200

        return jsonify({"error": "해당 회원 정보를 찾을 수 없습니다."}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500





















# ✅ 회원 수정
# ✅ 자연어 요청문에서 필드와 값 추출, 회원 dict 수정
# 필드 맵 (추가 가능)
field_map = {
    "휴대폰번호": "휴대폰번호",
    "핸드폰": "휴대폰번호",
    "회원번호": "회원번호",
    "주소": "주소",
    "이메일": "이메일",
    "이름": "회원명",
    "생일": "생년월일",
    "생년월일": "생년월일",
    "비밀번호": "비밀번호",
    "직업": "근무처",
    "직장": "근무처",
}




def parse_request_and_update(data: str, member: dict) -> tuple:
    수정된필드 = {}

# 정렬: 긴 키워드 우선
    for keyword in sorted(field_map.keys(), key=lambda k: -len(k)):
        # 다음 키워드 목록 준비
        keywords_pattern = '|'.join(sorted(field_map.keys(), key=lambda k: -len(k)))
        # 핵심 정규식: 현재 keyword → 다음 keyword 또는 문장 끝 전까지 추출
        pattern = rf"{keyword}(?:를|은|는|이|:|：)?\s*(?P<value>.+?)(?=\s+(?:{keywords_pattern})(?:를|은|는|이|:|：)?|\s*$)"
        matches = re.finditer(pattern, data)


        matches = re.finditer(pattern, data)

        for match in matches:
            value_raw = match.group("value").strip()

            value_raw = re.sub(r'\s+', ' ', value_raw)

            # 후처리: 조사/명령어 제거
            value = re.sub(r"(으로|로|에)?(수정|변경|바꿔줘|바꿔|바꿈)?$", "", value_raw)

            field = field_map[keyword]

            if field not in 수정된필드 and value not in 수정된필드.values():  # ✅ 중복 저장 방지
                수정된필드[field] = value
                member[field] = value
                member[f"{field}_기록"] = f"(기록됨: {value})"

    return member, 수정된필드
















# ✅ 회원 수정 API
@app.route("/update_member", methods=["POST"])
def update_member():
    try:
        raw_data = request.data.decode("utf-8")
        data = json.loads(raw_data)
        요청문 = data.get("요청문", "").strip()

        if not 요청문:
            return jsonify({"error": "요청문이 비어 있습니다."}), 400

        # ✅ 시트 가져오기 및 회원명 리스트 확보
        sheet = get_member_sheet()
        db = sheet.get_all_records()
        raw_headers = sheet.row_values(1)
        headers = [h.strip().lower() for h in raw_headers]

        # ✅ 안전하게 문자열로 변환 후 strip()
        member_names = [str(row.get("회원명", "")).strip() for row in db if row.get("회원명") is not None]


        # ✅ 요청문 내 포함된 실제 회원명 찾기 (길이순 정렬)
        name = None
        for candidate in sorted(member_names, key=lambda x: -len(x)):
            if candidate and candidate in 요청문:
                name = candidate
                break

        if not name:
            return jsonify({"error": "요청문에서 유효한 회원명을 찾을 수 없습니다."}), 400

        # ✅ 해당 회원 찾기
        matching_rows = [i for i, row in enumerate(db) if row.get("회원명") == name]
        if len(matching_rows) == 0:
            return jsonify({"error": f"'{name}' 회원을 찾을 수 없습니다."}), 404
        if len(matching_rows) > 1:
            return jsonify({"error": f"'{name}' 회원이 중복됩니다. 고유한 이름만 지원합니다."}), 400

        row_index = matching_rows[0] + 2  # 헤더 포함으로 +2
        member = db[matching_rows[0]]

        # ✅ 자연어 해석 및 필드 수정
        updated_member, 수정된필드 = parse_request_and_update(요청문, member)

        수정결과 = []
        무시된필드 = []

        for key, value in updated_member.items():
            key_strip = key.strip()
            key_lower = key_strip.lower()

            # _기록 필드는 저장 안 함
            if key_strip.endswith("_기록"):
                continue

            if key_lower in headers:
                col_index = headers.index(key_lower) + 1
                sheet.update_cell(row_index, col_index, value)
                수정결과.append({"필드": key_strip, "값": value})
            else:
                무시된필드.append(key_strip)

        return jsonify({
            "status": "success",
            "회원명": name,
            "수정": 수정결과,
            "무시된_필드": 무시된필드
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500















# ✅ 회원 시트 접근 함수
def get_member_sheet():
    return get_worksheet("DB")  # 시트 탭 이름에 맞게 수정



# ✅ 회원 등록 명령 파싱 함수
def parse_registration(text):
    import re
    text = text.strip()
    print(f"[🔍DEBUG] 입력 text: '{text}'")

    # 형식 1
    match = re.search(r"(.+?)\s*회원번호\s*(\d+)", text)
    if match:
        name, number = match.group(1).strip(), match.group(2).strip()
        print(f"[✅DEBUG] 형식1 매칭 → name: '{name}', number: '{number}'")
        return name, number

    # 형식 2
    match = re.search(r"(.+?)\s+(\d{6,})", text)
    if match and "등록" in text:
        name, number = match.group(1).strip(), match.group(2).strip()
        print(f"[✅DEBUG] 형식2 매칭 → name: '{name}', number: '{number}'")
        return name, number

    # 형식 3 (김철수 등록, 김 철수 등록)
    match = re.search(r"^([\w가-힣\s]+?)\s*등록$", text)
    if match:
        name = match.group(1).strip()
        print(f"[✅DEBUG] 형식3 매칭 → name: '{name}', number: None")
        return name, None

    print("[❌DEBUG] 어떤 패턴에도 매칭되지 않음.")
    return None, None










# 예시 시트 함수 (실제 구현에 맞게 교체)
# ✅ 회원 등록 API
@app.route("/register", methods=["POST"])
def register_member():
    data = request.get_json()
    print(f"\n[1] ✅ 요청 데이터 수신: {data}")

    text = data.get("text", "")
    if not text:
        print("[1] ❌ 'text' 키가 없습니다.")
        return jsonify({"error": "'text' 키가 없습니다."}), 400

    print(f"[1] ✅ text 내용: '{text}'")

    # 이름과 회원번호 추출
    name, number = parse_registration(text)
    print(f"[2] 📦 parse_registration 결과 → name: {name}, number: {number}")

    if not name:
        print("[3] ❌ 이름 추출 실패")
        return jsonify({"error": "이름 추출 실패"}), 400

    if not number:
        import uuid
        number = str(uuid.uuid4())[:8]
        print(f"[3] ⚠️ 회원번호 없음 → 기본값 할당: {number}")
    else:
        print(f"[3] ✅ 회원번호: {number}")

    try:
        sheet = get_member_sheet()
        print("[4] ✅ 시트 접근 성공")
    except Exception as e:
        print(f"[4] ❌ 시트 접근 실패: {e}")
        return jsonify({"error": "시트 접근 실패"}), 500

    data_rows = sheet.get_all_records()
    headers = sheet.row_values(1)
    print(f"[4] ✅ 시트 헤더: {headers}")

    for i, row in enumerate(data_rows):
        if row.get("회원명") == name:
            print(f"[5] ⚠️ 기존 회원 '{name}' 발견 → 덮어쓰기")
            for key, value in {"회원명": name, "회원번호": number}.items():
                if key in headers:
                    sheet.update_cell(i + 2, headers.index(key) + 1, value)
            return jsonify({"message": f"{name} 기존 회원 정보 수정 완료"})

    print(f"[5] 🆕 신규 회원 '{name}' 등록")
    new_row = [''] * len(headers)
    for key, value in {"회원명": name, "회원번호": number}.items():
        try:
            col_idx = headers.index(key)
            new_row[col_idx] = value
        except ValueError:
            print(f"[5] ⚠️ '{key}' 컬럼이 없음 → 무시됨")


    print(f"[5] 💬 최종 new_row 값: {new_row}")
    print(f"[4] 헤더 raw: {sheet.row_values(1)}")
    print(f"[4] 헤더 strip 적용 후: {headers}")

    sheet.append_row(new_row)
    print(f"[6] ✅ 신규 회원 '{name}' 저장 완료")
    return jsonify({"message": f"{name} 회원 등록 완료"})



































   



# ✅ JSON 기반 회원 저장/수정 API
@app.route('/save_member', methods=['POST'])
def save_member():
    try:
        # 1. 요청값 정리
        req_raw = request.get_json()
        req = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in req_raw.items()}
        name = req.get("회원명", "").strip()
        number = req.get("회원번호", "").strip().lower()
        요청문_raw = req_raw.get("요청문", "") if isinstance(req_raw, dict) else ""

        if not name:
            return jsonify({"error": "회원명은 필수입니다"}), 400

        # 2. 시트 데이터 준비
        sheet = get_member_sheet()
        data = sheet.get_all_records()
        headers = [h.strip() for h in sheet.row_values(1)]

        # 3. 기존 회원 여부 확인
        for i, row in enumerate(data):
            if str(row.get("회원명", "")).strip() == name:
                요약정보 = {k: row.get(k, "") for k in ["회원명", "회원번호", "휴대폰번호", "주소"] if k in row}
                return jsonify({
                    "message": f"이미 등록된 회원 '{name}'입니다.",
                    "회원정보": 요약정보
                }), 200

        # 4. 등록 문구 포함 여부 확인
        등록요청여부 = "등록" in 요청문_raw or "등록" in name

        if 등록요청여부:
            new_row = [''] * len(headers)
            if "회원명" in headers:
                new_row[headers.index("회원명")] = name
            if "회원번호" in headers and number:
                new_row[headers.index("회원번호")] = number
            for key, value in req.items():
                if key in headers and key not in ["회원명", "회원번호"]:
                    new_row[headers.index(key)] = value

            sheet.insert_row(new_row, 2)
            return jsonify({
                "message": f"{name} 회원 신규 등록 완료" + (f" (회원번호 {number})" if number else "")
            }), 200
        else:
            return jsonify({
                "message": f"'{name}' 회원은 등록되지 않았습니다. '등록' 문구가 포함되어야 합니다."
            }), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500













# ✅ 회원 삭제 API (안전 확인 포함)
# ✅ 회원 삭제 API
@app.route('/delete_member', methods=['POST'])
def delete_member():
    try:
        name = request.get_json().get("회원명")
        if not name:
            return jsonify({"error": "회원명을 입력해야 합니다."}), 400

        sheet = get_member_sheet()
        data = sheet.get_all_records()

        for i, row in enumerate(data):
            if row.get('회원명') == name:
                sheet.delete_rows(i + 2)  # 헤더 포함으로 인덱스 +2
                return jsonify({"message": f"'{name}' 회원 삭제 완료"}), 200

        return jsonify({"error": f"'{name}' 회원을 찾을 수 없습니다."}), 404

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
















# 예시 데이터베이스 (실제 환경에서는 DB 연동)
mock_db = {
    "홍길동": {
        "회원명": "홍길동",
        "회원번호": "12345678",
        "휴대폰번호": "010-1234-5678",
        "주소": "서울시 강남구"
    }
}

# 동의어 포함 field_map
field_map = {
    "회원명": "회원명", "이름": "회원명", "성함": "회원명",
    "회원번호": "회원번호", "번호": "회원번호", "아이디": "회원번호",
    "생년월일": "생년월일", "생일": "생년월일", "출생일": "생년월일",
    "성별": "연령/성별", "연령": "연령/성별", "나이": "연령/성별",
    "휴대폰번호": "휴대폰번호", "전화번호": "휴대폰번호", "연락처": "휴대폰번호", "폰": "휴대폰번호",
    "주소": "주소", "거주지": "주소", "사는곳": "주소",
    "직업": "직업", "일": "직업", "하는일": "직업",
    "가입일자": "가입일자", "입회일": "가입일자", "등록일": "가입일자",
    "가족관계": "가족관계", "가족": "가족관계",
    "추천인": "소개한분", "소개자": "소개한분",
    "계보도": "계보도",
    "후원인": "카드주인", "카드주인": "카드주인", "스폰서": "카드주인",
    "카드사": "카드사", "카드번호": "카드번호", "카드생년월일": "카드생년월일",
    "리더": "리더님", "리더님": "리더님", "멘토": "리더님",
    "비번": "비번",   
    "비밀번호": "비밀번호",
    "시스템코드": "코드", "코드": "코드", "시스템": "비즈니스시스템",
    "콘텐츠": "콘텐츠", "통신사": "통신사", "유효기간": "유효기간", "수신동의": "수신동의",
    "메모": "메모", "비고": "메모", "노트": "메모",
    "GLC": "GLC프로젝트", "프로젝트": "GLC프로젝트", "단계": "회원단계",
    "분류": "분류", "니즈": "니즈", "관심": "니즈",
    "애용제품": "애용제품", "제품": "애용제품", "주력제품": "애용제품",
    "친밀도": "친밀도", "관계": "친밀도",
    "근무처": "근무처", "회사": "근무처", "직장": "근무처"
}









# 다중 필드 업데이트 함수
def parse_request_and_update_multi(data: str, member: dict) -> dict:
    for keyword in field_map:
        # 유연한 한글 + 숫자 + 기호 값 처리
        pattern = rf"{keyword}\s*[:：]?\s*([^\s]+)"
        for match in re.finditer(pattern, data):
            value_raw = match.group(1)
            value = re.sub(r"(으로|로|에|를|은|는)$", "", value_raw)
            field = field_map[keyword]
            member[field] = value
            member[f"{field}_기록"] = f"(기록됨: {value})"
    return member



def extract_nouns(text):
    return re.findall(r'[가-힣]{2,}', text)

def generate_tags(text):
    nouns = extract_nouns(text)
    top_keywords = [word for word, _ in Counter(nouns).most_common(5)]
    return top_keywords



API_URL = os.getenv("COUNSELING_API_URL")

HEADERS = {"Content-Type": "application/json"}

def determine_mode(content: str) -> str:
    if "상담일지" in content:
        return "1"  # 상담일지 (공유)
    elif "개인메모" in content:
        return "개인"
    elif "활동일지" in content:
        return "3"
    else:
        return "1"  # 기본값

@app.route('/save_note', methods=['POST'])
def save_note():
    data = request.json
    요청문 = data.get("요청문", "")
    mode = determine_mode(요청문)

    payload = {
        "요청문": 요청문,
        "mode": mode,
        "allow_unregistered": True
    }

    response = requests.post(API_URL, json=payload, headers=HEADERS)
    if response.ok:
        return jsonify({"status": "success", "message": "저장 완료"})
    else:
        return jsonify({"status": "error", "message": response.text})
        




# ✅ 시트 저장 함수 (Google Sheets 연동 및 중복 확인)
def save_to_sheet(sheet_name, member_name, content):
    try:
        sheet = get_worksheet(sheet_name)
        if sheet is None:
            print(f"[오류] '{sheet_name}' 시트를 찾을 수 없습니다.")
            return False

        existing = sheet.get_all_values()
        contents = [row[2] if len(row) > 2 else "" for row in existing]  # 내용은 3열 기준
        if content in contents:
            print(f"[중복] 이미 같은 내용이 '{sheet_name}'에 존재합니다.")
            return False

        now = datetime.now(pytz.timezone("Asia/Seoul"))
        time_str = now.strftime("%Y-%m-%d %H:%M")

        sheet.insert_row([time_str, member_name, content], index=2)
        print(f"[저장완료] '{sheet_name}' 시트에 저장 완료")
        return True

    except Exception as e:
        print(f"[시트 저장 오류: {sheet_name}] {e}")
        return False


# ✅ /add_counseling 처리 API (자연어 입력 기반 저장 + mode 분기)
@app.route('/add_counseling', methods=['POST'])
def add_counseling():
    try:
        data = request.get_json()
        text = data.get("요청문", "")

        # ✅ 시트 키워드 정규화 처리
        text = text.replace("개인 메모", "개인메모")
        text = text.replace("상담 일지", "상담일지")
        text = text.replace("활동 일지", "활동일지")

        sheet_keywords = ["상담일지", "개인메모", "활동일지", "직접입력"]
        action_keywords = ["저장", "기록", "입력"]

        if not any(kw in text for kw in sheet_keywords) or not any(kw in text for kw in action_keywords):
            return jsonify({"message": "저장하려면 '상담일지', '개인메모', '활동일지', '직접입력' 중 하나와 '저장', '기록', '입력' 같은 동작어를 함께 포함해 주세요."})

        match = re.search(r'([가-힣]{2,3})\s*(상담일지|개인메모|활동일지|직접입력)', text)
        if not match:
            return jsonify({"message": "회원명을 인식할 수 없습니다."})
        member_name = match.group(1)
        matched_sheet = match.group(2)

        for kw in sheet_keywords + action_keywords:
            text = text.replace(f"{member_name}{kw}", "")
            text = text.replace(f"{member_name} {kw}", "")
            text = text.replace(kw, "")
        text = text.strip()
        # 앞에 붙은 콜론(: 또는 ：) 제거
        text = re.sub(r'^[:：]\s*', '', text)


        if matched_sheet not in ["상담일지", "개인메모", "활동일지"]:
            return jsonify({"message": "저장할 시트를 인식할 수 없습니다."})

        if save_to_sheet(matched_sheet, member_name, text):
            return jsonify({"message": f"{member_name}님의 {matched_sheet} 저장이 완료되었습니다."})
        else:
            return jsonify({"message": f"같은 내용이 이미 '{matched_sheet}' 시트에 저장되어 있습니다."})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



    
    
    
    
    




    












@app.route("/search_memo_by_tags", methods=["POST"])
def search_memo_by_tags():
    try:
        data = request.get_json()
        input_tags = data.get("tags", [])
        limit = int(data.get("limit", 10))
        sort_by = data.get("sort_by", "date").lower()
        min_match = int(data.get("min_match", 1))

        if not input_tags:
            return jsonify({"error": "태그 리스트가 비어 있습니다."}), 400
        if sort_by not in ["date", "tag"]:
            return jsonify({"error": "sort_by는 'date' 또는 'tag'만 가능합니다."}), 400

        sheet = get_mymemo_sheet()
        values = sheet.get_all_values()[1:]  # 헤더 제외
        results = []

        for row in values:
            if len(row) < 3:
                continue
            member, date_str, content = row[0], row[1], row[2]

            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            except ValueError:
                continue  # 날짜 형식 오류시 건너뜀

            memo_tags = extract_nouns(content)
            similarity = len(set(input_tags) & set(memo_tags))
            if similarity >= min_match:
                results.append({
                    "회원명": member,
                    "날짜": date_str,
                    "내용": content,
                    "일치_태그수": similarity,
                    "날짜_obj": parsed_date
                })

        # 정렬 조건 적용
        if sort_by == "tag":
            results.sort(key=lambda x: (x["일치_태그수"], x["날짜_obj"]), reverse=True)
        else:  # 기본: 날짜순
            results.sort(key=lambda x: (x["날짜_obj"], x["일치_태그수"]), reverse=True)

        # 날짜 객체 제거
        for r in results:
            del r["날짜_obj"]

        return jsonify({"검색결과": results[:limit]}), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500












    









@app.route("/order_upload_form")
def order_upload_form():
    return render_template("upload_order_form.html")







# ✅ 제품주문 시트

# ✅ 인증 처리
# ✅ Google Sheets 연동 함수


# ✅ 주문내역 시트 가져오기
sheet = get_worksheet("제품주문")


# ✅ 주문일자 처리 함수 (먼저 정의되어야 함)
# ✅ 주문일자 처리 함수 (수식 및 누락 방지)
# ✅ 주문일자 처리 함수 (자연어 + 문자열 고정)
from datetime import datetime, timedelta

# ✅ 오늘 날짜를 실제 문자열로 반환하는 함수
def process_order_date(raw_date: str) -> str:
    try:
        if not raw_date or raw_date.strip() == "":
            return now_kst().strftime('%Y-%m-%d')

        raw_date = raw_date.strip()

        if "오늘" in raw_date:
            return now_kst().strftime('%Y-%m-%d')
        elif "어제" in raw_date:
            return (now_kst() - timedelta(days=1)).strftime('%Y-%m-%d')
        elif "내일" in raw_date:
            return (now_kst() + timedelta(days=1)).strftime('%Y-%m-%d')

        # 날짜 형식 유효성 검사
        datetime.strptime(raw_date, "%Y-%m-%d")
        return raw_date

    except Exception:
        return now_kst().strftime('%Y-%m-%d')





# ✅ 주문 데이터 추가 함수
def insert_order_row(sheet, order_data):
    row = [
        process_order_date(data.get("주문일자", "")),
        order_data.get('회원명', ''),
        order_data.get('회원번호', ''),
        order_data.get('휴대폰번호', ''),
        order_data.get('제품명', ''),
        order_data.get('제품가격', ''),
        order_data.get('PV', ''),
        order_data.get('결재방법', ''),
        order_data.get('주문자_고객명', ''),
        order_data.get('주문자_휴대폰번호', ''),
        order_data.get('배송처', ''),
        order_data.get('수령확인', '')
    ]
    sheet.append_row(row)




# ✅ 사용 예시
data = {
    '회원명': '이태수',
    '제품명': '칫솔 1통',
    '제품가격': 9600,
    'PV': 4800,
    '결재방법': '카드',
    '주문자_고객명': '박태수'
}

if sheet:
    insert_order_row(sheet, data)













# ✅ 공통 주문 저장 함수
# ✅ 주문 저장 함수
def handle_order_save(data):
    sheet = get_worksheet("제품주문")
    if not sheet:
        raise Exception("제품주문 시트를 찾을 수 없습니다.")

    order_date = process_order_date(data.get("주문일자", ""))
    # ✅ 회원명 정제
    raw_name = data.get("회원명", "")
    name = re.sub(r"\s*등록$", "", raw_name).strip()
    row = [
        order_date,
        data.get("회원명", ""),
        data.get("회원번호", ""),
        data.get("휴대폰번호", ""),
        data.get("제품명", ""),
        float(data.get("제품가격", 0)),
        float(data.get("PV", 0)),
        data.get("결재방법", ""),
        data.get("주문자_고객명", ""),
        data.get("주문자_휴대폰번호", ""),
        data.get("배송처", ""),
        data.get("수령확인", "")
    ]

    values = sheet.get_all_values()
    if not values:
        headers = [
            "주문일자", "회원명", "회원번호", "휴대폰번호",
            "제품명", "제품가격", "PV", "결재방법",
            "주문자_고객명", "주문자_휴대폰번호", "배송처", "수령확인"
        ]
        sheet.append_row(headers)

    # 중복 방지 로직
    for existing in values[1:]:
        if (existing[0] == order_date and
            existing[1] == data.get("회원명") and
            existing[4] == data.get("제품명")):
            print("⚠️ 이미 동일한 주문이 존재하여 저장하지 않음")
            return

    sheet.insert_row(row, index=2)






# ✅ 제품 주문 등록 API
@app.route("/add_order", methods=["POST"])
def add_order():
    try:
        data = request.get_json()
        member_name = re.sub(r"\s*등록$", "", data.get("회원명", "")).strip()
      
        if not member_name:
            return jsonify({"error": "회원명을 입력해야 합니다."}), 400

        # ✅ 회원 정보 확인
        sheet = get_member_sheet()

        records = sheet.get_all_records()
        member_info = next((r for r in records if r.get("회원명") == member_name), None)
        if not member_info:
            return jsonify({"error": f"'{member_name}' 회원을 DB에서 찾을 수 없습니다."}), 404

        # ✅ 주문 시트 준비
        order_sheet = get_product_order_sheet()

        if not order_sheet.get_all_values():
            ORDER_HEADERS = [
                "주문일자", "회원명", "회원번호", "휴대폰번호",
                "제품명", "제품가격", "PV", "결재방법",
                "주문자_고객명", "주문자_휴대폰번호", "배송처", "수령확인"
            ]
            order_sheet.append_row(ORDER_HEADERS)

        # ✅ 주문 행 구성
        order_date = process_order_date(data.get("주문일자", ""))
        row = [
            order_date,
            member_name,
            member_info.get("회원번호", ""),
            member_info.get("휴대폰번호", ""),
            data.get("제품명", ""),
            float(data.get("제품가격", 0)),
            float(data.get("PV", 0)),
            data.get("결재방법", ""),
            data.get("주문자_고객명", ""),
            data.get("주문자_휴대폰번호", ""),
            data.get("배송처", ""),
            data.get("수령확인", "")
        ]

        # ✅ 2행(최신)으로 삽입
        order_sheet.insert_row(row, index=2)
        
       
        return jsonify({"message": "제품주문이 저장되었습니다."}), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    









# ✅ 주문 저장 API
@app.route("/save_order", methods=["POST"])
def save_order(
    회원명, 제품명, 제품가격, PV,
    주문자_고객명=None,
    주문자_휴대폰번호=None,
    주문일자=None,
    결재방법="카드",
    배송처=None,
    수령확인="0",
    ORDER_API_ENDPOINT = os.getenv("ORDER_API_ENDPOINT")

):


    data = {
        "회원명": 회원명,
        "주문일자": process_order_date(주문일자),  # ✅ 여기서 날짜 처리 통일
        "제품명": 제품명,
        "제품가격": 제품가격,
        "PV": PV,
        "결재방법": 결재방법,
        "주문자_고객명": 주문자_고객명,
        "주문자_휴대폰번호": 주문자_휴대폰번호,
        "배송처": 배송처,
        "수령확인": 수령확인
    }

    response = requests.post(endpoint, json=data)

    if response.status_code == 200:
        print("✅ 주문 저장 성공:", response.json())
        return response.json()
    else:
        print("❌ 주문 저장 실패:", response.status_code, response.text)
        return None

    








def normalize_order_fields(data: dict) -> dict:
    result = data.copy()

    # 주문완료란 / 주문상품란 → 제품정보 매핑
    for prefix in ["주문완료", "주문상품"]:
        if f"{prefix}_제품명" in data:
            result["제품명"] = data.get(f"{prefix}_제품명", "")
            result["제품가격"] = data.get(f"{prefix}_제품가격", "")
            result["PV"] = data.get(f"{prefix}_PV", "")

    # 배송지란 → 주문자 정보 매핑
    if "배송지_이름" in data:
        result["주문자_고객명"] = data.get("배송지_이름", "")
        result["주문자_휴대폰번호"] = data.get("배송지_휴대폰번호", "")
        result["배송처"] = data.get("배송지_주소", "")

    return result


# ✅ 주문일자 처리
def process_order_date(raw_date: str) -> str:
    try:
        if not raw_date or raw_date.strip() == "":
            return now_kst().strftime('%Y-%m-%d')

        raw_date = raw_date.strip()

        if "오늘" in raw_date:
            return now_kst().strftime('%Y-%m-%d')
        elif "어제" in raw_date:
            return (now_kst() - timedelta(days=1)).strftime('%Y-%m-%d')
        elif "내일" in raw_date:
            return (now_kst() + timedelta(days=1)).strftime('%Y-%m-%d')

        datetime.strptime(raw_date, "%Y-%m-%d")
        return raw_date
    except Exception:
        return now_kst().strftime('%Y-%m-%d')











# ✅ 최근 주문 확인 후 삭제 요청 유도
@app.route("/delete_order_request", methods=["POST"])
def delete_order_request():
    try:
        sheet = get_product_order_sheet()
        all_values = sheet.get_all_values()

        if not all_values or len(all_values) < 2:
            return jsonify({"message": "등록된 주문이 없습니다."}), 404

        headers, rows = all_values[0], all_values[1:]
        row_count = min(5, len(rows))  # 최대 5건

        # 최신 주문 상단 5건을 가져옴
        recent_orders = [(i + 2, row) for i, row in enumerate(rows[:row_count])]

        response = []
        for idx, (row_num, row_data) in enumerate(recent_orders, start=1):
            try:
                내용 = {
                    "번호": idx,
                    "행번호": row_num,
                    "회원명": row_data[headers.index("회원명")],
                    "제품명": row_data[headers.index("제품명")],
                    "가격": row_data[headers.index("제품가격")],
                    "PV": row_data[headers.index("PV")],
                    "주문일자": row_data[headers.index("주문일자")]
                }
                response.append(내용)
            except Exception:
                continue  # 누락된 필드는 건너뜀

        return jsonify({
            "message": f"📌 최근 주문 내역 {len(response)}건입니다. 삭제할 번호(1~{len(response)})를 선택해 주세요.",
            "주문목록": response
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    








# ✅ 주문 삭제 확인 API
@app.route("/delete_order_confirm", methods=["POST"])
def delete_order_confirm():
    try:
        data = request.get_json()
        번호들 = data.get("삭제번호", "").strip()

        if 번호들 in ["없음", "취소", ""]:
            return jsonify({"message": "삭제 요청이 취소되었습니다."}), 200

        # 숫자만 추출 → 중복 제거 및 정렬
        번호_리스트 = sorted(set(map(int, re.findall(r'\d+', 번호들))))

        sheet = get_product_order_sheet()
        all_values = sheet.get_all_values()

        if not all_values or len(all_values) < 2:
            return jsonify({"error": "삭제할 주문 데이터가 없습니다."}), 400

        headers, rows = all_values[0], all_values[1:]
        row_count = min(5, len(rows))
        recent_rows = [(i + 2) for i in range(row_count)]  # 실제 행 번호

        # 입력 유효성 검사
        if not 번호_리스트 or any(n < 1 or n > row_count for n in 번호_리스트):
            return jsonify({"error": f"삭제할 주문 번호는 1 ~ {row_count} 사이로 입력해 주세요."}), 400

        # 행 번호 역순으로 정렬 후 삭제
        삭제행목록 = [recent_rows[n - 1] for n in 번호_리스트]
        삭제행목록.sort(reverse=True)

        for row_num in 삭제행목록:
            sheet.delete_rows(row_num)

        return jsonify({
            "message": f"{', '.join(map(str, 번호_리스트))}번 주문이 삭제되었습니다.",
            "삭제행번호": 삭제행목록
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500













# 서버 실행
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)





