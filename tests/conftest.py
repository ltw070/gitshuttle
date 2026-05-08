import subprocess
import os
import pytest
from pathlib import Path

from gitshuttle.git_ops import Commit


@pytest.fixture
def sample_commits():
    """manifest/export 테스트용 Commit 샘플 목록."""
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
            hash="bcd2345efg678901234567890123456789012345",
            short_hash="bcd2345",
            date="2026-04-28 09:00:00 +0900",
            author="Bob",
            message="fix: 인코딩 수정",
            files_changed=1,
        ),
    ]


def _git_env() -> dict:
    """테스트용 git 환경 변수 딕셔너리."""
    return {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'GIT_TERMINAL_PROMPT': '0'}


@pytest.fixture
def tmp_git_repo(tmp_path):
    env = _git_env()
    subprocess.run(
        ["git", "init", str(tmp_path)],
        check=True,
        encoding='utf-8',
        env=env,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        encoding='utf-8',
        env=env,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        encoding='utf-8',
        env=env,
    )
    (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        check=True,
        encoding='utf-8',
        env=env,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        encoding='utf-8',
        env=env,
    )
    return tmp_path


@pytest.fixture
def tmp_git_repo_with_korean(tmp_git_repo):
    """tmp_git_repo에 한글 커밋 메시지 커밋을 추가한다."""
    env = _git_env()
    (tmp_git_repo / "korean.txt").write_text("한글 내용", encoding='utf-8')
    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_git_repo,
        check=True,
        encoding='utf-8',
        env=env,
    )
    subprocess.run(
        ["git", "commit", "-m", "feat: 한글 커밋 메시지 테스트"],
        cwd=tmp_git_repo,
        check=True,
        encoding='utf-8',
        env=env,
    )
    return tmp_git_repo
