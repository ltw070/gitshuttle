"""Patchset export/import for replay-style transfers."""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .git_ops import Commit, _git_env, run_git
from .rewrite import load_author_map


PATCHSET_TYPE = "gitshuttle-patchset"
PATCHSET_VERSION = 1
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
METADATA_FORMAT = "%H%x00%P%x00%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI%x00%B%x1e"
METADATA_BATCH_SIZE = 100
FORMAT_PATCH_FROM_RE = re.compile(br"(?m)^From [0-9a-f]{40} .*(?:\r?\n)")


@dataclass
class ReplayResult:
    """Result of replaying a patchset."""

    imported: int
    skipped: int
    total: int
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReplayCommitResult:
    """Result of replaying a single patchset commit."""

    imported: int = 0
    skipped: int = 0


def create_patchset(
    repo_path: Path | str,
    commits: list[Commit],
    output_dir: Path | str,
    filename: str | None = None,
    branch: str = "unknown",
    compression: str = "fast",
) -> Path:
    """Create a replay patchset from selected commits.

    The selected commits are expected in the same order as get_commits returns
    them, newest first. The patchset stores them oldest first for replay.
    """
    if not commits:
        raise ValueError("commits 목록이 비어있습니다. 최소 1개의 커밋이 필요합니다.")

    repo_path = Path(repo_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        date_str = datetime.now().strftime("%y%m%d")
        filename = f"shuttle_{date_str}.patchset"

    patchset_path = output_dir / filename
    replay_commits = _order_commits_for_replay(repo_path, commits)
    metadata_by_hash = _read_commits_metadata(repo_path, replay_commits)
    patches_by_hash, patch_source = _read_commit_patches(
        repo_path,
        replay_commits,
        metadata_by_hash,
    )

    metadata: dict = {
        "type": PATCHSET_TYPE,
        "version": PATCHSET_VERSION,
        "branch": branch,
        "selection": {
            "contiguous_first_parent": _is_contiguous_first_parent_series(
                replay_commits,
                metadata_by_hash,
            ),
            "order": "topo",
            "patch_source": patch_source,
        },
        "commits": [],
    }

    with zipfile.ZipFile(patchset_path, "w", **_zip_options(compression)) as zf:
        for index, commit in enumerate(replay_commits, start=1):
            patch_name = f"patches/{index:04d}-{commit.short_hash}.patch"
            commit_meta = metadata_by_hash[commit.hash]
            commit_meta["patch"] = patch_name
            commit_meta["files"] = _write_commit_snapshots(
                zf,
                repo_path,
                commit.hash,
                commit.short_hash,
                commit_meta["parents"],
                index,
            )
            metadata["commits"].append(commit_meta)
            zf.writestr(patch_name, patches_by_hash[commit.hash])

        zf.writestr(
            "metadata.json",
            json.dumps(metadata, ensure_ascii=False, indent=2),
        )

    return patchset_path


def run_replay_import(
    patchset_path: Path | str,
    repo_path: Path | str,
    author_map_path: str | None = None,
    target_branch: str | None = None,
    timestamp_mode: str = "now",
    on_conflict: str = "skip",
    confirm_duplicate_message: Callable[[str, str], bool] | None = None,
) -> ReplayResult:
    """Replay a patchset onto the target repository's current HEAD.

    This is intentionally cherry-pick-like: commits are recreated on top of the
    target branch, so original commit SHA and merge topology are not preserved.
    """
    patchset_path = Path(patchset_path)
    repo_path = Path(repo_path)
    if on_conflict not in ("skip", "force", "abort"):
        raise ValueError("on_conflict는 skip, force, abort 중 하나여야 합니다.")

    metadata = _load_patchset_metadata(patchset_path)
    commits = metadata["commits"]
    if not commits:
        return ReplayResult(imported=0, skipped=0, total=0)

    _ensure_worktree_repo(repo_path)
    _ensure_clean_worktree(repo_path)
    _checkout_target_branch(
        repo_path,
        target_branch,
        start_empty=_starts_with_root_commit(commits),
    )
    _ensure_clean_worktree(repo_path)

    head_subject = _get_head_subject(repo_path)
    first_subject = commits[0].get("subject", "")
    if head_subject and first_subject and head_subject == first_subject:
        if confirm_duplicate_message is None:
            raise ValueError(
                "replay import 확인 필요: 대상 HEAD의 마지막 커밋 메시지와 "
                f"첫 replay 커밋 메시지가 같습니다: {first_subject}"
            )
        if not confirm_duplicate_message(head_subject, first_subject):
            raise ValueError("사용자가 replay import를 취소했습니다.")

    author_map = load_author_map(author_map_path) if author_map_path else {}
    warnings: list[str] = []
    timestamp_plan = _build_timestamp_plan(commits, timestamp_mode)

    imported = 0
    skipped = 0
    for index, commit_meta in enumerate(commits):
        result = _replay_commit(
            patchset_path=patchset_path,
            repo_path=repo_path,
            commit_meta=commit_meta,
            commit_number=index + 1,
            commit_total=len(commits),
            author_map=author_map,
            timestamp=timestamp_plan[index],
            on_conflict=on_conflict,
            warnings=warnings,
        )
        imported += result.imported
        skipped += result.skipped

    return ReplayResult(
        imported=imported,
        skipped=skipped,
        total=len(commits),
        warnings=warnings,
    )


def _replay_commit(
    *,
    patchset_path: Path,
    repo_path: Path,
    commit_meta: dict,
    commit_number: int,
    commit_total: int,
    author_map: dict,
    timestamp: tuple[str, str],
    on_conflict: str,
    warnings: list[str],
) -> ReplayCommitResult:
    patch_bytes = _read_patch_bytes(patchset_path, commit_meta["patch"])
    patch_applied = bool(patch_bytes.strip())

    if patch_applied:
        applied, forced = _apply_patch_with_conflict_policy(
            patchset_path=patchset_path,
            repo_path=repo_path,
            commit_meta=commit_meta,
            commit_number=commit_number,
            commit_total=commit_total,
            patch_bytes=patch_bytes,
            on_conflict=on_conflict,
        )
        if not applied:
            warnings.append(
                f"이미 적용된 replay patch 건너뜀: {commit_meta.get('subject', '')}"
            )
            return ReplayCommitResult(skipped=1)
        if forced:
            warnings.append(f"force replay 적용: {commit_meta.get('subject', '')}")

    author = _mapped_identity(
        commit_meta["author_name"],
        commit_meta["author_email"],
        author_map,
        warnings,
    )
    committer = _mapped_identity(
        commit_meta["committer_name"],
        commit_meta["committer_email"],
        author_map,
        warnings,
    )
    author_date, committer_date = timestamp
    _commit_index(
        repo_path=repo_path,
        message=commit_meta["message"],
        author_name=author[0],
        author_email=author[1],
        author_date=author_date,
        committer_name=committer[0],
        committer_email=committer[1],
        committer_date=committer_date,
        allow_empty=not patch_applied,
    )
    return ReplayCommitResult(imported=1)


def _apply_patch_with_conflict_policy(
    *,
    patchset_path: Path,
    repo_path: Path,
    commit_meta: dict,
    commit_number: int,
    commit_total: int,
    patch_bytes: bytes,
    on_conflict: str,
) -> tuple[bool, bool]:
    try:
        return _apply_patch(repo_path, patch_bytes), False
    except ValueError as exc:
        if on_conflict != "force":
            raise ValueError(
                _format_replay_commit_failure(
                    commit_meta,
                    commit_number,
                    commit_total,
                    str(exc),
                )
            ) from exc

        try:
            applied = _force_apply_commit_snapshot(
                patchset_path,
                repo_path,
                commit_meta,
            )
        except ValueError as force_exc:
            raise ValueError(
                _format_replay_commit_failure(
                    commit_meta,
                    commit_number,
                    commit_total,
                    f"{exc}\n\nforce 적용 실패:\n{force_exc}",
                )
            ) from force_exc
        return applied, applied


def _read_commit_metadata(repo_path: Path, commit_hash: str) -> dict:
    return _read_commits_metadata(repo_path, [Commit(
        hash=commit_hash,
        short_hash=commit_hash[:7],
        date="",
        author="",
        message="",
        files_changed=0,
    )])[commit_hash]


def _order_commits_for_replay(repo_path: Path, commits: list[Commit]) -> list[Commit]:
    """Return selected commits oldest-first in topological order."""
    selected = {commit.hash: commit for commit in commits}
    result = subprocess.run(
        ["git", "rev-list", "--topo-order", "--reverse", *selected.keys()],
        cwd=repo_path,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=_git_env(),
    )
    if result.returncode != 0:
        return list(reversed(commits))

    ordered: list[Commit] = []
    seen: set[str] = set()
    for commit_hash in result.stdout.splitlines():
        commit = selected.get(commit_hash.strip())
        if commit is not None and commit.hash not in seen:
            ordered.append(commit)
            seen.add(commit.hash)

    for commit in reversed(commits):
        if commit.hash not in seen:
            ordered.append(commit)
    return ordered


def _read_commits_metadata(repo_path: Path, commits: list[Commit]) -> dict[str, dict]:
    if not commits:
        return {}

    metadata_by_hash: dict[str, dict] = {}
    for start in range(0, len(commits), METADATA_BATCH_SIZE):
        batch = commits[start:start + METADATA_BATCH_SIZE]
        metadata_by_hash.update(_read_commits_metadata_batch(repo_path, batch))
    return metadata_by_hash


def _read_commits_metadata_batch(repo_path: Path, commits: list[Commit]) -> dict[str, dict]:
    commit_hashes = [commit.hash for commit in commits]
    result = subprocess.run(
        ["git", "show", "--no-patch", f"--format={METADATA_FORMAT}", *commit_hashes],
        cwd=repo_path,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=_git_env(),
    )
    if result.returncode != 0:
        raise ValueError(f"커밋 메타데이터를 읽을 수 없습니다:\n{result.stderr}")

    metadata_by_hash: dict[str, dict] = {}
    records = [record.strip("\n") for record in result.stdout.split("\x1e") if record.strip()]
    for record in records:
        parts = record.split("\x00", 8)
        if len(parts) != 9:
            raise ValueError("커밋 메타데이터 응답을 파싱할 수 없습니다.")

        (
            commit_hash,
            parents_text,
            author_name,
            author_email,
            author_date,
            committer_name,
            committer_email,
            committer_date,
            message,
        ) = parts
        message = message.rstrip("\n")
        parents = parents_text.split() if parents_text else []
        metadata_by_hash[commit_hash] = {
            "hash": commit_hash,
            "subject": message.splitlines()[0] if message else "",
            "message": message,
            "author_name": author_name,
            "author_email": author_email,
            "author_date": author_date,
            "committer_name": committer_name,
            "committer_email": committer_email,
            "committer_date": committer_date,
            "parents": parents,
            "parent_count": len(parents),
        }

    missing = [commit_hash for commit_hash in commit_hashes if commit_hash not in metadata_by_hash]
    if missing:
        raise ValueError(f"커밋 메타데이터를 읽을 수 없습니다: {', '.join(missing)}")

    return metadata_by_hash


def _read_commit_patches(
    repo_path: Path,
    replay_commits: list[Commit],
    metadata_by_hash: dict[str, dict],
) -> tuple[dict[str, bytes], str]:
    if _can_use_format_patch(replay_commits, metadata_by_hash):
        try:
            return _read_format_patches(repo_path, replay_commits, metadata_by_hash), "format-patch"
        except ValueError:
            pass

    return (
        {
            commit.hash: _read_commit_patch(
                repo_path,
                commit.hash,
                metadata_by_hash[commit.hash]["parents"],
            )
            for commit in replay_commits
        },
        "per-commit-diff",
    )


def _read_format_patches(
    repo_path: Path,
    replay_commits: list[Commit],
    metadata_by_hash: dict[str, dict],
) -> dict[str, bytes]:
    first = replay_commits[0]
    tip = replay_commits[-1]
    first_parents = metadata_by_hash[first.hash]["parents"]
    cmd = [
        "git",
        "format-patch",
        "--stdout",
        "--binary",
        "--full-index",
        "--no-stat",
        "--no-signature",
    ]
    if first_parents:
        cmd.append(f"{first_parents[0]}..{tip.hash}")
    else:
        cmd.extend(["--root", tip.hash])

    result = subprocess.run(
        cmd,
        cwd=repo_path,
        capture_output=True,
        env=_git_env(),
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise ValueError(f"format-patch 생성 실패:\n{stderr}")

    chunks = _split_format_patch_stream(result.stdout)
    if len(chunks) != len(replay_commits):
        raise ValueError("format-patch 결과 개수가 선택 커밋 수와 일치하지 않습니다.")

    return {
        commit.hash: patch_bytes
        for commit, patch_bytes in zip(replay_commits, chunks)
    }


def _split_format_patch_stream(patch_bytes: bytes) -> list[bytes]:
    matches = list(FORMAT_PATCH_FROM_RE.finditer(patch_bytes))
    chunks: list[bytes] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(patch_bytes)
        chunks.append(patch_bytes[match.start():end])
    return chunks


def _read_commit_patch(repo_path: Path, commit_hash: str, parents: list[str]) -> bytes:
    base = parents[0] if parents else EMPTY_TREE
    result = subprocess.run(
        ["git", "diff", "--binary", "--full-index", base, commit_hash],
        cwd=repo_path,
        capture_output=True,
        env=_git_env(),
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise ValueError(f"patch 생성 실패 ({commit_hash}):\n{stderr}")
    return result.stdout


def _write_commit_snapshots(
    zf: zipfile.ZipFile,
    repo_path: Path,
    commit_hash: str,
    short_hash: str,
    parents: list[str],
    index: int,
) -> list[dict]:
    files = _read_changed_files(repo_path, commit_hash, parents)
    for file_index, file_meta in enumerate(files, start=1):
        if file_meta["status"].startswith("D"):
            continue

        snapshot_name = f"snapshots/{index:04d}-{short_hash}/{file_index:04d}.bin"
        file_meta["snapshot"] = snapshot_name
        zf.writestr(snapshot_name, _read_file_at_commit(repo_path, commit_hash, file_meta["path"]))
    return files


def _read_changed_files(repo_path: Path, commit_hash: str, parents: list[str]) -> list[dict]:
    base = parents[0] if parents else EMPTY_TREE
    result = subprocess.run(
        ["git", "diff", "--name-status", "-z", "-M", base, commit_hash],
        cwd=repo_path,
        capture_output=True,
        env=_git_env(),
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise ValueError(f"변경 파일 목록 생성 실패 ({commit_hash}):\n{stderr}")

    tokens = [token for token in result.stdout.split(b"\0") if token]
    files: list[dict] = []
    cursor = 0
    while cursor < len(tokens):
        status = tokens[cursor].decode("utf-8", errors="surrogateescape")
        cursor += 1
        status_type = status[:1]
        if status_type in ("R", "C"):
            old_path = _decode_git_path(tokens[cursor])
            new_path = _decode_git_path(tokens[cursor + 1])
            cursor += 2
            file_meta = {"status": status, "path": new_path, "old_path": old_path}
        else:
            path = _decode_git_path(tokens[cursor])
            cursor += 1
            file_meta = {"status": status, "path": path}
        files.append(file_meta)
    return files


def _decode_git_path(value: bytes) -> str:
    return value.decode("utf-8", errors="surrogateescape")


def _read_file_at_commit(repo_path: Path, commit_hash: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit_hash}:{path}"],
        cwd=repo_path,
        capture_output=True,
        env=_git_env(),
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise ValueError(f"커밋 파일 내용을 읽을 수 없습니다 ({commit_hash}:{path}):\n{stderr}")
    return result.stdout


def _zip_options(compression: str) -> dict:
    if compression == "stored":
        return {"compression": zipfile.ZIP_STORED}
    if compression == "fast":
        return {"compression": zipfile.ZIP_DEFLATED, "compresslevel": 1}
    if compression == "deflated":
        return {"compression": zipfile.ZIP_DEFLATED}
    raise ValueError("patchset compression은 fast, stored, deflated 중 하나여야 합니다.")


def _is_contiguous_first_parent_series(
    replay_commits: list[Commit],
    metadata_by_hash: dict[str, dict],
) -> bool:
    if len(replay_commits) < 2:
        return True

    for previous, current in zip(replay_commits, replay_commits[1:]):
        parents = metadata_by_hash[current.hash]["parents"]
        if not parents or parents[0] != previous.hash:
            return False
    return True


def _can_use_format_patch(
    replay_commits: list[Commit],
    metadata_by_hash: dict[str, dict],
) -> bool:
    if not replay_commits:
        return False
    if not _is_contiguous_first_parent_series(replay_commits, metadata_by_hash):
        return False
    return all(metadata_by_hash[commit.hash]["parent_count"] <= 1 for commit in replay_commits)


def _load_patchset_metadata(patchset_path: Path) -> dict:
    if not patchset_path.exists():
        raise FileNotFoundError(f"patchset 파일을 찾을 수 없습니다: {patchset_path}")

    with zipfile.ZipFile(patchset_path, "r") as zf:
        try:
            metadata = json.loads(zf.read("metadata.json").decode("utf-8"))
        except KeyError as exc:
            raise ValueError("patchset metadata.json을 찾을 수 없습니다.") from exc

    if metadata.get("type") != PATCHSET_TYPE:
        raise ValueError("GitShuttle patchset 파일이 아닙니다.")
    if metadata.get("version") != PATCHSET_VERSION:
        raise ValueError(f"지원하지 않는 patchset 버전: {metadata.get('version')}")
    return metadata


def _read_patch_bytes(patchset_path: Path, patch_name: str) -> bytes:
    with zipfile.ZipFile(patchset_path, "r") as zf:
        return zf.read(patch_name)


def _ensure_worktree_repo(repo_path: Path) -> None:
    try:
        is_bare = run_git(["rev-parse", "--is-bare-repository"], cwd=repo_path).strip()
    except RuntimeError as exc:
        raise ValueError(f"Git 리포지토리가 아닙니다: {repo_path}") from exc
    if is_bare == "true":
        raise ValueError("replay import는 작업 폴더가 있는 non-bare repo에서만 사용할 수 있습니다.")


def _ensure_clean_worktree(repo_path: Path) -> None:
    status = run_git(["status", "--porcelain"], cwd=repo_path)
    if status.strip():
        raise ValueError(
            "대상 repo 작업 폴더에 커밋되지 않은 변경 사항이 있습니다.\n"
            "replay import 전에 먼저 commit/stash 하거나 정리하세요."
        )


def _checkout_target_branch(
    repo_path: Path,
    target_branch: str | None,
    start_empty: bool = False,
) -> None:
    if not target_branch:
        return

    try:
        run_git(["rev-parse", "--verify", f"refs/heads/{target_branch}"], cwd=repo_path)
        run_git(["checkout", target_branch], cwd=repo_path)
        return
    except RuntimeError:
        pass

    try:
        run_git(["rev-parse", "--verify", "HEAD"], cwd=repo_path)
        if start_empty:
            run_git(["checkout", "--orphan", target_branch], cwd=repo_path)
            _clear_orphan_worktree(repo_path)
        else:
            run_git(["checkout", "-b", target_branch], cwd=repo_path)
    except RuntimeError:
        run_git(["checkout", "--orphan", target_branch], cwd=repo_path)
        _clear_orphan_worktree(repo_path)


def _starts_with_root_commit(commits: list[dict]) -> bool:
    return bool(commits) and commits[0].get("parent_count", 0) == 0


def _clear_orphan_worktree(repo_path: Path) -> None:
    result = subprocess.run(
        ["git", "rm", "-rf", "--ignore-unmatch", "."],
        cwd=repo_path,
        capture_output=True,
        encoding="utf-8",
        env=_git_env(),
    )
    if result.returncode != 0:
        detail = "\n".join(
            part.strip() for part in (result.stdout, result.stderr) if part.strip()
        )
        raise ValueError(f"orphan 브랜치 초기화 실패:\n{detail}")


def _get_head_subject(repo_path: Path) -> str | None:
    try:
        return run_git(["log", "-1", "--format=%s"], cwd=repo_path).strip()
    except RuntimeError:
        return None


def _mapped_identity(
    name: str,
    email: str,
    author_map: dict,
    warnings: list[str],
) -> tuple[str, str]:
    if email in author_map:
        mapped = author_map[email]
        return mapped.get("name", name), mapped.get("email", email)

    if author_map:
        warning = f"미매핑 작성자: {name} <{email}>"
        if warning not in warnings:
            warnings.append(warning)
    return name, email


def _build_timestamp_plan(commits: list[dict], mode: str) -> list[tuple[str, str]]:
    if mode == "original":
        return [(c["author_date"], c["committer_date"]) for c in commits]

    if mode == "now":
        now = datetime.now(tz=timezone.utc).isoformat()
        return [(now, now) for _ in commits]

    if mode.startswith("from="):
        from_dt = _parse_from_datetime(mode[len("from="):])
        original_base = min(_parse_git_datetime(c["committer_date"]) for c in commits)
        offset = from_dt - original_base
        return [
            (
                (_parse_git_datetime(c["author_date"]) + offset).isoformat(),
                (_parse_git_datetime(c["committer_date"]) + offset).isoformat(),
            )
            for c in commits
        ]

    raise ValueError("timestamp 모드는 now, original, from=DATETIME 중 하나여야 합니다.")


def _parse_git_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_from_datetime(value: str) -> datetime:
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    raise ValueError(
        f"타임스탬프 형식을 인식할 수 없습니다: {value!r}\n"
        "허용 형식: YYYY-MM-DDTHH:MM:SS, YYYY-MM-DD HH:MM:SS, YYYY-MM-DD"
    )


def _apply_patch(repo_path: Path, patch_bytes: bytes) -> bool:
    """Apply a patch to the repo index.

    Returns False when the exact patch is already applied.
    """
    result = subprocess.run(
        ["git", "apply", "--index", "--binary", "--3way"],
        cwd=repo_path,
        input=patch_bytes,
        capture_output=True,
        env=_git_env(),
    )
    if result.returncode == 0:
        return _has_staged_changes(repo_path)

    output = _process_output(result)
    _reset_hard(repo_path)

    reverse_check = subprocess.run(
        ["git", "apply", "--reverse", "--check", "--index", "--binary"],
        cwd=repo_path,
        input=patch_bytes,
        capture_output=True,
        env=_git_env(),
    )
    if reverse_check.returncode == 0:
        return False

    raise ValueError(_format_patch_apply_failure(output))


def _force_apply_commit_snapshot(
    patchset_path: Path,
    repo_path: Path,
    commit_meta: dict,
) -> bool:
    files = commit_meta.get("files")
    if files is None:
        raise ValueError(
            "force replay에 필요한 파일 스냅샷이 patchset에 없습니다.\n"
            "최신 GitShuttle로 patchset을 다시 export한 뒤 재시도하세요."
        )

    for file_meta in files:
        status = file_meta.get("status", "")
        path = file_meta.get("path")
        if not path:
            raise ValueError("patchset 파일 스냅샷 metadata에 path가 없습니다.")

        if status.startswith("R") and file_meta.get("old_path"):
            _remove_path(repo_path, file_meta["old_path"])

        if status.startswith("D"):
            _remove_path(repo_path, path)
            continue

        snapshot = file_meta.get("snapshot")
        if not snapshot:
            raise ValueError(f"파일 스냅샷을 찾을 수 없습니다: {path}")
        _write_snapshot_file(patchset_path, repo_path, path, snapshot)

    return _has_staged_changes(repo_path)


def _write_snapshot_file(
    patchset_path: Path,
    repo_path: Path,
    path: str,
    snapshot: str,
) -> None:
    _remove_path(repo_path, path)
    target_path = _safe_repo_path(repo_path, path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(_read_patch_bytes(patchset_path, snapshot))
    _git_add_path(repo_path, path)


def _remove_path(repo_path: Path, path: str) -> None:
    result = subprocess.run(
        ["git", "rm", "-rf", "--ignore-unmatch", "--", path],
        cwd=repo_path,
        capture_output=True,
        encoding="utf-8",
        env=_git_env(),
    )
    if result.returncode != 0:
        detail = "\n".join(
            part.strip() for part in (result.stdout, result.stderr) if part.strip()
        )
        raise ValueError(f"파일 제거 실패 ({path}):\n{detail}")


def _git_add_path(repo_path: Path, path: str) -> None:
    result = subprocess.run(
        ["git", "add", "--", path],
        cwd=repo_path,
        capture_output=True,
        encoding="utf-8",
        env=_git_env(),
    )
    if result.returncode != 0:
        detail = "\n".join(
            part.strip() for part in (result.stdout, result.stderr) if part.strip()
        )
        raise ValueError(f"파일 추가 실패 ({path}):\n{detail}")


def _safe_repo_path(repo_path: Path, git_path: str) -> Path:
    root = repo_path.resolve()
    target = (root / Path(*git_path.split("/"))).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"repo 밖의 경로는 적용할 수 없습니다: {git_path}") from exc
    return target


def _reset_hard(repo_path: Path) -> None:
    subprocess.run(
        ["git", "reset", "--hard", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        env=_git_env(),
    )


def _has_staged_changes(repo_path: Path) -> bool:
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--exit-code"],
        cwd=repo_path,
        capture_output=True,
        env=_git_env(),
    )
    return result.returncode == 1


def _process_output(result: subprocess.CompletedProcess) -> str:
    stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
    stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
    return "\n".join(part.strip() for part in (stdout, stderr) if part.strip())


def _format_replay_commit_failure(
    commit_meta: dict,
    index: int,
    total: int,
    detail: str,
) -> str:
    subject = commit_meta.get("subject") or "(no subject)"
    commit_hash = commit_meta.get("hash") or "unknown"
    lines = [
        f"replay patch 적용 실패 ({index}/{total}):",
        f"- 원본 커밋: {commit_hash}",
        f"- 제목: {subject}",
        "",
        detail,
    ]
    return "\n".join(lines).rstrip()


def _format_patch_apply_failure(output: str) -> str:
    detail = output.strip()
    lines = ["replay patch 적용 실패:"]
    if detail:
        lines.extend(["", detail])

    lines.extend([
        "",
        "가능한 원인:",
        "- 대상 브랜치에 같은 경로의 파일이 이미 있지만 내용이 달라 patch를 적용할 수 없습니다.",
        "- 전체 patchset을 이미 파일이 있는 repo에 적용했거나, 이전 변경분 일부가 이미 반영되어 있습니다.",
        "- 대상 브랜치가 원본 기준과 달라져 cherry-pick/replay 충돌이 발생했습니다.",
        "",
        "해결 방법:",
        "- 이미 반영된 커밋은 선택하지 말고 그 이후 커밋만 patchset으로 다시 생성하세요.",
        "- 대상 브랜치에서 충돌 파일을 직접 정리한 뒤 다시 replay 하세요.",
        "- 전체 이력 보존이 목적이면 patchset/replay 대신 bundle import를 사용하세요.",
    ])
    return "\n".join(lines)


def _commit_index(
    repo_path: Path,
    message: str,
    author_name: str,
    author_email: str,
    author_date: str,
    committer_name: str,
    committer_email: str,
    committer_date: str,
    allow_empty: bool,
) -> None:
    env = {
        **_git_env(),
        "GIT_AUTHOR_NAME": author_name,
        "GIT_AUTHOR_EMAIL": author_email,
        "GIT_AUTHOR_DATE": author_date,
        "GIT_COMMITTER_NAME": committer_name,
        "GIT_COMMITTER_EMAIL": committer_email,
        "GIT_COMMITTER_DATE": committer_date,
    }
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
        f.write(message)
        f.write("\n")
        message_path = Path(f.name)

    try:
        cmd = ["git", "commit", "-F", str(message_path)]
        if allow_empty:
            cmd.append("--allow-empty")
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            encoding="utf-8",
            env=env,
        )
    finally:
        message_path.unlink(missing_ok=True)

    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        detail = "\n".join(part for part in (stdout, stderr) if part)
        raise ValueError(f"replay commit 생성 실패:\n{detail}")
