"""Tests for gitshuttle.git_ops — Sprint 1."""
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_get_commits_returns_list(tmp_git_repo):
    """get_commits(repo_path, branch) → 커밋 목록 반환.

    각 항목은 hash, short_hash, date, author, message, files_changed 필드를 가져야 한다.
    """
    from gitshuttle.git_ops import get_commits, Commit

    commits = get_commits(tmp_git_repo, branch="HEAD")

    assert isinstance(commits, list)
    assert len(commits) >= 1

    c = commits[0]
    assert isinstance(c, Commit)
    assert len(c.hash) == 40        # full SHA-1
    assert len(c.short_hash) >= 7
    assert c.date                   # non-empty string
    assert c.author                 # non-empty string
    assert c.message                # non-empty string
    assert isinstance(c.files_changed, int)
    assert c.files_changed >= 0


def test_get_commits_korean_message(tmp_git_repo_with_korean):
    """한글 커밋 메시지가 깨지지 않고 파싱되어야 한다."""
    from gitshuttle.git_ops import get_commits

    commits = get_commits(tmp_git_repo_with_korean, branch="HEAD")

    # 가장 최신 커밋이 한글 메시지여야 한다
    messages = [c.message for c in commits]
    assert any("한글" in m for m in messages), (
        f"한글 메시지를 찾을 수 없음. 실제 메시지 목록: {messages}"
    )


def test_check_git_version():
    """check_git_version() → 버전 문자열 반환. 2.37 미만이면 RuntimeError."""
    from gitshuttle.git_ops import check_git_version

    version = check_git_version()

    assert isinstance(version, str)
    # 형식: "2.xx.x" 또는 "2.xx.x.windows.x"
    assert version[0].isdigit()

    parts = version.split(".")
    major = int(parts[0])
    minor = int(parts[1])
    assert (major, minor) >= (2, 37), (
        f"Git 버전이 2.37 미만: {version}"
    )


def test_run_git_basic(tmp_git_repo):
    """run_git(['status'], cwd=repo_path) → stdout 문자열 반환."""
    from gitshuttle.git_ops import run_git

    output = run_git(["status"], cwd=tmp_git_repo)

    assert isinstance(output, str)
    assert len(output) > 0


def test_run_git_invalid_command_raises(tmp_git_repo):
    """잘못된 git 명령은 RuntimeError를 발생시켜야 한다."""
    from gitshuttle.git_ops import run_git

    with pytest.raises(RuntimeError):
        run_git(["this-command-does-not-exist"], cwd=tmp_git_repo)


def test_get_commits_files_changed(tmp_git_repo):
    """files_changed 값이 실제 변경 파일 수와 일치해야 한다.

    init 커밋은 README.md 1개 파일이므로 files_changed == 1이어야 한다.
    """
    from gitshuttle.git_ops import get_commits

    commits = get_commits(tmp_git_repo, branch="HEAD")

    # init 커밋 (가장 오래된 커밋)
    init_commit = commits[-1]
    assert init_commit.files_changed == 1, (
        f"init 커밋 files_changed 예상 1, 실제 {init_commit.files_changed}"
    )


def test_get_commits_limit_reads_recent_only(tmp_git_repo):
    """limit 옵션은 최신 N개 커밋만 반환한다."""
    import os
    import subprocess
    from gitshuttle.git_ops import get_commits

    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "GIT_TERMINAL_PROMPT": "0"}
    for index in range(3):
        (tmp_git_repo / f"file{index}.txt").write_text(str(index), encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_git_repo, check=True, env=env)
        subprocess.run(
            ["git", "commit", "-m", f"commit {index}"],
            cwd=tmp_git_repo,
            check=True,
            env=env,
        )

    commits = get_commits(tmp_git_repo, branch="HEAD", limit=2)

    assert [commit.message for commit in commits] == ["commit 2", "commit 1"]
