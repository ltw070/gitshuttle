"""bundle.py — git bundle 생성/검증.

create_bundle: 선택한 커밋들을 .bundle 파일로 생성.
verify_bundle: git bundle verify 로 무결성 검증.

git bundle create 동작 방식:
  - 단순 커밋 해시만 전달하면 "Refusing to create empty bundle" 오류 발생.
  - 반드시 ref(브랜치명, HEAD, refs/...) 를 포함해야 한다.
  - 전략: 임시 ref (refs/gitshuttle/tmp_<newest_short>) 를 생성 후
    bundle 완료 시 즉시 삭제한다. 부분 범위는 exclusion ref(^parent) 사용.
  - base_refs 가 있으면 base metadata ref 도 함께 담아 self-contained bundle을
    만든다. import 단계는 metadata ref를 기준으로 delta만 다시 export한다.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .git_ops import run_git, Commit, _git_env


# 임시 ref 네임스페이스 — 다른 refs 와 충돌하지 않도록
_TMP_REF_NS = "refs/gitshuttle/tmp"
_BASE_REF_NS = "refs/gitshuttle/base"


@dataclass
class BundleVerifyResult:
    """git bundle verify 실행 결과."""
    valid: bool
    message: str = ""


def create_bundle(
    repo_path: Path | str,
    commits: list[Commit],
    output_dir: Path | str,
    filename: str | None = None,
    scope: str = "range",
    base_refs: list[str] | None = None,
) -> Path:
    """선택한 커밋들을 .bundle 파일로 생성한다.

    Args:
        repo_path:  소스 git 리포지토리 경로.
        commits:    bundle에 포함할 Commit 객체 목록 (최신순, get_commits 반환 순서).
        output_dir: bundle 파일을 저장할 디렉토리.
        filename:   출력 파일명. 미지정 시 shuttle_YYMMDD.bundle.
        scope:      "range"는 선택 범위만, "full"은 tip까지 전체 이력을 포함.
        base_refs:  base..branch export 기준점. 지정 시 bundle은 검증 가능하도록
                    self-contained로 만들고, base commit을 metadata ref로 표시한다.

    Returns:
        생성된 bundle 파일의 절대 Path.

    Raises:
        ValueError: commits 가 비어있을 때.
    """
    if not commits:
        raise ValueError("commits 목록이 비어있습니다. 최소 1개의 커밋이 필요합니다.")
    if scope not in ("range", "full"):
        raise ValueError("bundle scope는 range 또는 full 이어야 합니다.")

    repo_path = Path(repo_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        date_str = datetime.now().strftime("%y%m%d")
        filename = f"shuttle_{date_str}.bundle"

    bundle_path = output_dir / filename

    # commits 는 최신순 정렬 (index 0 = 최신, index -1 = 가장 오래된)
    newest = commits[0]
    oldest = commits[-1]

    # 임시 ref 이름 (충돌 방지를 위해 short_hash 포함)
    tmp_ref = f"{_TMP_REF_NS}_{newest.short_hash}"

    # 임시 ref 등록
    run_git(["update-ref", tmp_ref, newest.hash], cwd=repo_path)
    base_ref_names: list[str] = []

    try:
        base_ref_names = _create_base_metadata_refs(
            repo_path=repo_path,
            base_refs=base_refs or [],
            namespace_suffix=newest.short_hash,
        )

        # bundle 범위 인자 계산
        bundle_args = _build_bundle_args(
            repo_path,
            oldest.hash,
            tmp_ref,
            scope=scope,
            base_ref_names=base_ref_names,
        )

        run_git(
            ["bundle", "create", str(bundle_path)] + bundle_args,
            cwd=repo_path,
        )
    finally:
        # 임시 ref 반드시 삭제
        _delete_refs(repo_path, [tmp_ref, *base_ref_names])

    return bundle_path


def _build_bundle_args(
    repo_path: Path,
    oldest_hash: str,
    tmp_ref: str,
    scope: str = "range",
    base_ref_names: list[str] | None = None,
) -> list[str]:
    """git bundle create 에 전달할 인자 목록을 반환한다.

    루트 커밋(부모 없음)이 포함된 경우:
      → [tmp_ref]  (전체 히스토리 포함)
    일반 경우:
      → [^<oldest_parent>, tmp_ref]  (범위 지정)
    """
    if base_ref_names:
        return [tmp_ref, *base_ref_names]

    if scope == "full":
        return [tmp_ref]

    # 가장 오래된 커밋의 부모 확인
    try:
        parent_out = run_git(
            ["rev-list", "--parents", "-n", "1", oldest_hash],
            cwd=repo_path,
        )
        parts = parent_out.strip().split()
        parents = parts[1:]  # parts[0] = oldest_hash 자신
    except RuntimeError:
        parents = []

    if not parents:
        # 루트 커밋 포함 → 전체 히스토리 번들
        return [tmp_ref]
    else:
        # 부분 범위: 가장 오래된 커밋의 부모들을 제외
        exclude_args = [f"^{p}" for p in parents]
        return exclude_args + [tmp_ref]


def _create_base_metadata_refs(
    repo_path: Path,
    base_refs: list[str],
    namespace_suffix: str,
) -> list[str]:
    """base refs를 임시 metadata ref로 등록하고 ref 이름 목록을 반환한다."""
    created: list[str] = []
    try:
        for index, base_ref in enumerate(base_refs):
            commit_hash = run_git(
                ["rev-parse", "--verify", f"{base_ref}^{{commit}}"],
                cwd=repo_path,
            ).strip()
            metadata_ref = f"{_BASE_REF_NS}/{namespace_suffix}_{index}_{commit_hash[:12]}"
            run_git(["update-ref", metadata_ref, commit_hash], cwd=repo_path)
            created.append(metadata_ref)
        return created
    except RuntimeError:
        _delete_refs(repo_path, created)
        raise


def _delete_refs(repo_path: Path, refs: list[str]) -> None:
    for ref in refs:
        try:
            run_git(["update-ref", "-d", ref], cwd=repo_path)
        except RuntimeError:
            pass


def split_bundle(bundle_path: Path | str, chunk_bytes: int) -> list[Path]:
    """bundle 파일을 chunk_bytes 크기로 분할한다.

    분할 파일명: <basename>.part000, .part001, ... (3자리 zero-pad)
    같은 디렉터리에 생성한다.

    Args:
        bundle_path:  분할할 bundle 파일 경로.
        chunk_bytes:  각 파트의 최대 바이트 크기.

    Returns:
        분할된 파일 경로 목록 (순서 보장).

    Raises:
        ValueError: chunk_bytes <= 0 일 때.
    """
    if chunk_bytes <= 0:
        raise ValueError(f"chunk_bytes는 1 이상이어야 합니다. 입력값: {chunk_bytes}")

    bundle_path = Path(bundle_path)
    parent = bundle_path.parent
    # 확장자를 포함한 전체 파일명을 base로 사용 (.bundle 포함)
    base_name = bundle_path.name  # e.g. "shuttle_260508.bundle"

    parts: list[Path] = []
    data = bundle_path.read_bytes()
    total_size = len(data)

    if total_size == 0:
        # 빈 파일이면 빈 part000 하나 생성
        part_path = parent / f"{base_name}.part000"
        part_path.write_bytes(b"")
        return [part_path]

    offset = 0
    part_index = 0

    while offset < total_size:
        chunk = data[offset: offset + chunk_bytes]
        part_path = parent / f"{base_name}.part{part_index:03d}"
        part_path.write_bytes(chunk)
        parts.append(part_path)
        offset += chunk_bytes
        part_index += 1

    return parts


def merge_bundles(parts: list[Path | str], output: Path | str) -> Path:
    """분할된 bundle 파일들을 하나로 재조립한다.

    parts 순서대로 이어붙인다.

    Args:
        parts:   분할 파일 경로 목록 (순서 보장).
        output:  재조립된 bundle 파일을 저장할 경로.

    Returns:
        재조립된 bundle 파일 경로.

    Raises:
        FileNotFoundError: parts 중 하나라도 존재하지 않을 때.
    """
    output = Path(output)

    # 모든 파트 존재 여부 선행 검증
    for part in parts:
        part = Path(part)
        if not part.exists():
            raise FileNotFoundError(f"파트 파일을 찾을 수 없습니다: {part}")

    # 순서대로 이어붙이기 (바이너리 모드)
    with output.open('wb') as out_file:
        for part in parts:
            out_file.write(Path(part).read_bytes())

    return output


def verify_bundle(
    bundle_path: Path | str,
    repo_path: Path | str | None = None,
) -> bool:
    """git bundle verify 로 bundle 파일의 무결성을 검증한다.

    Args:
        bundle_path: 검증할 bundle 파일 경로.
        repo_path:   prerequisite 검증 기준이 되는 Git 리포지토리 경로.
                     None 이면 현재 작업 디렉터리 기준.

    Returns:
        True  — bundle이 유효함.
        False — 파일 없음, 손상, git 오류 등 모든 실패 케이스.
    """
    return verify_bundle_detailed(bundle_path, repo_path=repo_path).valid


def verify_bundle_detailed(
    bundle_path: Path | str,
    repo_path: Path | str | None = None,
) -> BundleVerifyResult:
    """git bundle verify 결과와 상세 메시지를 반환한다."""
    bundle_path = Path(bundle_path)

    if not bundle_path.exists():
        return BundleVerifyResult(
            valid=False,
            message=f"bundle 파일을 찾을 수 없습니다: {bundle_path}",
        )

    try:
        result = subprocess.run(
            ["git", "bundle", "verify", str(bundle_path)],
            cwd=repo_path,
            capture_output=True,
            encoding='utf-8',
            env=_git_env(),
        )
        message = "\n".join(
            part.strip()
            for part in (result.stdout, result.stderr)
            if part and part.strip()
        )
        return BundleVerifyResult(
            valid=result.returncode == 0,
            message=message,
        )
    except Exception as exc:
        return BundleVerifyResult(valid=False, message=str(exc))
