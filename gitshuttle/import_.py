"""import_.py — import 오케스트레이션.

run_import:
  1. SHA-256 체크섬 검증 (불일치 → ChecksumError)
  2. git bundle verify (실패 → ValueError)
  3. bundle 내 커밋 목록 조회
  4. 커밋 매칭 (skip / force / abort)
  5. git bundle unbundle → tip 해시 획득
  6. rewrite 파이프라인 (author, branch, timestamp)
  7. tip을 현재 브랜치에 merge → ImportResult 반환

모든 subprocess 호출: encoding='utf-8', env에 PYTHONIOENCODING='utf-8' 포함.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .checksum import _compute_sha256
from .bundle import verify_bundle_detailed
from .git_ops import run_git, _git_env


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ChecksumError(Exception):
    """SHA-256 체크섬 불일치."""


class ImportConflictError(Exception):
    """--on-conflict abort 상황에서 충돌 발견 시 발생."""


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ImportResult:
    imported: int          # 새로 반입된 커밋 수
    skipped: int           # 이미 존재하여 건너뛴 커밋 수
    total: int             # bundle 내 전체 커밋 수
    warnings: list[str] = field(default_factory=list)  # 미매핑 작성자 경고 목록


@dataclass(frozen=True)
class RewriteOptions:
    """rewrite import에 필요한 정규화된 옵션."""

    author_map: dict
    target_branch: str
    timestamp_mode: str
    from_dt: object | None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_import(
    bundle_path: Path | str,
    repo_path: Path | str,
    on_conflict: str = "skip",             # "skip" | "force" | "abort"
    sha256_path: Path | str | None = None,
    author_map_path: Optional[str] = None, # 작성자 매핑 JSON 경로
    target_branch: Optional[str] = None,   # 대상 브랜치 (None → "imported/<소스브랜치>")
    timestamp_mode: str = "now",           # "now" | "original" | "from=DATETIME"
) -> ImportResult:
    """bundle 파일을 target repo에 반입한다.

    Args:
        bundle_path:      반입할 .bundle 파일 경로.
        repo_path:        대상 git 리포지토리 경로.
        on_conflict:      충돌 처리 방식 — "skip" | "force" | "abort".
        sha256_path:      SHA-256 체크섬 파일 경로. 미지정 시 bundle_path.sha256 탐색.
                          체크섬 파일이 없으면 경고 출력 후 검증 생략.
        author_map_path:  작성자 매핑 JSON 파일 경로. None 이면 치환 없음.
        target_branch:    import 대상 브랜치 이름.
                          None 이면 "imported/<소스브랜치>" 형식 자동 생성.
        timestamp_mode:   타임스탬프 재작성 모드.
                          "now"(기본) | "original" | "from=YYYY-MM-DDTHH:MM:SS"

    Returns:
        ImportResult (imported, skipped, total, warnings 포함).

    Raises:
        FileNotFoundError:    bundle 파일이 존재하지 않을 때.
        ChecksumError:        체크섬 불일치 (파일이 있는 경우).
        ValueError:           bundle verify 실패.
        ImportConflictError:  on_conflict="abort" 이고 이미 존재하는 커밋이 있을 때.
    """
    bundle_path = Path(bundle_path)
    repo_path = Path(repo_path)

    if not bundle_path.exists():
        raise FileNotFoundError(f"bundle 파일을 찾을 수 없습니다: {bundle_path}")

    _verify_checksum(bundle_path, sha256_path)

    verify_result = verify_bundle_detailed(bundle_path, repo_path=repo_path)
    if not verify_result.valid:
        raise ValueError(_format_bundle_verify_failure(bundle_path, verify_result.message))

    existing_hashes_before = _get_existing_hashes(repo_path)
    bundle_tips = _get_bundle_commits(bundle_path)
    duplicates = _find_duplicates(bundle_tips, existing_hashes_before)
    _handle_duplicates(duplicates, on_conflict)

    rewrite_needed = _needs_rewrite(author_map_path, target_branch, timestamp_mode)
    rewrite_warnings: list[str] = []
    if rewrite_needed:
        rewrite_options = _build_rewrite_options(
            bundle_path=bundle_path,
            author_map_path=author_map_path,
            target_branch=target_branch,
            timestamp_mode=timestamp_mode,
        )
        tip_hashes, rewrite_warnings = _rewrite_and_import(
            bundle_path=bundle_path,
            repo_path=repo_path,
            author_map=rewrite_options.author_map,
            target_branch=rewrite_options.target_branch,
            timestamp_mode=rewrite_options.timestamp_mode,
            from_dt=rewrite_options.from_dt,
            force_ref_update=on_conflict == "force",
        )
    else:
        tip_hashes = _unbundle(bundle_path, repo_path)
        for tip_hash in tip_hashes:
            _merge_tip(repo_path, tip_hash)

    return _build_import_result(
        repo_path=repo_path,
        tip_hashes=tip_hashes,
        existing_hashes_before=existing_hashes_before,
        duplicates=duplicates,
        on_conflict=on_conflict,
        rewrite_needed=rewrite_needed,
        warnings=rewrite_warnings,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_duplicates(bundle_tips: list[str], existing_hashes: set[str]) -> list[str]:
    return [commit_hash for commit_hash in bundle_tips if commit_hash in existing_hashes]


def _handle_duplicates(duplicates: list[str], on_conflict: str) -> None:
    if duplicates and on_conflict == "abort":
        raise ImportConflictError(
            f"이미 존재하는 커밋이 있습니다. (on_conflict=abort)\n"
            f"첫 번째 중복: {duplicates[0]}"
        )


def _needs_rewrite(
    author_map_path: Optional[str],
    target_branch: Optional[str],
    timestamp_mode: str,
) -> bool:
    return (
        author_map_path is not None
        or target_branch is not None
        or timestamp_mode != "now"
    )


def _build_rewrite_options(
    *,
    bundle_path: Path,
    author_map_path: Optional[str],
    target_branch: Optional[str],
    timestamp_mode: str,
) -> RewriteOptions:
    source_branch = _detect_source_branch(bundle_path)
    effective_target_branch = target_branch or f"imported/{source_branch}"
    effective_ts_mode = timestamp_mode
    from_dt = None

    if timestamp_mode.startswith("from="):
        from_dt = _parse_from_datetime(timestamp_mode[len("from="):])
        effective_ts_mode = "from"

    from .rewrite import load_author_map

    return RewriteOptions(
        author_map=load_author_map(author_map_path) if author_map_path else {},
        target_branch=effective_target_branch,
        timestamp_mode=effective_ts_mode,
        from_dt=from_dt,
    )


def _build_import_result(
    *,
    repo_path: Path,
    tip_hashes: list[str],
    existing_hashes_before: set[str],
    duplicates: list[str],
    on_conflict: str,
    rewrite_needed: bool,
    warnings: list[str],
) -> ImportResult:
    if rewrite_needed:
        hashes_after = _get_reachable_hashes(repo_path, tip_hashes)
    else:
        hashes_after = _get_existing_hashes(repo_path)

    imported = len(hashes_after - existing_hashes_before)
    skipped = len(duplicates) if on_conflict == "skip" else 0
    return ImportResult(
        imported=imported,
        skipped=skipped,
        total=imported + skipped,
        warnings=warnings,
    )


def _verify_checksum(
    bundle_path: Path,
    sha256_path: Path | str | None,
) -> None:
    """SHA-256 체크섬을 검증한다.

    체크섬 파일이 없으면 경고 출력 후 생략한다.
    불일치 시 ChecksumError 를 발생시킨다.
    """
    if sha256_path is None:
        candidate = bundle_path.with_suffix(bundle_path.suffix + ".sha256")
        if not candidate.exists():
            # 체크섬 파일 없음 → 경고만 출력하고 계속
            import sys
            print(
                f"[경고] 체크섬 파일을 찾을 수 없습니다: {candidate}\n"
                "SHA-256 검증을 생략합니다.",
                file=sys.stderr,
            )
            return
        sha256_path = candidate
    else:
        sha256_path = Path(sha256_path)

    if not sha256_path.exists():
        import sys
        print(
            f"[경고] 지정된 체크섬 파일이 없습니다: {sha256_path}\n"
            "SHA-256 검증을 생략합니다.",
            file=sys.stderr,
        )
        return

    # 체크섬 파일 파싱
    content = sha256_path.read_text(encoding='utf-8').strip()
    parts = content.split("  ", 1)
    if len(parts) != 2:
        raise ChecksumError(
            f"체크섬 파일 형식이 잘못되었습니다: {sha256_path}\n"
            "재export 방법: gitshuttle export 를 다시 실행하세요."
        )
    expected_hex = parts[0].strip()

    actual_hex = _compute_sha256(bundle_path)

    if actual_hex != expected_hex:
        raise ChecksumError(
            f"SHA-256 체크섬 불일치!\n"
            f"  기대값 (expected): {expected_hex}\n"
            f"  실제값 (actual):   {actual_hex}\n"
            f"\n파일이 손상되었을 수 있습니다.\n"
            f"재export 방법: 소스 측에서 'gitshuttle export' 를 다시 실행하세요."
        )


def _format_bundle_verify_failure(bundle_path: Path, detail: str) -> str:
    """bundle verify 실패 원인과 복구 방법을 사용자에게 안내한다."""
    lines = [f"bundle 검증 실패: {bundle_path}"]
    if detail:
        lines.extend(["", detail])

    lines.extend([
        "",
        "가능한 원인:",
        "- 최근 1~2개처럼 일부 커밋만 export한 bundle은 대상 repo에 그 직전 원본 부모 커밋 SHA가 있어야 합니다.",
        "- 대상 repo에 이전 이력이 없거나, 작성자/날짜 rewrite로 기존 커밋 SHA가 바뀐 경우 prerequisite 검증에 실패합니다.",
        "- 최신 GitShuttle은 rewrite import 시 원본 SHA를 refs/gitshuttle/original 아래 보관해 이후 증분 import를 지원합니다.",
        "",
        "해결 방법:",
        "- 대상 repo에 원본 부모 커밋이 있는지 확인하세요.",
        "- 기존 버전으로 이미 rewrite import한 repo라면, 한 번은 필요한 전체 범위를 다시 export/import해 증분 기준점을 만드세요.",
        "- 안전하게는 새 --target-branch 이름으로 전체 이력을 다시 import한 뒤 검토하세요.",
    ])
    return "\n".join(lines)


def _get_bundle_commits(bundle_path: Path) -> list[str]:
    """bundle 파일에 포함된 커밋 해시 목록을 반환한다.

    git bundle list-heads で ref tip を取得し、임시 bare repo에 fetch 후
    rev-list로 전체 커밋 목록을 추출한다.
    """
    import subprocess
    import tempfile
    import shutil

    # Step 1: list-heads로 bundle 내 ref tip 해시 수집
    lh_result = subprocess.run(
        ["git", "bundle", "list-heads", str(bundle_path)],
        capture_output=True,
        encoding='utf-8',
        env=_git_env(),
    )
    if lh_result.returncode != 0 or not lh_result.stdout.strip():
        return []

    tip_hashes = []
    for line in lh_result.stdout.strip().splitlines():
        parts = line.strip().split(None, 1)
        if parts:
            tip_hashes.append(parts[0])

    if not tip_hashes:
        return []

    # Step 2: 임시 bare repo에 bundle을 fetch (명시적 refspec 사용)
    tmp_dir = Path(tempfile.mkdtemp(prefix="gs_bundle_"))
    try:
        subprocess.run(
            ["git", "init", "--bare", str(tmp_dir)],
            capture_output=True,
            encoding='utf-8',
            env=_git_env(),
            check=True,
        )

        # 명시적 refspec으로 bundle의 모든 refs를 가져옴
        fetch_result = subprocess.run(
            ["git", "fetch", str(bundle_path), "+refs/*:refs/*"],
            cwd=tmp_dir,
            capture_output=True,
            encoding='utf-8',
            env=_git_env(),
        )
        if fetch_result.returncode != 0:
            return tip_hashes  # fallback: tip hashes만 반환

        # Step 3: rev-list로 전체 커밋 나열
        rev_result = subprocess.run(
            ["git", "rev-list", "--all"],
            cwd=tmp_dir,
            capture_output=True,
            encoding='utf-8',
            env=_git_env(),
        )
        if rev_result.returncode != 0:
            return tip_hashes

        all_commits = [h.strip() for h in rev_result.stdout.splitlines() if h.strip()]
        return all_commits if all_commits else tip_hashes

    except Exception:
        return tip_hashes
    finally:
        shutil.rmtree(str(tmp_dir), ignore_errors=True)


def _get_existing_hashes(repo_path: Path) -> set[str]:
    """target repo에 존재하는 모든 커밋 해시 집합을 반환한다."""
    import subprocess

    result = subprocess.run(
        ["git", "rev-list", "--all"],
        cwd=repo_path,
        capture_output=True,
        encoding='utf-8',
        env=_git_env(),
    )
    if result.returncode != 0:
        return set()

    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _get_reachable_hashes(repo_path: Path, tips: list[str]) -> set[str]:
    """지정 tip들에서 도달 가능한 커밋 해시 집합을 반환한다."""
    if not tips:
        return set()

    result = subprocess.run(
        ["git", "rev-list", *tips],
        cwd=repo_path,
        capture_output=True,
        encoding='utf-8',
        env=_git_env(),
    )
    if result.returncode != 0:
        return set()

    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _unbundle(bundle_path: Path, repo_path: Path) -> list[str]:
    """git bundle unbundle로 objects를 target repo에 추가하고 tip 해시 목록을 반환한다.

    git remote + fetch 방식은 refs/gitshuttle/* 같은 커스텀 ref를 가져오지 못하므로
    git bundle unbundle을 사용한다. stdout에 "hash ref" 형식으로 tip 목록이 출력된다.
    """
    result = subprocess.run(
        ["git", "bundle", "unbundle", str(bundle_path)],
        cwd=repo_path,
        capture_output=True,
        encoding='utf-8',
        env=_git_env(),
    )
    if result.returncode != 0:
        raise ValueError(f"bundle unbundle 실패:\n{result.stderr}")

    tip_hashes = []
    for line in result.stdout.strip().splitlines():
        parts = line.strip().split()
        if parts:
            tip_hashes.append(parts[0])

    return tip_hashes


def _merge_tip(repo_path: Path, tip_hash: str) -> None:
    """tip_hash를 현재 브랜치에 merge한다.

    빈 repo(커밋 없음): checkout -b main <hash> → merge commit 없음.
    공통 히스토리: fast-forward → merge commit 없음.
    무관한 히스토리: --no-ff --allow-unrelated-histories -Xours.
    """
    # 빈 repo 감지 — HEAD가 없으면 브랜치만 생성하고 종료 (merge commit 없음)
    try:
        run_git(["rev-parse", "--verify", "HEAD"], cwd=repo_path)
    except RuntimeError:
        # 빈 repo: checkout -b로 브랜치 생성
        try:
            run_git(["checkout", "-b", "main", tip_hash], cwd=repo_path)
        except RuntimeError:
            run_git(["checkout", tip_hash], cwd=repo_path)
        return

    # 이미 ancestor이면 merge 불필요
    try:
        run_git(["merge-base", "--is-ancestor", tip_hash, "HEAD"], cwd=repo_path)
        return
    except RuntimeError:
        pass

    # Fast-forward 시도 (공통 히스토리 → merge commit 없음)
    try:
        run_git(["merge", "--ff-only", tip_hash], cwd=repo_path)
        return
    except RuntimeError:
        pass

    # Fast-forward 불가 → --no-ff merge (unrelated histories + 충돌 자동 해결)
    try:
        run_git(
            ["merge", "--no-ff", "--allow-unrelated-histories", "-Xours",
             "-m", "GitShuttle import merge", tip_hash],
            cwd=repo_path,
        )
    except RuntimeError:
        try:
            run_git(["merge", "--abort"], cwd=repo_path)
        except RuntimeError:
            pass
        raise


def _detect_source_branch(bundle_path: Path) -> str:
    """bundle 파일에서 소스 브랜치 이름을 감지한다.

    git bundle list-heads 출력의 첫 번째 ref에서 브랜치 이름을 추출.
    감지 실패 시 "main"을 반환.
    """
    result = subprocess.run(
        ["git", "bundle", "list-heads", str(bundle_path)],
        capture_output=True,
        encoding='utf-8',
        env=_git_env(),
    )
    if result.returncode != 0 or not result.stdout.strip():
        return "main"

    for line in result.stdout.strip().splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            ref = parts[1]
            if ref.startswith("refs/heads/"):
                return ref[len("refs/heads/"):]

    return "main"


def _parse_from_datetime(dt_str: str):
    """'from=YYYY-MM-DDTHH:MM:SS' 형식의 문자열을 datetime으로 파싱한다.

    timezone 없으면 UTC로 처리.
    """
    from datetime import datetime, timezone

    # 지원 형식 목록
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(dt_str.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    raise ValueError(
        f"타임스탬프 형식을 인식할 수 없습니다: {dt_str!r}\n"
        "허용 형식: YYYY-MM-DDTHH:MM:SS, YYYY-MM-DD HH:MM:SS, YYYY-MM-DD"
    )


def _rewrite_and_import(
    bundle_path: Path,
    repo_path: Path,
    author_map: dict,
    target_branch: str,
    timestamp_mode: str,
    from_dt,
    force_ref_update: bool = False,
) -> tuple[list[str], list[str]]:
    """fast-export → apply_rewrites → fast-import 파이프라인.

    1. 임시 bare repo에 bundle을 fetch
    2. git fast-export로 스트림 추출
    3. apply_rewrites로 재작성
    4. git fast-import로 target repo에 반영
    5. target_branch로 checkout/reset 하여 worktree 갱신

    Returns:
        (tip_hashes, warnings)
    """
    import tempfile
    import shutil
    from .rewrite import apply_rewrites

    tmp_dir = Path(tempfile.mkdtemp(prefix="gs_rewrite_"))
    try:
        # 임시 bare repo 초기화
        subprocess.run(
            ["git", "init", "--bare", str(tmp_dir)],
            capture_output=True,
            encoding='utf-8',
            env=_git_env(),
            check=True,
        )

        _fetch_original_shadow_refs(repo_path, tmp_dir)

        # bundle → 임시 bare repo fetch
        fetch_result = subprocess.run(
            ["git", "fetch", str(bundle_path), "+refs/*:refs/*"],
            cwd=tmp_dir,
            capture_output=True,
            encoding='utf-8',
            env=_git_env(),
        )
        if fetch_result.returncode != 0:
            raise ValueError(f"bundle fetch 실패:\n{fetch_result.stderr}")

        _delete_original_shadow_refs(tmp_dir)

        # 임시 bare repo에서 fast-export 스트림 추출
        export_result = subprocess.run(
            ["git", "fast-export", "--all"],
            cwd=tmp_dir,
            capture_output=True,
            encoding='utf-8',
            errors='surrogateescape',
            env=_git_env(),
        )
        if export_result.returncode != 0:
            raise ValueError(f"fast-export 실패:\n{export_result.stderr}")

        stream = export_result.stdout

        # rewrite 파이프라인 적용
        rewritten_stream, warnings = apply_rewrites(
            stream=stream,
            author_map=author_map,
            target_branch=target_branch,
            timestamp_mode=timestamp_mode,
            from_dt=from_dt,
        )

        _ensure_clean_worktree(repo_path)

        # target repo에 git fast-import로 반영
        # 바이너리 모드로 전달해야 Windows에서 \r\n 변환을 방지할 수 있음
        fi_env = {
            **_git_env(),
            'GIT_AUTHOR_NAME': 'GitShuttle',
            'GIT_AUTHOR_EMAIL': 'gitshuttle@local',
            'GIT_COMMITTER_NAME': 'GitShuttle',
            'GIT_COMMITTER_EMAIL': 'gitshuttle@local',
        }
        fast_import_cmd = ["git", "fast-import", "--quiet"]
        if force_ref_update:
            fast_import_cmd.append("--force")

        import_result = subprocess.run(
            fast_import_cmd,
            cwd=repo_path,
            input=rewritten_stream.encode('utf-8', errors='surrogateescape'),
            capture_output=True,
            env=fi_env,
        )
        if import_result.returncode != 0:
            stderr_text = import_result.stderr.decode('utf-8', errors='replace') if import_result.stderr else ''
            if "Not updating refs/heads/" in stderr_text and "does not contain" in stderr_text:
                raise ValueError(
                    "fast-import 실패:\n"
                    f"{stderr_text}\n"
                    f"대상 브랜치 '{target_branch}'가 이미 존재하지만, "
                    "이번 import 이력이 기존 브랜치 tip을 포함하지 않습니다.\n"
                    "해결 방법: 다른 --target-branch 이름을 사용하거나, "
                    "기존 로컬 브랜치를 삭제한 뒤 다시 import하거나, "
                    "덮어써도 된다면 --on-conflict force 옵션을 사용하세요."
                )
            raise ValueError(f"fast-import 실패:\n{stderr_text}")

        shadow_warning = _store_original_bundle_refs(bundle_path, repo_path, target_branch)
        if shadow_warning:
            warnings.append(shadow_warning)

        # target_branch에서 HEAD 업데이트 (checkout or reset)
        tip_hashes = _checkout_or_create_branch(repo_path, target_branch)

        return tip_hashes, warnings

    finally:
        shutil.rmtree(str(tmp_dir), ignore_errors=True)


def _checkout_or_create_branch(repo_path: Path, branch: str) -> list[str]:
    """target_branch로 checkout/reset 한 뒤 tip 해시를 반환한다.

    fast-import는 ref와 object DB를 갱신하지만 worktree/index는 자동 갱신하지 않는다.
    일반 repo에서는 checkout + reset --hard로 작업 폴더를 import 결과와 맞춘다.
    bare repo에서는 worktree가 없으므로 tip 해시만 반환한다.

    브랜치가 없으면 빈 리스트 반환.
    """
    try:
        tip = run_git(
            ["rev-parse", f"refs/heads/{branch}"],
            cwd=repo_path,
        ).strip()
    except RuntimeError:
        return []

    if not tip:
        return []

    if _is_bare_repo(repo_path):
        return [tip]

    run_git(["checkout", branch], cwd=repo_path)
    run_git(["reset", "--hard", tip], cwd=repo_path)
    return [tip]


def _is_bare_repo(repo_path: Path) -> bool:
    """repo_path가 bare repository인지 반환한다."""
    try:
        return run_git(["rev-parse", "--is-bare-repository"], cwd=repo_path).strip() == "true"
    except RuntimeError:
        return False


def _ensure_clean_worktree(repo_path: Path) -> None:
    """fast-import 후 reset 전에 사용자 변경이 덮이지 않도록 사전 확인한다."""
    if _is_bare_repo(repo_path):
        return

    try:
        status = run_git(["status", "--porcelain"], cwd=repo_path)
    except RuntimeError:
        return

    if status.strip():
        raise ValueError(
            "대상 repo 작업 폴더에 커밋되지 않은 변경 사항이 있습니다.\n"
            "import 후 target branch로 checkout/reset 해야 하므로, 먼저 변경 사항을 "
            "commit/stash 하거나 정리한 뒤 다시 실행하세요."
        )


def _fetch_original_shadow_refs(repo_path: Path, tmp_dir: Path) -> None:
    """target repo의 원본 SHA shadow refs를 임시 repo로 가져온다.

    rewrite import 후속 증분 bundle은 원본 부모 SHA를 prerequisite로 요구한다.
    이전 import에서 보관한 refs/gitshuttle/original/* refs를 임시 repo에 먼저
    가져와야 부분 bundle fetch/fast-export가 가능하다.
    """
    try:
        refs = run_git(
            ["for-each-ref", "--format=%(refname)", "refs/gitshuttle/original"],
            cwd=repo_path,
        )
    except RuntimeError:
        return

    if not refs.strip():
        return

    result = subprocess.run(
        [
            "git",
            "fetch",
            str(repo_path),
            "+refs/gitshuttle/original/*:refs/gitshuttle/original/*",
        ],
        cwd=tmp_dir,
        capture_output=True,
        encoding='utf-8',
        env=_git_env(),
    )
    if result.returncode != 0:
        raise ValueError(f"원본 SHA shadow refs fetch 실패:\n{result.stderr}")


def _delete_original_shadow_refs(tmp_dir: Path) -> None:
    """임시 repo에서 shadow refs만 삭제하고 object는 남겨 fast-export 대상을 제한한다."""
    try:
        refs = run_git(
            ["for-each-ref", "--format=%(refname)", "refs/gitshuttle/original"],
            cwd=tmp_dir,
        )
    except RuntimeError:
        return

    for ref in refs.splitlines():
        ref = ref.strip()
        if not ref:
            continue
        try:
            run_git(["update-ref", "-d", ref], cwd=tmp_dir)
        except RuntimeError:
            pass


def _store_original_bundle_refs(
    bundle_path: Path,
    repo_path: Path,
    target_branch: str,
) -> str | None:
    """원본 bundle refs를 hidden namespace에 보관해 다음 증분 import 기준점으로 삼는다."""
    refspec = f"+refs/*:refs/gitshuttle/original/{target_branch}/*"
    result = subprocess.run(
        ["git", "fetch", str(bundle_path), refspec],
        cwd=repo_path,
        capture_output=True,
        encoding='utf-8',
        env=_git_env(),
    )
    if result.returncode == 0:
        return None

    return (
        "원본 SHA shadow refs 보관 실패: 이후 부분 bundle 증분 import가 실패할 수 있습니다.\n"
        f"{result.stderr.strip()}"
    )
