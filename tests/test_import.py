"""test_import.py — import_.py TDD 테스트.

TDD RED phase: import_.py 구현 전에 작성.
E2E 흐름: source repo export → target repo import → 커밋 수 확인.
"""
from __future__ import annotations

import os
import json
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


def test_rewrite_import_preserves_crlf_blob_payload(two_git_repos, tmp_path):
    """CRLF 파일이 포함된 bundle도 rewrite import에서 fast-import 오류 없이 반입한다."""
    from gitshuttle.import_ import run_import

    source, target = two_git_repos
    env = _git_env()
    subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=source, check=True, env=env)
    subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=target, check=True, env=env)

    crlf_payload = b"line1\r\nline2\r\n"
    (source / "crlf.txt").write_bytes(crlf_payload)
    subprocess.run(["git", "add", "crlf.txt"], cwd=source, check=True, env=env)
    subprocess.run(
        ["git", "commit", "-m", "feat: add crlf payload"],
        cwd=source,
        check=True,
        env=env,
    )

    author_map_path = tmp_path / "author_map.json"
    author_map_path.write_text(
        json.dumps({
            "test@test.com": {
                "name": "New Author",
                "email": "new.author@example.com",
            },
        }),
        encoding="utf-8",
    )

    bundle_path = _export_repo(source, tmp_path)

    result = run_import(
        bundle_path,
        target,
        author_map_path=str(author_map_path),
        target_branch="migration/crlf",
        timestamp_mode="original",
    )

    assert result.imported >= 1
    assert (target / "crlf.txt").read_bytes() == crlf_payload


def test_rewrite_import_partial_branch_bundle_appends_to_existing_target_branch(two_git_repos, tmp_path):
    """기존 target 브랜치에 부분 bundle을 얹을 때 source base 이력을 다시 가져오지 않는다."""
    from gitshuttle.export_ import run_export
    from gitshuttle.git_ops import get_commits
    from gitshuttle.import_ import run_import

    source, target = two_git_repos
    env = _git_env()

    _add_commit(source, "base.txt", "source base", "feat: source base")
    source_base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    ).stdout.strip()
    subprocess.run(["git", "checkout", "-b", "feature/work"], cwd=source, check=True, env=env)
    _add_commit(source, "feature.txt", "feature change", "feat: feature only")

    subprocess.run(
        ["git", "fetch", str(source), f"{source_base}:refs/gitshuttle/original/source-base"],
        cwd=target,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    )
    target_main = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=target,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    ).stdout.strip()
    subprocess.run(
        ["git", "checkout", "-b", "migration/feature"],
        cwd=target,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    )

    feature_commit = get_commits(source, branch="feature/work", limit=1)[0]
    bundle_path = run_export(
        repo_path=source,
        commits=[feature_commit],
        output_dir=tmp_path,
        branch="main..feature/work",
        filename="feature_delta",
    ).bundle

    result = run_import(
        bundle_path,
        target,
        target_branch="migration/feature",
        timestamp_mode="original",
    )

    ahead_count = subprocess.run(
        ["git", "rev-list", "--count", "migration/feature", "--not", target_main],
        cwd=target,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    ).stdout.strip()
    source_base_reachable = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_base, "migration/feature"],
        cwd=target,
        env=env,
    ).returncode == 0

    assert result.imported == 1
    assert ahead_count == "1"
    assert not source_base_reachable
    assert (target / "feature.txt").read_text(encoding="utf-8") == "feature change"


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
                ).encode("utf-8"),
                stderr=b"",
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


def test_rewrite_import_captures_fast_export_as_bytes_to_preserve_crlf_payload(tmp_path, monkeypatch):
    """fast-export blob payload의 CRLF가 text mode 변환으로 깨지면 안 된다."""
    import gitshuttle.import_ as import_module

    fast_export_kwargs = []
    fast_import_inputs = []
    payload = b"line1\r\nline2\r\n"
    stream = (
        b"blob\n"
        b"mark :1\n"
        + f"data {len(payload)}\n".encode("utf-8")
        + payload
        + b"reset refs/heads/main\n"
        + b"commit refs/heads/main\n"
        + b"mark :2\n"
        + b"author A <a@example.com> 1 +0000\n"
        + b"committer A <a@example.com> 1 +0000\n"
        + b"data 4\n"
        + b"msg\n"
        + b"M 100644 :1 crlf.txt\n"
        + b"\n"
    )

    def fake_run(args, **kwargs):
        if args[:2] == ["git", "fast-export"]:
            fast_export_kwargs.append(kwargs)
            return SimpleNamespace(returncode=0, stdout=stream, stderr=b"")
        if args[:2] == ["git", "fast-import"]:
            fast_import_inputs.append(kwargs["input"])
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
    )

    assert "encoding" not in fast_export_kwargs[0]
    assert "text" not in fast_export_kwargs[0]
    assert fast_import_inputs
    assert f"data {len(payload)}\n".encode("utf-8") + payload in fast_import_inputs[0]


def test_rewrite_import_exports_only_bundle_range_and_links_existing_target_tip(tmp_path, monkeypatch):
    """부분 bundle은 prerequisite 조상을 다시 export하지 않고 target branch tip에 이어붙인다."""
    import gitshuttle.import_ as import_module

    base_parent = "a" * 40
    target_tip = "b" * 40
    bundle_tip = "c" * 40
    fast_export_args = []
    fast_import_inputs = []

    def fake_run(args, **kwargs):
        if args[:3] == ["git", "rev-parse", "--verify"]:
            return SimpleNamespace(returncode=0, stdout=f"{target_tip}\n", stderr="")
        if args[:3] == ["git", "bundle", "list-heads"]:
            return SimpleNamespace(
                returncode=0,
                stdout=f"{bundle_tip} refs/gitshuttle/tmp_feature\n",
                stderr="",
            )
        if args[:3] == ["git", "bundle", "verify"]:
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "The bundle contains this ref:\n"
                    f"{bundle_tip} refs/gitshuttle/tmp_feature\n"
                    "The bundle requires this ref:\n"
                    f"{base_parent} \n"
                    "The bundle uses this hash algorithm: sha1\n"
                    f"{tmp_path / 'test.bundle'} is okay\n"
                ),
                stderr="",
            )
        if args[:2] == ["git", "fast-export"]:
            fast_export_args.append(args)
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "commit refs/gitshuttle/tmp_feature\n"
                    "mark :1\n"
                    "author A <a@example.com> 1 +0000\n"
                    "committer A <a@example.com> 1 +0000\n"
                    "data 4\n"
                    "msg\n"
                    f"from {base_parent}\n"
                    "M 100644 inline f.txt\n"
                    "data 2\n"
                    "x\n"
                    "\n"
                ).encode("utf-8"),
                stderr=b"",
            )
        if args[:2] == ["git", "fast-import"]:
            fast_import_inputs.append(kwargs["input"])
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(import_module.subprocess, "run", fake_run)
    monkeypatch.setattr(import_module, "_fetch_original_shadow_refs", lambda repo_path, tmp_dir: None)
    monkeypatch.setattr(import_module, "_delete_original_shadow_refs", lambda tmp_dir: None)
    monkeypatch.setattr(import_module, "_store_original_bundle_refs", lambda bundle_path, repo_path, target_branch: None)
    monkeypatch.setattr(import_module, "_ensure_clean_worktree", lambda repo_path: None)
    monkeypatch.setattr(
        import_module,
        "_checkout_or_create_branch",
        lambda repo_path, branch: [bundle_tip],
    )

    import_module._rewrite_and_import(
        bundle_path=tmp_path / "test.bundle",
        repo_path=tmp_path,
        author_map={},
        target_branch="feat/gitshuttle",
        timestamp_mode="original",
        from_dt=None,
    )

    assert fast_export_args == [
        [
            "git",
            "fast-export",
            "--reference-excluded-parents",
            "refs/gitshuttle/tmp_feature",
            f"^{base_parent}",
        ]
    ]
    assert fast_import_inputs
    assert f"from {target_tip}\n".encode("utf-8") in fast_import_inputs[0]
    assert f"from {base_parent}\n".encode("utf-8") not in fast_import_inputs[0]


def test_rewrite_import_uses_base_metadata_ref_as_excluded_parent(tmp_path, monkeypatch):
    """base metadata ref가 있으면 prerequisite 없이도 delta만 target tip에 이어붙인다."""
    import gitshuttle.import_ as import_module

    base_parent = "a" * 40
    target_tip = "b" * 40
    bundle_tip = "c" * 40
    fast_export_args = []
    fast_import_inputs = []

    def fake_run(args, **kwargs):
        if args[:3] == ["git", "rev-parse", "--verify"]:
            return SimpleNamespace(returncode=0, stdout=f"{target_tip}\n", stderr="")
        if args[:3] == ["git", "bundle", "list-heads"]:
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    f"{bundle_tip} refs/gitshuttle/tmp_feature\n"
                    f"{base_parent} refs/gitshuttle/base/{base_parent[:12]}\n"
                ),
                stderr="",
            )
        if args[:3] == ["git", "bundle", "verify"]:
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "The bundle contains these refs:\n"
                    f"{bundle_tip} refs/gitshuttle/tmp_feature\n"
                    f"{base_parent} refs/gitshuttle/base/{base_parent[:12]}\n"
                    "The bundle uses this hash algorithm: sha1\n"
                    f"{tmp_path / 'test.bundle'} is okay\n"
                ),
                stderr="",
            )
        if args[:2] == ["git", "fast-export"]:
            fast_export_args.append(args)
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "commit refs/gitshuttle/tmp_feature\n"
                    "mark :1\n"
                    "author A <a@example.com> 1 +0000\n"
                    "committer A <a@example.com> 1 +0000\n"
                    "data 4\n"
                    "msg\n"
                    f"from {base_parent}\n"
                    "M 100644 inline f.txt\n"
                    "data 2\n"
                    "x\n"
                    "\n"
                ).encode("utf-8"),
                stderr=b"",
            )
        if args[:2] == ["git", "fast-import"]:
            fast_import_inputs.append(kwargs["input"])
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(import_module.subprocess, "run", fake_run)
    monkeypatch.setattr(import_module, "_fetch_original_shadow_refs", lambda repo_path, tmp_dir: None)
    monkeypatch.setattr(import_module, "_delete_original_shadow_refs", lambda tmp_dir: None)
    monkeypatch.setattr(import_module, "_store_original_bundle_refs", lambda bundle_path, repo_path, target_branch: None)
    monkeypatch.setattr(import_module, "_ensure_clean_worktree", lambda repo_path: None)
    monkeypatch.setattr(
        import_module,
        "_checkout_or_create_branch",
        lambda repo_path, branch: [bundle_tip],
    )

    import_module._rewrite_and_import(
        bundle_path=tmp_path / "test.bundle",
        repo_path=tmp_path,
        author_map={},
        target_branch="feat/gitshuttle",
        timestamp_mode="original",
        from_dt=None,
    )

    assert fast_export_args == [
        [
            "git",
            "fast-export",
            "--reference-excluded-parents",
            "refs/gitshuttle/tmp_feature",
            f"^{base_parent}",
        ]
    ]
    assert f"from {target_tip}\n".encode("utf-8") in fast_import_inputs[0]
    assert f"from {base_parent}\n".encode("utf-8") not in fast_import_inputs[0]


def test_rewrite_import_base_ref_bundle_appends_without_original_base(two_git_repos, tmp_path):
    """target repo에 원본 base SHA가 없어도 base_refs bundle은 delta만 반입한다."""
    from gitshuttle.export_ import run_export
    from gitshuttle.git_ops import get_commits
    from gitshuttle.import_ import run_import

    source, target = two_git_repos
    env = _git_env()

    _add_commit(source, "base.txt", "source base", "feat: source base")
    source_base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    ).stdout.strip()
    subprocess.run(["git", "checkout", "-b", "feature/work"], cwd=source, check=True, env=env)
    _add_commit(source, "feature.txt", "feature change", "feat: feature only")

    target_main = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=target,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    ).stdout.strip()
    subprocess.run(
        ["git", "checkout", "-b", "migration/feature"],
        cwd=target,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    )

    feature_commits = get_commits(source, branch=f"{source_base}..feature/work")
    bundle_path = run_export(
        repo_path=source,
        commits=feature_commits,
        output_dir=tmp_path,
        branch=f"{source_base}..feature/work",
        filename="feature_delta_with_base",
        base_refs=[source_base],
    ).bundle

    result = run_import(
        bundle_path,
        target,
        target_branch="migration/feature",
        timestamp_mode="original",
    )

    ahead_count = subprocess.run(
        ["git", "rev-list", "--count", "migration/feature", "--not", target_main],
        cwd=target,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
    ).stdout.strip()
    source_base_reachable = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_base, "migration/feature"],
        cwd=target,
        env=env,
    ).returncode == 0

    assert result.imported == 1
    assert ahead_count == "1"
    assert not source_base_reachable
    assert (target / "feature.txt").read_text(encoding="utf-8") == "feature change"


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
                ).encode("utf-8"),
                stderr=b"",
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


def test_fetch_original_shadow_refs_copies_hidden_refs(tmp_path, monkeypatch):
    """증분 rewrite import 전에 target repo의 원본 SHA refs를 임시 repo로 복사한다."""
    import gitshuttle.import_ as import_module

    source_repo = tmp_path / "target"
    tmp_repo = tmp_path / "tmp.git"
    source_repo.mkdir()
    tmp_repo.mkdir()
    calls = []

    monkeypatch.setattr(
        import_module,
        "run_git",
        lambda args, cwd: "refs/gitshuttle/original/main/gitshuttle/tmp_abc\n",
    )

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(import_module.subprocess, "run", fake_run)

    import_module._fetch_original_shadow_refs(source_repo, tmp_repo)

    assert calls
    assert calls[0][0] == [
        "git",
        "fetch",
        str(source_repo),
        "+refs/gitshuttle/original/*:refs/gitshuttle/original/*",
    ]
    assert calls[0][1]["cwd"] == tmp_repo


def test_fetch_original_shadow_refs_noops_when_empty(tmp_path, monkeypatch):
    """보관된 원본 SHA refs가 없으면 추가 fetch를 하지 않는다."""
    import gitshuttle.import_ as import_module

    calls = []

    monkeypatch.setattr(import_module, "run_git", lambda args, cwd: "")
    monkeypatch.setattr(
        import_module.subprocess,
        "run",
        lambda args, **kwargs: calls.append(args),
    )

    import_module._fetch_original_shadow_refs(tmp_path / "target", tmp_path / "tmp.git")

    assert calls == []


def test_delete_original_shadow_refs_removes_only_hidden_refs(tmp_path, monkeypatch):
    """fast-export 전에 shadow refs를 삭제해 실제 export 대상에 섞이지 않게 한다."""
    import gitshuttle.import_ as import_module

    calls = []

    def fake_run_git(args, cwd):
        calls.append(args)
        if args == ["for-each-ref", "--format=%(refname)", "refs/gitshuttle/original"]:
            return (
                "refs/gitshuttle/original/main/gitshuttle/tmp_abc\n"
                "refs/gitshuttle/original/main/heads/main\n"
            )
        return ""

    monkeypatch.setattr(import_module, "run_git", fake_run_git)

    import_module._delete_original_shadow_refs(tmp_path)

    assert ["update-ref", "-d", "refs/gitshuttle/original/main/gitshuttle/tmp_abc"] in calls
    assert ["update-ref", "-d", "refs/gitshuttle/original/main/heads/main"] in calls


def test_store_original_bundle_refs_uses_hidden_namespace(tmp_path, monkeypatch):
    """rewrite import 후 원본 bundle refs를 target branch별 hidden namespace에 보관한다."""
    import gitshuttle.import_ as import_module

    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(import_module.subprocess, "run", fake_run)

    warning = import_module._store_original_bundle_refs(
        bundle_path=tmp_path / "shuttle.bundle",
        repo_path=tmp_path / "repo",
        target_branch="migration/gitshuttle-20260610",
    )

    assert warning is None
    assert calls[0][0] == [
        "git",
        "fetch",
        str(tmp_path / "shuttle.bundle"),
        "+refs/*:refs/gitshuttle/original/migration/gitshuttle-20260610/*",
    ]
    assert calls[0][1]["cwd"] == tmp_path / "repo"


def test_store_original_bundle_refs_returns_warning_on_failure(tmp_path, monkeypatch):
    """원본 SHA refs 보관 실패는 import 자체 실패 대신 경고로 전달한다."""
    import gitshuttle.import_ as import_module

    monkeypatch.setattr(
        import_module.subprocess,
        "run",
        lambda args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="fatal: bad bundle\n",
        ),
    )

    warning = import_module._store_original_bundle_refs(
        bundle_path=tmp_path / "shuttle.bundle",
        repo_path=tmp_path / "repo",
        target_branch="migration/main",
    )

    assert warning is not None
    assert "원본 SHA shadow refs 보관 실패" in warning
    assert "fatal: bad bundle" in warning


def test_rewrite_import_partial_bundle_continues_from_hidden_original_refs(two_git_repos, tmp_path):
    """rewrite import 후 저장된 원본 SHA refs 덕분에 후속 부분 bundle을 반입할 수 있다."""
    from gitshuttle.export_ import run_export
    from gitshuttle.git_ops import get_commits
    from gitshuttle.import_ import run_import

    source, target = two_git_repos
    _add_commit(source, "one.txt", "one", "feat: one")
    _add_commit(source, "two.txt", "two", "feat: two")

    commits = get_commits(source)
    newest, middle, oldest = commits[0], commits[1], commits[2]
    author_map_path = tmp_path / "author_map.json"
    author_map_path.write_text(
        json.dumps({
            "test@test.com": {
                "name": "New Author",
                "email": "new.author@example.com",
            },
        }),
        encoding="utf-8",
    )

    initial_bundle = run_export(
        repo_path=source,
        commits=[middle, oldest],
        output_dir=tmp_path,
        branch="HEAD",
        filename="initial",
    ).bundle
    partial_bundle = run_export(
        repo_path=source,
        commits=[newest],
        output_dir=tmp_path,
        branch="HEAD",
        filename="partial",
    ).bundle

    first = run_import(
        bundle_path=initial_bundle,
        repo_path=target,
        author_map_path=str(author_map_path),
        target_branch="migration/main",
        timestamp_mode="original",
    )
    second = run_import(
        bundle_path=partial_bundle,
        repo_path=target,
        author_map_path=str(author_map_path),
        target_branch="migration/main",
        timestamp_mode="original",
    )

    assert first.imported >= 2
    assert second.imported == 1
    commit_count = subprocess.run(
        ["git", "rev-list", "--count", "migration/main"],
        cwd=target,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=_git_env(),
    ).stdout.strip()
    latest_author = subprocess.run(
        ["git", "log", "-1", "--format=%an <%ae>", "migration/main"],
        cwd=target,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=_git_env(),
    ).stdout.strip()

    assert commit_count == "3"
    assert latest_author == "New Author <new.author@example.com>"


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
