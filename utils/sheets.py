# utils/sheets.py

import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# 🔄 .env 파일 로드 (필요한 경우)
load_dotenv()

# 🔐 인증 클라이언트 생성
def get_gspread_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    return gspread.authorize(creds)

# 📄 제품주문 시트 가져오기
def get_order_sheet():
    client = get_gspread_client()
    sheet = client.open(os.getenv("GOOGLE_SHEET_TITLE"))
    return sheet.worksheet("제품주문")

# 📄 DB 시트에서 회원번호/휴대폰번호 조회
def get_member_info(member_name):
    client = get_gspread_client()
    db_sheet = client.open(os.getenv("GOOGLE_SHEET_TITLE")).worksheet("DB")
    records = db_sheet.get_all_records()
    for row in records:
        if row.get("회원명") == member_name:
            return row.get("회원번호", ""), row.get("휴대폰번호", "")
    return "", ""


# ✅ 제품주문 시트 가져오기
def get_order_sheet():
    client = get_gspread_client()
    sheet = client.open(os.getenv("GOOGLE_SHEET_TITLE"))
    return sheet.worksheet("제품주문")

# ✅ 회원번호, 휴대폰번호 가져오기
def get_member_info(member_name):
    client = get_gspread_client()
    db_sheet = client.open(os.getenv("GOOGLE_SHEET_TITLE")).worksheet("DB")
    records = db_sheet.get_all_records()
    for row in records:
        if row.get("회원명") == member_name:
            return row.get("회원번호", ""), row.get("휴대폰번호", "")
    return "", ""
