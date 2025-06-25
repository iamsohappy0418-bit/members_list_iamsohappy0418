import os
import sys
import subprocess
import shutil
from pathlib import Path

# ✅ .git 디렉토리 강제 삭제 함수
def safe_rmtree(path):
    try:
        shutil.rmtree(path)
    except PermissionError:
        print("❌ 삭제 실패: 관리자 권한으로 실행하거나 VSCode를 완전히 종료하고 다시 시도하세요.")
    except Exception as e:
        print(f"⚠️ 기타 오류 발생: {e}")

# ✅ 환경 변수 로드 함수
def load_env(path):
    env_vars = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                key, val = line.strip().split("=", 1)
                env_vars[key.strip()] = val.strip()
    return env_vars

# ✅ PC 환경 선택
def select_pc_env():
    print("\n==============================")
    print("💻 사용할 PC 환경을 선택하세요:")
    print("[1] pc_home")
    print("[2] pc_office")
    print("[3] pc_pohang")
    print("[4] pc_daejeon")
    print("==============================")
    choice = input("번호를 입력하세요 (1~4): ").strip()
    pc_map = {"1": "home", "2": "office", "3": "pohang", "4": "daejeon"}
    return f"pish_pc_{pc_map.get(choice, 'home')}.env"

# ✅ 사용자 선택
def select_user(env_vars):
    print("\n==============================")
    print("🔐 Git 사용자 계정을 선택하세요:")
    print(f"[1] {env_vars.get('USER1_NAME')}")
    print(f"[2] {env_vars.get('USER2_NAME')}")
    print(f"[3] {env_vars.get('USER3_NAME')}")
    print("==============================")
    choice = input("번호를 입력하세요 (1~3): ").strip()
    return {
        "name": env_vars.get(f"USER{choice}_NAME"),
        "email": env_vars.get(f"USER{choice}_EMAIL"),
        "ssh": env_vars.get(f"USER{choice}_SSH"),
        "remote": env_vars.get(f"USER{choice}_REMOTE")
    }

def main():
    base_dir = Path(__file__).parent  # git_auto_push 폴더 기준
    env_file_name = select_pc_env()
    env_file_path = base_dir / env_file_name

    if not env_file_path.exists():
        print(f"❌ .env 파일이 존재하지 않습니다: {env_file_path}")
        return

    env_vars = load_env(env_file_path)
    user = select_user(env_vars)

    # ✅ GIT_SSH_COMMAND 환경변수 설정
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = f'ssh -i "{user["ssh"]}"'

    # ✅ 기존 .git 폴더 삭제
    git_dir = ".git"
    if os.path.exists(git_dir):
        print("🧹 기존 Git 설정 초기화")
        safe_rmtree(git_dir)
    else:
        print("✅ .git 폴더가 존재하지 않습니다. 초기화 생략.")

    # ✅ Git 초기화 및 설정
    subprocess.run(["git", "init"], shell=True)
    # ✅ Git 초기화 후 main 브랜치 생성 및 전환
    subprocess.run(["git", "checkout", "-B", "main"], shell=True)
    subprocess.run(["git", "branch", "-M", "main"], shell=True)  # <- 이 줄 추가
    subprocess.run(["git", "config", "user.name", user["name"]], shell=True)
    subprocess.run(["git", "config", "user.email", user["email"]], shell=True)
    subprocess.run(["git", "remote", "add", "origin", user["remote"]], shell=True)

  
    # ✅ git pull 실행 (unrelated histories 허용)
    print("\n📥 git pull 실행 중...")
    pull_result = subprocess.run(
        ["git", "pull", "origin", "main", "--allow-unrelated-histories"],
        shell=True,
        env=env
    )

    if pull_result.returncode != 0:
        print("❌ 병합 실패: 수동 병합이 필요합니다.")
        return



    # ✅ 커밋 메시지 입력
    commit_msg = input("\n💬 커밋 메시지를 입력하세요 (기본값: 자동 커밋): ").strip()
    if not commit_msg:
        commit_msg = "자동 커밋"

    # ✅ Git add, commit
    print("🚀 Git 커밋 작업 시작...")
    subprocess.run(["git", "add", "."], shell=True)

    # 변경된 파일이 있을 경우만 커밋
    commit_result = subprocess.run(["git", "diff", "--cached", "--quiet"], shell=True)
    if commit_result.returncode != 0:
        subprocess.run(["git", "commit", "-m", commit_msg], shell=True)
        print("✅ 변경 사항이 커밋되었습니다.")
    else:
        print("ℹ️ 커밋할 변경 사항이 없습니다.")

    print("✅ Git 초기화 및 커밋 완료! (Push는 제외됨)")
    
    # ✅ 사용자 SSH 키로 push 실행
    print("📤 push 실행 중...")
    push_env = os.environ.copy()
    push_env["GIT_SSH_COMMAND"] = f'ssh -i "{user["ssh"]}"'
    subprocess.run(["git", "push", "-u", "origin", "main"], shell=True, env=push_env)

    print("✅ Git push 완료!")

if __name__ == "__main__":
    main()
