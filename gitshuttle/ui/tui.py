"""tui.py — Textual 기반 커밋 선택 TUI.

headless 테스트 지원:
  GITSHUTTLE_HEADLESS=1 환경변수 설정 시 전체 커밋을 선택한 것으로 반환한다.

Textual import 는 이 파일 내부에서만 수행하므로
Textual 이 설치되지 않은 환경에서도 다른 모듈을 import 할 수 있다.
"""
from __future__ import annotations

import os

from gitshuttle.git_ops import Commit


def select_commits_tui(
    commits: list[Commit],
    already_imported: set[str] | None = None,
) -> list[Commit]:
    """TUI 로 커밋을 선택하여 반환한다.

    Args:
        commits:          선택 대상 Commit 목록 (최신순).
        already_imported: 이미 import 된 커밋 hash set.
                          해당 커밋은 '[imported]' 태그로 표시된다.

    Returns:
        사용자가 선택한 Commit 목록.
        GITSHUTTLE_HEADLESS=1 인 경우 전체 커밋 반환.
    """
    if already_imported is None:
        already_imported = set()

    # Headless 모드 (테스트/CI 용)
    if os.environ.get("GITSHUTTLE_HEADLESS") == "1":
        return list(commits)

    # Textual TUI 실행
    from gitshuttle.ui._textual_app import CommitSelectorApp

    app = CommitSelectorApp(commits, already_imported)
    return app.run_selection()
