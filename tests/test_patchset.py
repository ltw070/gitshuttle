from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path


def _git_env() -> dict:
    return {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'GIT_TERMINAL_PROMPT': '0'}


def _init_repo(repo_path: Path, message: str = "init") -> None:
    subprocess.run(["git", "init", str(repo_path)], check=True, encoding="utf-8", env=_git_env())
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_path, check=True, encoding="utf-8", env=_git_env())
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, encoding="utf-8", env=_git_env())
    (repo_path / "README.md").write_text("# Test", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, encoding="utf-8", env=_git_env())
    subprocess.run(["git", "commit", "-m", message], cwd=repo_path, check=True, encoding="utf-8", env=_git_env())


def _add_commit(repo_path: Path, filename: str, content: str, message: str) -> None:
    (repo_path / filename).write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, encoding="utf-8", env=_git_env())
    subprocess.run(["git", "commit", "-m", message], cwd=repo_path, check=True, encoding="utf-8", env=_git_env())


def test_create_patchset_writes_metadata_and_patches(tmp_git_repo, tmp_path):
    """patchset export는 metadata.json과 커밋별 patch를 포함한다."""
    from gitshuttle.git_ops import get_commits
    from gitshuttle.patchset import create_patchset

    _add_commit(tmp_git_repo, "feature.txt", "feature", "feat: replay")
    commits = get_commits(tmp_git_repo)

    patchset = create_patchset(
        repo_path=tmp_git_repo,
        commits=[commits[0]],
        output_dir=tmp_path,
        filename="test.patchset",
        branch="HEAD",
    )

    assert patchset.exists()
    assert patchset.suffix == ".patchset"
    with zipfile.ZipFile(patchset, "r") as zf:
        metadata = json.loads(zf.read("metadata.json").decode("utf-8"))
        assert metadata["type"] == "gitshuttle-patchset"
        assert metadata["commits"][0]["subject"] == "feat: replay"
        assert metadata["commits"][0]["patch"] in zf.namelist()
        assert metadata["selection"]["contiguous_first_parent"] is True


def test_create_patchset_reuses_batch_metadata_and_parent_cache(tmp_path, monkeypatch):
    """patchset 생성은 metadata 일괄 조회 결과의 parent를 patch 생성에 재사용한다."""
    from gitshuttle.git_ops import Commit
    import gitshuttle.patchset as patchset_module

    commit = Commit(
        hash="b" * 40,
        short_hash="bbbbbbb",
        date="2026-06-10 09:00:00 +0900",
        author="ltw070",
        message="feat: fast patchset",
        files_changed=1,
    )
    calls = {}

    def fake_read_commits_metadata(repo_path, commits):
        calls["metadata_commits"] = commits
        return {
            commit.hash: {
                "hash": commit.hash,
                "subject": commit.message,
                "message": commit.message,
                "author_name": "ltw070",
                "author_email": "ltw070@naver.com",
                "author_date": "2026-06-10T09:00:00+09:00",
                "committer_name": "ltw070",
                "committer_email": "ltw070@naver.com",
                "committer_date": "2026-06-10T09:00:00+09:00",
                "parents": ["a" * 40],
                "parent_count": 1,
            }
        }

    def fake_read_commit_patch(repo_path, commit_hash, parents):
        calls["patch_parents"] = parents
        return b"diff --git a/a.txt b/a.txt\n"

    monkeypatch.setattr(patchset_module, "_read_commits_metadata", fake_read_commits_metadata)
    monkeypatch.setattr(patchset_module, "_read_commit_patch", fake_read_commit_patch)

    patchset = patchset_module.create_patchset(
        repo_path=tmp_path,
        commits=[commit],
        output_dir=tmp_path,
        filename="fast.patchset",
    )

    assert patchset.exists()
    assert calls["metadata_commits"] == [commit]
    assert calls["patch_parents"] == ["a" * 40]


def test_read_commits_metadata_chunks_large_selection(monkeypatch):
    """metadata 조회는 Windows 명령행 길이 제한을 피하도록 batch 처리한다."""
    from gitshuttle.git_ops import Commit
    import gitshuttle.patchset as patchset_module

    commits = [
        Commit(
            hash=str(index) * 40,
            short_hash=str(index) * 7,
            date="2026-06-10 09:00:00 +0900",
            author="ltw070",
            message=f"commit {index}",
            files_changed=1,
        )
        for index in (1, 2, 3)
    ]
    batches = []

    def fake_read_batch(repo_path, batch):
        batches.append([commit.hash for commit in batch])
        return {
            commit.hash: {
                "hash": commit.hash,
                "parents": [],
                "parent_count": 0,
            }
            for commit in batch
        }

    monkeypatch.setattr(patchset_module, "METADATA_BATCH_SIZE", 2)
    monkeypatch.setattr(patchset_module, "_read_commits_metadata_batch", fake_read_batch)

    metadata = patchset_module._read_commits_metadata("repo", commits)

    assert batches == [[commits[0].hash, commits[1].hash], [commits[2].hash]]
    assert set(metadata) == {commit.hash for commit in commits}


def test_create_patchset_supports_stored_compression(tmp_git_repo, tmp_path):
    """compression=stored 는 zip 항목을 무압축으로 저장한다."""
    from gitshuttle.git_ops import get_commits
    from gitshuttle.patchset import create_patchset

    commits = get_commits(tmp_git_repo)
    patchset = create_patchset(
        repo_path=tmp_git_repo,
        commits=[commits[0]],
        output_dir=tmp_path,
        filename="stored.patchset",
        compression="stored",
    )

    with zipfile.ZipFile(patchset, "r") as zf:
        assert all(info.compress_type == zipfile.ZIP_STORED for info in zf.infolist())


def test_run_replay_import_applies_patchset_with_author_map(tmp_path):
    """replay import는 대상 HEAD 위에 새 커밋을 생성하고 author_map을 적용한다."""
    from gitshuttle.git_ops import get_commits
    from gitshuttle.patchset import create_patchset, run_replay_import

    source = tmp_path / "source"
    target = tmp_path / "target"
    _init_repo(source, "init source")
    _init_repo(target, "init target")
    _add_commit(source, "feature.txt", "feature", "feat: replay feature")

    commits = get_commits(source)
    patchset = create_patchset(
        repo_path=source,
        commits=[commits[0]],
        output_dir=tmp_path,
        filename="feature.patchset",
        branch="HEAD",
    )
    author_map = tmp_path / "author_map.json"
    author_map.write_text(
        json.dumps({"test@test.com": {"name": "ltw070", "email": "ltw070@naver.com"}}),
        encoding="utf-8",
    )

    result = run_replay_import(
        patchset_path=patchset,
        repo_path=target,
        author_map_path=str(author_map),
        target_branch="main",
        timestamp_mode="original",
    )

    latest = subprocess.run(
        ["git", "log", "-1", "--format=%s|%an <%ae>"],
        cwd=target,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=_git_env(),
    ).stdout.strip()
    assert result.imported == 1
    assert (target / "feature.txt").read_text(encoding="utf-8") == "feature"
    assert latest == "feat: replay feature|ltw070 <ltw070@naver.com>"


def test_replay_import_duplicate_head_message_requires_confirmation(tmp_path):
    """대상 HEAD 제목과 첫 replay 제목이 같으면 확인 콜백이 거부할 수 있다."""
    from gitshuttle.patchset import run_replay_import

    target = tmp_path / "target"
    _init_repo(target, "feat: same")
    patchset = tmp_path / "same.patchset"
    _write_empty_patchset(patchset, subject="feat: same")

    try:
        run_replay_import(
            patchset_path=patchset,
            repo_path=target,
            timestamp_mode="original",
            confirm_duplicate_message=lambda head, first: False,
        )
    except ValueError as exc:
        assert "취소" in str(exc)
    else:
        raise AssertionError("duplicate message confirmation should abort")

    count = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=target,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=_git_env(),
    ).stdout.strip()
    assert count == "1"


def test_replay_import_skips_already_applied_patch(tmp_path):
    """patch 내용이 이미 대상에 적용되어 있으면 새 커밋 없이 건너뛴다."""
    from gitshuttle.git_ops import get_commits
    from gitshuttle.patchset import create_patchset, run_replay_import

    source = tmp_path / "source"
    target = tmp_path / "target"
    _init_repo(source, "init source")
    _init_repo(target, "init target")
    _add_commit(source, "feature.txt", "feature", "feat: replay feature")
    _add_commit(target, "feature.txt", "feature", "chore: already applied")

    commits = get_commits(source)
    patchset = create_patchset(
        repo_path=source,
        commits=[commits[0]],
        output_dir=tmp_path,
        filename="feature.patchset",
        branch="HEAD",
    )

    result = run_replay_import(
        patchset_path=patchset,
        repo_path=target,
        timestamp_mode="original",
    )

    count = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=target,
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=_git_env(),
    ).stdout.strip()

    assert result.imported == 0
    assert result.skipped == 1
    assert "이미 적용된 replay patch" in result.warnings[0]
    assert count == "2"


def test_replay_import_existing_path_conflict_has_recovery_hint(tmp_path):
    """같은 경로가 다른 내용으로 이미 있으면 복구 안내와 함께 실패한다."""
    from gitshuttle.git_ops import get_commits
    from gitshuttle.patchset import create_patchset, run_replay_import

    source = tmp_path / "source"
    target = tmp_path / "target"
    _init_repo(source, "init source")
    _init_repo(target, "init target")
    _add_commit(source, "feature.txt", "source content", "feat: replay feature")
    _add_commit(target, "feature.txt", "target content", "chore: divergent file")

    commits = get_commits(source)
    patchset = create_patchset(
        repo_path=source,
        commits=[commits[0]],
        output_dir=tmp_path,
        filename="feature.patchset",
        branch="HEAD",
    )

    try:
        run_replay_import(
            patchset_path=patchset,
            repo_path=target,
            timestamp_mode="original",
        )
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("conflicting existing path should fail")

    assert "replay patch 적용 실패" in message
    assert "같은 경로의 파일이 이미" in message
    assert "그 이후 커밋만 patchset" in message


def _write_empty_patchset(path: Path, subject: str) -> None:
    metadata = {
        "type": "gitshuttle-patchset",
        "version": 1,
        "branch": "HEAD",
        "commits": [
            {
                "hash": "a" * 40,
                "subject": subject,
                "message": subject,
                "author_name": "Test User",
                "author_email": "test@test.com",
                "author_date": "2026-06-10T00:00:00+00:00",
                "committer_name": "Test User",
                "committer_email": "test@test.com",
                "committer_date": "2026-06-10T00:00:00+00:00",
                "parents": [],
                "parent_count": 0,
                "patch": "patches/0001-empty.patch",
            }
        ],
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("metadata.json", json.dumps(metadata))
        zf.writestr("patches/0001-empty.patch", b"")
