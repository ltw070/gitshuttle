import subprocess
import os
import pytest
from pathlib import Path


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
