"""Patchset export/import for replay-style transfers."""
from __future__ import annotations

import json
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


@dataclass
class ReplayResult:
    """Result of replaying a patchset."""

    imported: int
    skipped: int
    total: int
    warnings: list[str] = field(default_factory=list)


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
    replay_commits = list(reversed(commits))
    metadata_by_hash = _read_commits_metadata(repo_path, replay_commits)

    metadata: dict = {
        "type": PATCHSET_TYPE,
        "version": PATCHSET_VERSION,
        "branch": branch,
        "selection": {
            "contiguous_first_parent": _is_contiguous_first_parent_series(
                replay_commits,
                metadata_by_hash,
            ),
            "patch_source": "per-commit-diff",
        },
        "commits": [],
    }

    with zipfile.ZipFile(patchset_path, "w", **_zip_options(compression)) as zf:
        for index, commit in enumerate(replay_commits, start=1):
            patch_name = f"patches/{index:04d}-{commit.short_hash}.patch"
            commit_meta = metadata_by_hash[commit.hash]
            commit_meta["patch"] = patch_name
            metadata["commits"].append(commit_meta)
            zf.writestr(
                patch_name,
                _read_commit_patch(repo_path, commit.hash, commit_meta["parents"]),
            )

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
    confirm_duplicate_message: Callable[[str, str], bool] | None = None,
) -> ReplayResult:
    """Replay a patchset onto the target repository's current HEAD.

    This is intentionally cherry-pick-like: commits are recreated on top of the
    target branch, so original commit SHA and merge topology are not preserved.
    """
    patchset_path = Path(patchset_path)
    repo_path = Path(repo_path)
    metadata = _load_patchset_metadata(patchset_path)
    commits = metadata["commits"]
    if not commits:
        return ReplayResult(imported=0, skipped=0, total=0)

    _ensure_worktree_repo(repo_path)
    _ensure_clean_worktree(repo_path)
    _checkout_target_branch(repo_path, target_branch)
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
        patch_bytes = _read_patch_bytes(patchset_path, commit_meta["patch"])
        patch_applied = bool(patch_bytes.strip())
        if patch_applied:
            applied = _apply_patch(repo_path, patch_bytes)
            if not applied:
                skipped += 1
                warnings.append(
                    f"이미 적용된 replay patch 건너뜀: {commit_meta.get('subject', '')}"
                )
                continue

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
        author_date, committer_date = timestamp_plan[index]
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
        imported += 1

    return ReplayResult(
        imported=imported,
        skipped=skipped,
        total=len(commits),
        warnings=warnings,
    )


def _read_commit_metadata(repo_path: Path, commit_hash: str) -> dict:
    return _read_commits_metadata(repo_path, [Commit(
        hash=commit_hash,
        short_hash=commit_hash[:7],
        date="",
        author="",
        message="",
        files_changed=0,
    )])[commit_hash]


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


def _checkout_target_branch(repo_path: Path, target_branch: str | None) -> None:
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
        run_git(["checkout", "-b", target_branch], cwd=repo_path)
    except RuntimeError:
        run_git(["checkout", "--orphan", target_branch], cwd=repo_path)


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

    stderr = result.stderr.decode("utf-8", errors="replace")
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

    raise ValueError(_format_patch_apply_failure(stderr))


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


def _format_patch_apply_failure(stderr: str) -> str:
    detail = stderr.strip()
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
