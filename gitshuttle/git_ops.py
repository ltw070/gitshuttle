"""git_ops.py — git 서브프로세스 래퍼.

모든 subprocess 호출은 encoding='utf-8', env에 PYTHONIOENCODING='utf-8' 포함.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Commit:
    hash: str           # full 40-char SHA-1
    short_hash: str     # 7~10 char abbreviated hash
    date: str           # ISO 8601 author date
    author: str         # author name
    message: str        # subject (first line)
    files_changed: int  # number of files changed in this commit


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _git_env() -> dict[str, str]:
    """git 서브프로세스용 환경 변수 딕셔너리 반환."""
    return {
        **os.environ,
        'PYTHONIOENCODING': 'utf-8',
        'GIT_TERMINAL_PROMPT': '0',
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_git(args: list[str], cwd: Path | str | None = None) -> str:
    """git 명령을 실행하고 stdout 문자열을 반환한다.

    실패 시(returncode != 0) RuntimeError 를 발생시킨다.
    encoding='utf-8' 필수 — 한글 출력 깨짐 방지.
    """
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        encoding='utf-8',
        env=_git_env(),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (code {result.returncode}):\n{result.stderr}"
        )
    return result.stdout


def check_git_version() -> str:
    """설치된 git 버전 문자열을 반환한다.

    버전이 2.37 미만이면 RuntimeError 를 발생시킨다.

    Returns:
        예: "2.45.0" 또는 "2.45.0.windows.1"
    """
    output = run_git(["--version"])
    # 출력 예시: "git version 2.45.0.windows.1"
    raw = output.strip()
    # "git version " 접두사 제거
    version_str = raw.removeprefix("git version ").strip()

    # 버전 비교: major.minor 부분만 추출
    parts = version_str.split(".")
    try:
        major = int(parts[0])
        minor = int(parts[1])
    except (IndexError, ValueError) as exc:
        raise RuntimeError(f"git 버전 파싱 실패: {raw!r}") from exc

    if (major, minor) < (2, 37):
        raise RuntimeError(
            f"Git 2.37 이상 필요. 현재 설치 버전: {version_str}"
        )

    return version_str


def get_commits(
    repo_path: Path | str,
    branch: str = "HEAD",
) -> list[Commit]:
    """지정 브랜치의 커밋 목록을 반환한다.

    null 바이트(\\x00) 구분자를 사용하므로 커밋 메시지 내
    특수문자·줄바꿈이 있어도 안전하게 파싱된다.

    반환 순서: 최신 커밋이 index 0 (git log 기본 순서).
    """
    repo_path = Path(repo_path)

    # %x00 = null byte separator
    # format: hash\x00short_hash\x00date\x00author\x00subject\x1e
    # \x1e (RS, Record Separator) 로 레코드를 구분
    log_format = "%H%x00%h%x00%ai%x00%an%x00%s%x1e"
    raw = run_git(
        ["log", branch, f"--format={log_format}"],
        cwd=repo_path,
    )

    commits: list[Commit] = []
    # 레코드 분리 (마지막 빈 항목 제거)
    records = [r for r in raw.split("\x1e") if r.strip()]

    for record in records:
        parts = record.strip().split("\x00")
        if len(parts) < 5:
            continue
        full_hash, short_hash, date, author, message = (
            parts[0], parts[1], parts[2], parts[3], parts[4]
        )

        # 변경 파일 수 계산
        files_changed = _count_files_changed(repo_path, full_hash)

        commits.append(Commit(
            hash=full_hash,
            short_hash=short_hash,
            date=date,
            author=author,
            message=message,
            files_changed=files_changed,
        ))

    return commits


def _count_files_changed(repo_path: Path, commit_hash: str) -> int:
    """특정 커밋에서 변경된 파일 수를 반환한다.

    루트 커밋(부모 없음)은 --root 플래그로 처리한다.
    """
    try:
        # 먼저 부모 커밋이 있는지 확인
        parent_output = run_git(
            ["rev-list", "--parents", "-n", "1", commit_hash],
            cwd=repo_path,
        )
        # 출력 예: "abc123 def456" (자신 해시 + 부모 해시)
        parts = parent_output.strip().split()
        is_root = len(parts) == 1  # 부모 없음 = 루트 커밋

        if is_root:
            # 루트 커밋: --root 플래그 사용
            output = run_git(
                ["diff-tree", "--root", "--no-commit-id", "-r", "--name-only", commit_hash],
                cwd=repo_path,
            )
        else:
            # 일반 커밋: 기본 diff-tree
            output = run_git(
                ["diff-tree", "--no-commit-id", "-r", "--name-only", commit_hash],
                cwd=repo_path,
            )

        files = [f for f in output.strip().splitlines() if f]
        return len(files)
    except RuntimeError:
        # diff-tree 실패 시 0 반환
        return 0
