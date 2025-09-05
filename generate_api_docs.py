import os
import re
import ast
import pathlib

DOCS_DIR = "docs"
DOC_FILE = os.path.join(DOCS_DIR, "DEVELOPER_AUTO_GUIDE.md")

# Flask 라우트 정규식 (경로와 함수명 추출)
ROUTE_PATTERN = re.compile(
    r'@app\.route\(["\']([^"\']+)["\'].*?\)\s*def\s+(\w+)',
    re.DOTALL
)

def extract_routes_with_docstrings(py_file: pathlib.Path):
    """특정 .py 파일에서 라우트 경로, 함수명, docstring 추출"""
    try:
        code = py_file.read_text(encoding="utf-8")
    except Exception:
        return []

    matches = ROUTE_PATTERN.findall(code)

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    func_docs = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            func_docs[node.name] = ast.get_docstring(node) or ""

    routes = []
    for path, func in matches:
        routes.append({
            "file": str(py_file),
            "path": path,
            "func": func,
            "doc": func_docs.get(func, "").strip()
        })
    return routes

def generate_markdown(all_routes):
    """라우트 + docstring을 Markdown으로 변환"""
    lines = []
    lines.append("# 📑 API Route 자동 문서 (docstring 기반)")
    lines.append("")
    lines.append("이 문서는 프로젝트 전체 `.py` 파일에서 추출한 Flask 라우트와 docstring을 정리한 것입니다.")
    lines.append("")
    lines.append("| 파일(File) | 경로(Path) | 함수명(Function) | 설명 (docstring) |")
    lines.append("|------------|------------|-----------------|------------------|")
    for r in all_routes:
        desc = r['doc'].split("\n")[0] if r['doc'] else "⚠️ 설명 없음"
        lines.append(f"| `{r['file']}` | `{r['path']}` | `{r['func']}` | {desc} |")
    lines.append("")
    lines.append("## 📄 상세 Docstring")
    for r in all_routes:
        lines.append(f"### `{r['path']}` → `{r['func']}` ({r['file']})")
        if r['doc']:
            lines.append("```text")
            lines.append(r['doc'])
            lines.append("```")
        else:
            lines.append("_⚠️ docstring 없음_")
        lines.append("")
    return "\n".join(lines)

def main():
    os.makedirs(DOCS_DIR, exist_ok=True)

    # 전체 프로젝트에서 모든 .py 파일 탐색
    py_files = list(pathlib.Path(".").rglob("*.py"))

    all_routes = []
    for file in py_files:
        all_routes.extend(extract_routes_with_docstrings(file))

    md_content = generate_markdown(all_routes)
    with open(DOC_FILE, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"✅ 자동 문서 생성 완료: {DOC_FILE}")
    print(f"📌 총 {len(all_routes)} 개 라우트가 문서화되었습니다.")

if __name__ == "__main__":
    main()
