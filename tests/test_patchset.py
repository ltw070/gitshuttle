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
