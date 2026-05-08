"""test_export.py — export_.py 통합 테스트.

TDD: 이 파일은 export_.py 구현 전에 먼저 작성된다 (RED 상태).
GITSHUTTLE_HEADLESS=1 환경변수로 TUI 를 우회한다.
"""
from __future__ import annotations

import os
import subprocess

import pytest

from gitshuttle.git_ops import Commit, get_commits


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_commit(repo_path, filename: str, content: str, message: str):
    """테스트용 커밋을 tmp_git_repo 에 추가한다."""
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'GIT_TERMINAL_PROMPT': '0'}
    (repo_path / filename).write_text(content, encoding='utf-8')
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, encoding='utf-8', env=env)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_path, check=True, encoding='utf-8', env=env,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_export_creates_all_three_files(tmp_git_repo, tmp_path):
    """run_export 호출 시 bundle + sha256 + manifest 3개 파일이 생성되어야 한다."""
    from gitshuttle.export_ import run_export

    _add_commit(tmp_git_repo, "a.txt", "hello", "feat: first commit")
    commits = get_commits(tmp_git_repo)

    result = run_export(
        repo_path=tmp_git_repo,
        commits=commits,
        output_dir=tmp_path,
        branch="main",
    )

    assert result.bundle.exists(), "bundle 파일이 존재해야 합니다."
    assert result.sha256.exists(), ".sha256 파일이 존재해야 합니다."
    assert result.manifest.exists(), "manifest 파일이 존재해야 합니다."

    assert result.bundle.suffix == ".bundle"
    assert result.sha256.suffix == ".sha256" or result.sha256.name.endswith(".sha256")
    assert result.manifest.name.endswith("_manifest.txt")


def test_export_sha256_verifies(tmp_git_repo, tmp_path):
    """생성된 .sha256 파일로 verify() 호출 시 True 를 반환해야 한다."""
    from gitshuttle.export_ import run_export
    from gitshuttle.checksum import verify

    _add_commit(tmp_git_repo, "b.txt", "world", "feat: second commit")
    commits = get_commits(tmp_git_repo)

    result = run_export(
        repo_path=tmp_git_repo,
        commits=commits,
        output_dir=tmp_path,
        branch="main",
    )

    assert verify(result.bundle, result.sha256), "SHA-256 검증이 성공해야 합니다."


def test_export_empty_commits_raises(tmp_git_repo, tmp_path):
    """빈 커밋 목록으로 run_export 호출 시 ValueError 가 발생해야 한다."""
    from gitshuttle.export_ import run_export

    with pytest.raises(ValueError):
        run_export(
            repo_path=tmp_git_repo,
            commits=[],
            output_dir=tmp_path,
        )


def test_export_manifest_has_korean(tmp_git_repo, tmp_path):
    """한글 커밋 메시지가 manifest 파일에 정상 포함되어야 한다."""
    from gitshuttle.export_ import run_export

    _add_commit(tmp_git_repo, "kor.txt", "한글 내용", "feat: 한글 커밋 메시지")
    commits = get_commits(tmp_git_repo)

    result = run_export(
        repo_path=tmp_git_repo,
        commits=commits,
        output_dir=tmp_path,
        branch="main",
    )

    manifest_content = result.manifest.read_text(encoding='utf-8')
    assert "한글 커밋 메시지" in manifest_content


def test_export_result_dataclass_fields(tmp_git_repo, tmp_path):
    """ExportResult 는 bundle, sha256, manifest 속성을 가져야 한다."""
    from gitshuttle.export_ import run_export, ExportResult

    _add_commit(tmp_git_repo, "c.txt", "data", "fix: a fix")
    commits = get_commits(tmp_git_repo)

    result = run_export(
        repo_path=tmp_git_repo,
        commits=commits,
        output_dir=tmp_path,
    )

    assert isinstance(result, ExportResult)
    assert hasattr(result, 'bundle')
    assert hasattr(result, 'sha256')
    assert hasattr(result, 'manifest')


def test_export_output_dir_created_if_missing(tmp_git_repo, tmp_path):
    """output_dir 이 존재하지 않으면 자동으로 생성해야 한다."""
    from gitshuttle.export_ import run_export

    _add_commit(tmp_git_repo, "d.txt", "data2", "chore: add file")
    commits = get_commits(tmp_git_repo)

    new_dir = tmp_path / "nested" / "output"
    assert not new_dir.exists()

    result = run_export(
        repo_path=tmp_git_repo,
        commits=commits,
        output_dir=new_dir,
    )

    assert new_dir.exists()
    assert result.bundle.exists()
