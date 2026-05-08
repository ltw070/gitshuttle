"""import_.py — import 오케스트레이션.

run_import:
  1. SHA-256 체크섬 검증 (불일치 → ChecksumError)
  2. git bundle verify (실패 → ValueError)
  3. bundle 내 커밋 목록 조회
  4. 커밋 매칭 (skip / force / abort)
  5. git bundle unbundle → tip 해시 획득
  6. tip을 현재 브랜치에 merge → ImportResult 반환

모든 subprocess 호출: encoding='utf-8', env에 PYTHONIOENCODING='utf-8' 포함.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .checksum import _compute_sha256
from .bundle import verify_bundle
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
    imported: int   # 새로 반입된 커밋 수
    skipped: int    # 이미 존재하여 건너뛴 커밋 수
    total: int      # bundle 내 전체 커밋 수


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_import(
    bundle_path: Path | str,
    repo_path: Path | str,
    on_conflict: str = "skip",   # "skip" | "force" | "abort"
    sha256_path: Path | str | None = None,
) -> ImportResult:
    """bundle 파일을 target repo에 반입한다.

    Args:
        bundle_path:  반입할 .bundle 파일 경로.
        repo_path:    대상 git 리포지토리 경로.
        on_conflict:  충돌 처리 방식 — "skip" | "force" | "abort".
        sha256_path:  SHA-256 체크섬 파일 경로. 미지정 시 bundle_path.sha256 탐색.
                      체크섬 파일이 없으면 경고 출력 후 검증 생략.

    Returns:
        ImportResult (imported, skipped, total 포함).

    Raises:
        FileNotFoundError:    bundle 파일이 존재하지 않을 때.
        ChecksumError:        체크섬 불일치 (파일이 있는 경우).
        ValueError:           bundle verify 실패.
        ImportConflictError:  on_conflict="abort" 이고 이미 존재하는 커밋이 있을 때.
    """
    bundle_path = Path(bundle_path)
    repo_path = Path(repo_path)

    # ------------------------------------------------------------------
    # Step 1. bundle 파일 존재 확인
    # ------------------------------------------------------------------
    if not bundle_path.exists():
        raise FileNotFoundError(f"bundle 파일을 찾을 수 없습니다: {bundle_path}")

    # ------------------------------------------------------------------
    # Step 2. SHA-256 체크섬 검증
    # ------------------------------------------------------------------
    _verify_checksum(bundle_path, sha256_path)

    # ------------------------------------------------------------------
    # Step 3. git bundle verify
    # ------------------------------------------------------------------
    if not verify_bundle(bundle_path):
        raise ValueError(f"bundle 검증 실패: {bundle_path}")

    # ------------------------------------------------------------------
    # Step 4. bundle 내 커밋 목록 조회
    # ------------------------------------------------------------------
    bundle_commits = _get_bundle_commits(bundle_path)
    total = len(bundle_commits)

    # ------------------------------------------------------------------
    # Step 5. target repo의 기존 커밋 해시 집합
    # ------------------------------------------------------------------
    existing_hashes = _get_existing_hashes(repo_path)

    # ------------------------------------------------------------------
    # Step 6. 충돌(이미 존재하는 커밋) 처리
    # ------------------------------------------------------------------
    duplicates = [c for c in bundle_commits if c in existing_hashes]

    if duplicates:
        if on_conflict == "abort":
            raise ImportConflictError(
                f"이미 존재하는 커밋 {len(duplicates)}개가 있습니다. "
                f"(on_conflict=abort)\n"
                f"첫 번째 중복 커밋: {duplicates[0]}"
            )
        # skip / force: fetch는 항상 수행, 이후 merge에서 처리

    # ------------------------------------------------------------------
    # Step 7. bundle unbundle — objects를 target repo에 추가하고 tip 해시 획득
    # git bundle unbundle은 refs/gitshuttle/* 등 커스텀 ref도 정상 처리
    # ------------------------------------------------------------------
    tip_hashes = _unbundle(bundle_path, repo_path)

    # ------------------------------------------------------------------
    # Step 8. tip 해시를 현재 브랜치에 merge
    # ------------------------------------------------------------------
    for tip_hash in tip_hashes:
        _merge_tip(repo_path, tip_hash)

    # ------------------------------------------------------------------
    # Step 9. ImportResult 계산
    # ------------------------------------------------------------------
    skipped = len(duplicates) if on_conflict == "skip" else 0
    imported = total - skipped

    return ImportResult(imported=imported, skipped=skipped, total=total)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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
