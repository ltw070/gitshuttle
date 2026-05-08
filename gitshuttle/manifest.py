"""manifest.py — 커밋 목록 요약 파일 생성.

생성 파일: shuttle_YYMMDD_manifest.txt
인코딩: UTF-8 (BOM 없음)
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .git_ops import Commit


def create_manifest(
    commits: list[Commit],
    output_path: Path | str,
    branch: str = "unknown",
) -> Path:
    """커밋 목록 요약 파일을 생성한다.

    형식:
      GitShuttle Manifest
      생성일시: YYYY-MM-DD HH:MM:SS
      브랜치: <branch>
      커밋 수: <n>

      <short_hash>  <date>  <author>  <message>  (<files> files)

    Args:
        commits:      포함할 Commit 목록.
        output_path:  출력 파일 경로 (디렉터리가 없으면 자동 생성).
        branch:       브랜치 이름 (헤더에 기록).

    Returns:
        생성된 파일의 Path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = [
        "GitShuttle Manifest",
        f"생성일시: {now_str}",
        f"브랜치: {branch}",
        f"커밋 수: {len(commits)}",
        "",
    ]

    for commit in commits:
        line = (
            f"{commit.short_hash}  "
            f"{commit.date}  "
            f"{commit.author}  "
            f"{commit.message}  "
            f"({commit.files_changed} files)"
        )
        lines.append(line)

    content = "\n".join(lines) + "\n"

    output_path.write_text(content, encoding='utf-8')

    return output_path
