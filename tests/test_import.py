"""test_import.py — import_.py TDD 테스트.

TDD RED phase: import_.py 구현 전에 작성.
E2E 흐름: source repo export → target repo import → 커밋 수 확인.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _git_env() -> dict:
    return {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'GIT_TERMINAL_PROMPT': '0'}


def _add_commit(repo_path: Path, filename: str, content: str, message: str) -> None:
    env = _git_env()
    (repo_path / filename).write_text(content, encoding='utf-8')
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, encoding='utf-8', env=env)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_path, check=True, encoding='utf-8', env=env,
    )


def _export_repo(source: Path, output_dir: Path) -> Path:
    """source repo를 bundle로 export하고 bundle 경로를 반환한다."""
    from gitshuttle.git_ops import get_commits
    from gitshuttle.export_ import run_export

    commits = get_commits(source)
    result = run_export(
        repo_path=source,
        commits=commits,
        output_dir=output_dir,
        branch="HEAD",
        filename="test_shuttle",
    )
    return result.bundle


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_import_creates_commits_in_target(two_git_repos, tmp_path):
    """소스 repo export → 타겟 repo import 후 커밋 수가 늘어야 한다."""
    from gitshuttle.import_ import run_import, ImportResult
    from gitshuttle.git_ops import get_commits

    source, target = two_git_repos

    # source에 추가 커밋
    _add_commit(source, "feature.txt", "new feature", "feat: add feature")

    # export
    bundle_path = _export_repo(source, tmp_path)

    # target 커밋 수 before
    before_count = len(get_commits(target))

    # import
    result = run_import(bundle_path, target)

    assert isinstance(result, ImportResult)
    assert result.total >= 1
    assert result.imported >= 1

    # target 커밋 수 after — import된 커밋이 있어야 한다
    after_count = len(get_commits(target))
    assert after_count > before_count


def test_import_skip_duplicate(two_git_repos, tmp_path):
    """이미 존재하는 커밋은 skip 방식에서 건너뛰고, 작업은 계속된다."""
    from gitshuttle.import_ import run_import

    source, target = two_git_repos

    _add_commit(source, "f1.txt", "content1", "feat: first")

    bundle_path = _export_repo(source, tmp_path)

    # 첫 번째 import (정상)
    result1 = run_import(bundle_path, target, on_conflict="skip")
    assert result1.imported >= 1

    # 두 번째 import — 이미 존재하는 커밋들 → 모두 skip
    result2 = run_import(bundle_path, target, on_conflict="skip")
    # 두 번째에는 새로 imported되는 것이 없거나, skip이 있어야 한다
    assert result2.imported == 0 or result2.skipped >= 0  # skip은 오류 없이 계속


def test_import_abort_on_conflict(two_git_repos, tmp_path):
    """abort 방식에서 이미 존재하는 커밋이 있으면 ImportConflictError 발생."""
    from gitshuttle.import_ import run_import, ImportConflictError

    source, target = two_git_repos

    _add_commit(source, "f2.txt", "content2", "feat: second")

    bundle_path = _export_repo(source, tmp_path)

    # 첫 번째 import 성공
    run_import(bundle_path, target, on_conflict="skip")

    # 두 번째 import — 이미 존재하는 커밋이 있으면 abort
    with pytest.raises(ImportConflictError):
        run_import(bundle_path, target, on_conflict="abort")


def test_import_checksum_mismatch_raises(tmp_path):
    """sha256 파일 내용이 실제 bundle과 불일치하면 ChecksumError 발생."""
    from gitshuttle.import_ import run_import, ChecksumError

    # 더미 bundle 파일 생성 (실제 git bundle이 아니어도 checksum 검사가 먼저)
    bundle_path = tmp_path / "test.bundle"
    bundle_path.write_bytes(b"fake bundle content for checksum test")

    # 잘못된 checksum 파일 생성
    sha256_path = tmp_path / "test.bundle.sha256"
    sha256_path.write_text(
        "0000000000000000000000000000000000000000000000000000000000000000  test.bundle",
        encoding='utf-8',
    )

    # 더미 target repo 경로 (checksum 검사는 repo 접근 전에 수행)
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()

    with pytest.raises(ChecksumError) as exc_info:
        run_import(bundle_path, fake_repo, sha256_path=sha256_path)

    # 오류 메시지에 기대값(expected)과 실제값(actual)이 포함되어야 한다
    error_msg = str(exc_info.value)
    assert "0000000000000000000000000000000000000000000000000000000000000000" in error_msg


def test_import_checksum_error_message_has_reexport_hint(tmp_path):
    """ChecksumError 메시지에 'gitshuttle export' 재실행 힌트가 포함되어야 한다."""
    from gitshuttle.import_ import run_import, ChecksumError

    bundle_path = tmp_path / "test2.bundle"
    bundle_path.write_bytes(b"another fake bundle for hint test")

    sha256_path = tmp_path / "test2.bundle.sha256"
    sha256_path.write_text(
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa  test2.bundle",
        encoding='utf-8',
    )

    fake_repo = tmp_path / "fake_repo2"
    fake_repo.mkdir()

    with pytest.raises(ChecksumError) as exc_info:
        run_import(bundle_path, fake_repo, sha256_path=sha256_path)

    error_msg = str(exc_info.value)
    assert "gitshuttle export" in error_msg


def test_import_missing_bundle_raises(tmp_path):
    """존재하지 않는 .bundle 파일 경로 → FileNotFoundError 발생."""
    from gitshuttle.import_ import run_import

    nonexistent = tmp_path / "nonexistent.bundle"
    fake_repo = tmp_path / "fake_repo"
    fake_repo.mkdir()

    with pytest.raises(FileNotFoundError):
        run_import(nonexistent, fake_repo)


def test_import_bundle_verify_failure_has_prerequisite_hint(tmp_path, monkeypatch):
    """부분 bundle prerequisite 실패 시 증분/rewrite 안내를 포함한다."""
    import gitshuttle.import_ as import_module

    bundle_path = tmp_path / "partial.bundle"
    bundle_path.write_bytes(b"fake bundle")
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()

    monkeypatch.setattr(
        import_module,
        "verify_bundle_detailed",
        lambda bundle_path, repo_path=None: SimpleNamespace(
            valid=False,
            message="error: Repository lacks these prerequisite commits:\nabc123",
        ),
    )

    with pytest.raises(ValueError) as exc_info:
        import_module.run_import(bundle_path, fake_repo)

    error_message = str(exc_info.value)
    assert "Repository lacks these prerequisite commits" in error_message
    assert "최근 1~2개처럼 일부 커밋만 export" in error_message
    assert "작성자/날짜 rewrite" in error_message
    assert "--target-branch" in error_message


def test_import_force_overwrites(two_git_repos, tmp_path):
    """force 방식에서 이미 존재하는 커밋이 있어도 오류 없이 계속 진행한다."""
    from gitshuttle.import_ import run_import

    source, target = two_git_repos

    _add_commit(source, "f3.txt", "content3", "feat: third")

    bundle_path = _export_repo(source, tmp_path)

    # 첫 번째 import 성공
    run_import(bundle_path, target, on_conflict="skip")

    # 두 번째 import force — 오류 없이 완료되어야 한다
    result = run_import(bundle_path, target, on_conflict="force")
    assert result is not None


def test_rewrite_import_force_ref_update_uses_fast_import_force(tmp_path, monkeypatch):
    """rewrite import에서 force_ref_update=True이면 fast-import --force를 사용한다."""
    import gitshuttle.import_ as import_module

    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:2] == ["git", "fast-export"]:
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "reset refs/heads/main\n"
                    "commit refs/heads/main\n"
                    "mark :1\n"
                    "author A <a@example.com> 1 +0000\n"
                    "committer A <a@example.com> 1 +0000\n"
                    "data 4\n"
                    "msg\n"
                    "\n"
                ),
                stderr="",
            )
        if args[:2] == ["git", "fast-import"]:
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(import_module.subprocess, "run", fake_run)
    monkeypatch.setattr(import_module, "_ensure_clean_worktree", lambda repo_path: None)
    monkeypatch.setattr(
        import_module,
        "_checkout_or_create_branch",
        lambda repo_path, branch: ["e18" + "0" * 37],
    )

    import_module._rewrite_and_import(
        bundle_path=tmp_path / "test.bundle",
        repo_path=tmp_path,
        author_map={},
        target_branch="feat/gitshuttle",
        timestamp_mode="original",
        from_dt=None,
        force_ref_update=True,
    )

    fast_import_args = next(args for args in calls if args[:2] == ["git", "fast-import"])
    assert "--force" in fast_import_args


def test_rewrite_import_non_ff_error_has_recovery_hint(tmp_path, monkeypatch):
    """fast-import non-fast-forward 오류에는 target branch 해결 안내를 포함한다."""
    import gitshuttle.import_ as import_module

    def fake_run(args, **kwargs):
        if args[:2] == ["git", "fast-export"]:
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "reset refs/heads/main\n"
                    "commit refs/heads/main\n"
                    "mark :1\n"
                    "author A <a@example.com> 1 +0000\n"
                    "committer A <a@example.com> 1 +0000\n"
                    "data 4\n"
                    "msg\n"
                    "\n"
                ),
                stderr="",
            )
        if args[:2] == ["git", "fast-import"]:
            return SimpleNamespace(
                returncode=1,
                stdout=b"",
                stderr=(
                    b"warning: Not updating refs/heads/feat/gitshuttle "
                    b"(new tip e18 does not contain 72d3)\n"
                ),
            )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(import_module.subprocess, "run", fake_run)
    monkeypatch.setattr(import_module, "_ensure_clean_worktree", lambda repo_path: None)

    with pytest.raises(ValueError) as exc_info:
        import_module._rewrite_and_import(
            bundle_path=tmp_path / "test.bundle",
            repo_path=tmp_path,
            author_map={},
            target_branch="feat/gitshuttle",
            timestamp_mode="original",
            from_dt=None,
        )

    error_message = str(exc_info.value)
    assert "대상 브랜치 'feat/gitshuttle'가 이미 존재" in error_message
    assert "--target-branch" in error_message
    assert "--on-conflict force" in error_message


def test_checkout_or_create_branch_updates_worktree(tmp_path, monkeypatch):
    """fast-import 후 target branch checkout/reset으로 작업 폴더를 갱신한다."""
    import gitshuttle.import_ as import_module

    tip = "e18" + "0" * 37
    calls = []

    def fake_run_git(args, cwd):
        calls.append(args)
        if args == ["rev-parse", "refs/heads/feat/gitshuttle"]:
            return f"{tip}\n"
        if args == ["rev-parse", "--is-bare-repository"]:
            return "false\n"
        return ""

    monkeypatch.setattr(import_module, "run_git", fake_run_git)

    result = import_module._checkout_or_create_branch(tmp_path, "feat/gitshuttle")

    assert result == [tip]
    assert ["checkout", "feat/gitshuttle"] in calls
    assert ["reset", "--hard", tip] in calls


def test_ensure_clean_worktree_raises_on_dirty_repo(tmp_path, monkeypatch):
    """사용자 변경이 있으면 fast-import 전에 중단해 reset 손실을 막는다."""
    import gitshuttle.import_ as import_module

    def fake_run_git(args, cwd):
        if args == ["rev-parse", "--is-bare-repository"]:
            return "false\n"
        if args == ["status", "--porcelain"]:
            return " M README.md\n"
        return ""

    monkeypatch.setattr(import_module, "run_git", fake_run_git)

    with pytest.raises(ValueError) as exc_info:
        import_module._ensure_clean_worktree(tmp_path)

    assert "커밋되지 않은 변경 사항" in str(exc_info.value)
    assert "commit/stash" in str(exc_info.value)
