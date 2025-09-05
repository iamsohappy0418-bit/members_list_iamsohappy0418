import pathlib

# ✅ 잘못된 import 패턴들
TARGETS = [
     "format_memo_results",
    
    # 필요한 만큼 추가...
]

def find_imports_only():
    for file in pathlib.Path(".").rglob("*.py"):
        try:
            text = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"⚠️ Skipping (decode error): {file}")
            continue

        for target in TARGETS:
            if target in text:
                print(f"🔎 Found in: {file}  →  {target}")

if __name__ == "__main__":
    find_imports_only()




