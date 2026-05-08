"""prompt_ui.py — InquirerPy 멀티셀렉트 UI.

InquirerPy import 는 함수 내부에서만 수행한다.
→ 설치되지 않은 환경에서도 이 모듈을 import 할 수 있다.

헤드리스 모드:
  GITSHUTTLE_HEADLESS=1 환경변수 설정 시 전체 커밋을 반환한다.
  (테스트/CI 환경에서 인터랙티브 UI 우회용)
"""
from __future__ import annotations

import os

from gitshuttle.git_ops import Commit


def select_commits_prompt(
    commits: list[Commit],
    already_imported: set[str] | None = None,
) -> list[Commit]:
    """InquirerPy 체크박스 멀티셀렉트로 커밋을 선택한다.

    Args:
        commits:          선택 대상 Commit 목록 (최신순).
        already_imported: 이미 import 된 커밋 short_hash set.

    Returns:
        사용자가 선택한 Commit 목록.
        GITSHUTTLE_HEADLESS=1 인 경우 전체 커밋 반환.
    """
    if already_imported is None:
        already_imported = set()

    # Headless 모드 (테스트/CI 용) — 인터랙티브 UI 건너뜀
    if os.environ.get("GITSHUTTLE_HEADLESS") == "1":
        return list(commits)

    # InquirerPy 는 인터랙티브 실행 시에만 import
    try:
        from InquirerPy import inquirer
    except ImportError as exc:
        raise RuntimeError(
            "InquirerPy 가 설치되지 않았습니다. "
            "`pip install InquirerPy` 로 설치하세요."
        ) from exc

    choices = []
    for commit in commits:
        imported_label = " [imported]" if commit.short_hash in already_imported else ""
        label = (
            f"[{commit.short_hash}] {commit.date[:10]}  "
            f"{commit.author:<12}  {commit.message}{imported_label}"
        )
        choices.append(
            {
                "name": label,
                "value": commit.short_hash,
                "enabled": commit.short_hash not in already_imported,
            }
        )

    selected_hashes: list[str] = inquirer.checkbox(
        message="export 할 커밋을 선택하세요 (Space 선택, Enter 확인):",
        choices=choices,
    ).execute()

    commit_map: dict[str, Commit] = {c.short_hash: c for c in commits}
    return [commit_map[h] for h in selected_hashes if h in commit_map]
