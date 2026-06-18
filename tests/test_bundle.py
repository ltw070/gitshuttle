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


def test_create_bundle_full_scope_is_self_contained(tmp_git_repo, tmp_path):
    """scope=full 은 최신 일부 커밋만 선택해도 prerequisite 없는 bundle을 만든다."""
    from gitshuttle.git_ops import get_commits
    from gitshuttle.bundle import create_bundle, verify_bundle_detailed

    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "GIT_TERMINAL_PROMPT": "0"}
    (tmp_git_repo / "feature.txt").write_text("feature", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo, check=True, env=env)
    subprocess.run(
        ["git", "commit", "-m", "feat: feature"],
        cwd=tmp_git_repo,
        check=True,
        env=env,
    )
    empty_repo = tmp_path / "empty"
    subprocess.run(["git", "init", str(empty_repo)], check=True, env=env)

    commits = get_commits(tmp_git_repo, branch="HEAD")
    range_bundle = create_bundle(
        tmp_git_repo,
        [commits[0]],
        tmp_path,
        filename="range.bundle",
    )
    full_bundle = create_bundle(
        tmp_git_repo,
        [commits[0]],
        tmp_path,
        filename="full.bundle",
        scope="full",
    )

    assert verify_bundle_detailed(range_bundle, repo_path=empty_repo).valid is False
    assert verify_bundle_detailed(full_bundle, repo_path=empty_repo).valid is True


def test_create_bundle_with_base_ref_is_self_contained_and_marks_base(tmp_git_repo, tmp_path):
    """base_refs bundle은 빈 target에서도 검증되고 base metadata ref를 담는다."""
    from gitshuttle.git_ops import get_commits
    from gitshuttle.bundle import create_bundle, verify_bundle_detailed

    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "GIT_TERMINAL_PROMPT": "0"}
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_git_repo,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    ).stdout.strip()
    (tmp_git_repo / "feature.txt").write_text("feature", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo, check=True, env=env)
    subprocess.run(
        ["git", "commit", "-m", "feat: feature"],
        cwd=tmp_git_repo,
        check=True,
        env=env,
    )
    empty_repo = tmp_path / "empty"
    subprocess.run(["git", "init", str(empty_repo)], check=True, env=env)

    commits = get_commits(tmp_git_repo, branch=f"{base_sha}..HEAD")
    bundle_path = create_bundle(
        tmp_git_repo,
        commits,
        tmp_path,
        filename="base_delta.bundle",
        base_refs=[base_sha],
    )
    list_heads = subprocess.run(
        ["git", "bundle", "list-heads", str(bundle_path)],
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    ).stdout
    leaked_refs = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname)", "refs/gitshuttle/base"],
        cwd=tmp_git_repo,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    ).stdout

    assert verify_bundle_detailed(bundle_path, repo_path=empty_repo).valid is True
    assert "refs/gitshuttle/base/" in list_heads
    assert leaked_refs == ""


def test_create_bundle_cleans_base_metadata_refs_on_invalid_base(tmp_git_repo, tmp_path):
    """base ref 해석이 실패해도 앞서 만든 metadata ref는 남기지 않는다."""
    from gitshuttle.git_ops import get_commits
    from gitshuttle.bundle import create_bundle

    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "GIT_TERMINAL_PROMPT": "0"}
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_git_repo,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    ).stdout.strip()
    (tmp_git_repo / "feature.txt").write_text("feature", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo, check=True, env=env)
    subprocess.run(["git", "commit", "-m", "feat: feature"], cwd=tmp_git_repo, check=True, env=env)

    commits = get_commits(tmp_git_repo, branch=f"{base_sha}..HEAD")
    with pytest.raises(RuntimeError):
        create_bundle(
            tmp_git_repo,
            commits,
            tmp_path,
            filename="invalid_base.bundle",
            base_refs=[base_sha, "missing-base-ref"],
        )

    leaked_refs = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname)", "refs/gitshuttle/base"],
        cwd=tmp_git_repo,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    ).stdout
    assert leaked_refs == ""


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


def test_verify_bundle_detailed_includes_git_output(tmp_path, monkeypatch):
    """verify_bundle_detailed는 git bundle verify 실패 출력을 보존한다."""
    import gitshuttle.bundle as bundle_module
    from gitshuttle.bundle import verify_bundle_detailed

    bundle_path = tmp_path / "test.bundle"
    bundle_path.write_bytes(b"fake bundle content")

    def fake_run(args, cwd=None, capture_output=True, encoding="utf-8", env=None):
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="error: Repository lacks these prerequisite commits:\nabc123\n",
        )

    monkeypatch.setattr(bundle_module.subprocess, "run", fake_run)

    result = verify_bundle_detailed(bundle_path)

    assert result.valid is False
    assert "Repository lacks these prerequisite commits" in result.message
    assert "abc123" in result.message


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
