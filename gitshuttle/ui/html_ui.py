"""html_ui.py — Self-contained HTML 생성 및 selection.json 파싱.

제약:
  - 외부 CDN/URL 절대 포함 금지 (http://, https://)
  - 순수 HTML + CSS + JS 만 사용
  - 인코딩: utf-8 (BOM 없음)
"""
from __future__ import annotations

import json
from pathlib import Path

from gitshuttle.git_ops import Commit


def generate_html(
    commits: list[Commit],
    output_path: Path | str,
    already_imported: set[str] | None = None,
) -> Path:
    """Self-contained HTML 파일을 생성한다.

    Args:
        commits:          커밋 목록 (최신순).
        output_path:      출력 파일 경로.
        already_imported: 이미 import 된 커밋 short_hash set.

    Returns:
        생성된 파일 경로.

    인코딩: utf-8 (BOM 없음).
    외부 네트워크 참조 없음.
    """
    if already_imported is None:
        already_imported = set()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows_html = []
    for commit in commits:
        imported_label = " [imported]" if commit.short_hash in already_imported else ""
        checked = "" if commit.short_hash in already_imported else "checked"
        # HTML 이스케이프 (기본 처리)
        message = _escape_html(commit.message)
        author = _escape_html(commit.author)
        date = _escape_html(commit.date)
        rows_html.append(
            f'<tr>'
            f'<td><input type="checkbox" class="cb" value="{commit.short_hash}" {checked}></td>'
            f'<td><code>{commit.short_hash}</code></td>'
            f'<td>{date}</td>'
            f'<td>{author}</td>'
            f'<td>{message}{_escape_html(imported_label)}</td>'
            f'<td>{commit.files_changed}</td>'
            f'</tr>'
        )

    rows_joined = "\n".join(rows_html)

    html_content = f"""\
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GitShuttle — 커밋 선택</title>
<style>
  body {{ font-family: monospace; margin: 20px; background: #1e1e1e; color: #d4d4d4; }}
  h1 {{ color: #4ec9b0; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #444; padding: 6px 10px; text-align: left; }}
  th {{ background: #333; color: #9cdcfe; }}
  tr:hover {{ background: #2d2d30; }}
  input[type=checkbox] {{ cursor: pointer; width: 16px; height: 16px; }}
  .btn {{ margin-top: 16px; padding: 10px 24px; background: #0e639c; color: white;
          border: none; cursor: pointer; font-size: 14px; border-radius: 4px; }}
  .btn:hover {{ background: #1177bb; }}
  .btn-all {{ background: #4e4e4e; margin-right: 8px; }}
  .info {{ margin-bottom: 10px; color: #888; }}
  code {{ color: #9cdcfe; }}
</style>
</head>
<body>
<h1>GitShuttle — 커밋 선택</h1>
<div class="info">체크박스로 export 할 커밋을 선택한 뒤 [Export] 버튼을 클릭하세요.</div>
<div>
  <button class="btn btn-all" onclick="selectAll(true)">전체 선택</button>
  <button class="btn btn-all" onclick="selectAll(false)">전체 해제</button>
</div>
<br>
<table>
  <thead>
    <tr>
      <th>선택</th>
      <th>해시</th>
      <th>날짜</th>
      <th>작성자</th>
      <th>메시지</th>
      <th>변경 파일</th>
    </tr>
  </thead>
  <tbody>
{rows_joined}
  </tbody>
</table>
<br>
<button class="btn" onclick="exportSelection()">Export (selection.json 다운로드)</button>

<script>
function selectAll(state) {{
  document.querySelectorAll('.cb').forEach(function(cb) {{ cb.checked = state; }});
}}

function exportSelection() {{
  var selected = [];
  document.querySelectorAll('.cb:checked').forEach(function(cb) {{
    selected.push(cb.value);
  }});
  var data = JSON.stringify({{ "selected": selected }}, null, 2);
  var blob = new Blob([data], {{ type: 'application/json' }});
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download = 'selection.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}}
</script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path


def parse_selection_json(
    json_path: Path | str,
    original_commits: list[Commit],
) -> list[Commit]:
    """selection.json 에서 선택된 해시 목록으로 커밋을 필터링한다.

    Args:
        json_path:        selection.json 파일 경로.
                          형식: {"selected": ["abc1234", ...]}
        original_commits: 전체 커밋 목록 (short_hash 기준 매칭).

    Returns:
        선택된 Commit 목록 (원본 순서 유지).
    """
    json_path = Path(json_path)

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    selected_hashes: set[str] = set(data.get("selected", []))
    commit_map: dict[str, Commit] = {c.short_hash: c for c in original_commits}

    return [commit_map[h] for h in selected_hashes if h in commit_map]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _escape_html(text: str) -> str:
    """기본 HTML 특수문자를 이스케이프한다."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
