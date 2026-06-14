"""Tests for gitshuttle.bundle — Sprint 1.

RED phase: these tests will fail until implementation is in place.
"""
import subprocess
import os
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_bundle(tmp_git_repo, tmp_path):
    """create_bundle(repo_path, commits, output_dir) → Path 반환.

    파일이 실제 생성되고 git bundle verify를 통과해야 한다.
    """
    from gitshuttle.git_ops import get_commits
    from gitshuttle.bundle import create_bundle, verify_bundle

    commits = get_commits(tmp_git_repo, branch="HEAD")
    assert len(commits) >= 1

    bundle_path = create_bundle(tmp_git_repo, commits, tmp_path)

    assert isinstance(bundle_path, Path)
    assert bundle_path.exists()
    assert bundle_path.suffix == ".bundle"
    # git bundle verify로 무결성 확인
    assert verify_bundle(bundle_path), "bundle verify 실패"


def test_create_bundle_custom_filename(tmp_git_repo, tmp_path):
    """filename 인자로 출력 파일명을 지정할 수 있어야 한다."""
    from gitshuttle.git_ops import get_commits
    from gitshuttle.bundle import create_bundle

    commits = get_commits(tmp_git_repo, branch="HEAD")
    bundle_path = create_bundle(tmp_git_repo, commits, tmp_path, filename="custom.bundle")

    assert bundle_path.name == "custom.bundle"
    assert bundle_path.exists()


def test_create_bundle_default_filename_format(tmp_git_repo, tmp_path):
    """filename 미지정 시 shuttle_YYMMDD.bundle 형식이어야 한다."""
    from gitshuttle.git_ops import get_commits
    from gitshuttle.bundle import create_bundle

    commits = get_commits(tmp_git_repo, branch="HEAD")
    bundle_path = create_bundle(tmp_git_repo, commits, tmp_path)

    import re
    assert re.match(r"^shuttle_\d{6}\.bundle$", bundle_path.name), (
        f"기본 파일명 형식 불일치: {bundle_path.name}"
    )


def test_create_bundle_empty_commits_raises(tmp_git_repo, tmp_path):
    """커밋 목록이 비어있으면 ValueError가 발생해야 한다."""
    from gitshuttle.bundle import create_bundle

    with pytest.raises(ValueError, match="commits"):
        create_bundle(tmp_git_repo, [], tmp_path)


def test_verify_bundle_valid(tmp_git_repo, tmp_path):
    """올바른 bundle은 verify_bundle → True를 반환해야 한다."""
    from gitshuttle.git_ops import get_commits
    from gitshuttle.bundle import create_bundle, verify_bundle

    commits = get_commits(tmp_git_repo, branch="HEAD")
    bundle_path = create_bundle(tmp_git_repo, commits, tmp_path)

    assert verify_bundle(bundle_path) is True


def test_verify_bundle_uses_repo_path(tmp_path, monkeypatch):
    """verify_bundle(repo_path=...)는 지정 repo를 기준으로 git bundle verify를 실행한다."""
    import gitshuttle.bundle as bundle_module
    from gitshuttle.bundle import verify_bundle

    bundle_path = tmp_path / "test.bundle"
    bundle_path.write_bytes(b"fake bundle content")
    repo_path = tmp_path / "target_repo"
    repo_path.mkdir()
    captured = {}

    def fake_run(args, cwd=None, capture_output=True, encoding="utf-8", env=None):
        captured["args"] = args
        captured["cwd"] = cwd
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(bundle_module.subprocess, "run", fake_run)

    assert verify_bundle(bundle_path, repo_path=repo_path) is True
    assert captured["args"] == ["git", "bundle", "verify", str(bundle_path)]
    assert captured["cwd"] == repo_path


def test_verify_bundle_invalid(tmp_path):
    """존재하지 않는 파일 → verify_bundle → False를 반환해야 한다."""
    from gitshuttle.bundle import verify_bundle

    nonexistent = tmp_path / "nonexistent.bundle"
    assert verify_bundle(nonexistent) is False


def test_verify_bundle_corrupted(tmp_path):
    """손상된 bundle 파일 → verify_bundle → False를 반환해야 한다."""
    from gitshuttle.bundle import verify_bundle

    corrupted = tmp_path / "corrupted.bundle"
    corrupted.write_bytes(b"this is not a valid git bundle content!!!")

    assert verify_bundle(corrupted) is False
