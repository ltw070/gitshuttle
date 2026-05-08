"""test_prompt_ui.py — prompt_ui.py 단위 테스트.

GITSHUTTLE_HEADLESS=1 환경변수로 InquirerPy UI를 우회한다.
"""
from __future__ import annotations

import os

import pytest

from gitshuttle.git_ops import Commit


def _sample_commits() -> list[Commit]:
    return [
        Commit(
            hash="abc1234def5678901234567890123456789012345",
            short_hash="abc1234",
            date="2026-05-01 10:00:00 +0900",
            author="Alice",
            message="feat: 로그인 구현",
            files_changed=3,
        ),
        Commit(
            hash="bcd2345efg678901234567890123456789012346",
            short_hash="bcd2345",
            date="2026-04-28 09:00:00 +0900",
            author="Bob",
            message="fix: 인코딩 수정",
            files_changed=1,
        ),
    ]


@pytest.fixture(autouse=True)
def headless(monkeypatch):
    monkeypatch.setenv("GITSHUTTLE_HEADLESS", "1")


def test_select_commits_prompt_returns_all_in_headless():
    """헤드리스 모드에서 전체 커밋을 반환한다."""
    from gitshuttle.ui.prompt_ui import select_commits_prompt

    commits = _sample_commits()
    result = select_commits_prompt(commits)

    assert len(result) == len(commits)


def test_select_commits_prompt_empty_list():
    """빈 커밋 목록은 빈 리스트를 반환한다."""
    from gitshuttle.ui.prompt_ui import select_commits_prompt

    result = select_commits_prompt([])
    assert result == []


def test_select_commits_prompt_preserves_order():
    """반환 순서가 입력 순서와 같다."""
    from gitshuttle.ui.prompt_ui import select_commits_prompt

    commits = _sample_commits()
    result = select_commits_prompt(commits)

    assert [c.short_hash for c in result] == [c.short_hash for c in commits]


def test_select_commits_prompt_already_imported_accepted():
    """already_imported 인자를 받아도 헤드리스에서는 전체 반환한다."""
    from gitshuttle.ui.prompt_ui import select_commits_prompt

    commits = _sample_commits()
    result = select_commits_prompt(commits, already_imported={"abc1234"})

    assert len(result) == len(commits)
