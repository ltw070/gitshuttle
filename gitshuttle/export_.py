"""export_.py — export 오케스트레이션.

run_export: 선택된 커밋들로 bundle + sha256 + manifest 3개 파일을 생성한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .git_ops import Commit
from .bundle import create_bundle
from .checksum import generate as generate_checksum
from .manifest import create_manifest


@dataclass
class ExportResult:
    """export 결과물 3개 파일 경로."""
    bundle: Path
    sha256: Path
    manifest: Path


def run_export(
    repo_path: Path | str,
    commits: list[Commit],
    output_dir: Path | str,
    branch: str = "unknown",
    filename: str | None = None,
    bundle_scope: str = "range",
    base_refs: list[str] | None = None,
) -> ExportResult:
    """선택된 커밋으로 bundle + sha256 + manifest 를 생성한다.

    Args:
        repo_path:   소스 git 리포지토리 경로.
        commits:     export 할 Commit 목록 (비어 있으면 ValueError).
        output_dir:  출력 디렉터리 (없으면 자동 생성).
        branch:      브랜치 이름 (manifest 헤더에 기록).
        filename:    패키지 파일명 (확장자 제외). 미지정 시 shuttle_YYMMDD.
        bundle_scope: bundle 범위 방식 ("range", "full").
        base_refs: base..branch delta export 기준점. 지정하면 self-contained
                   bundle에 기준점 metadata ref를 함께 기록한다.

    Returns:
        ExportResult (bundle, sha256, manifest 경로 포함).

    Raises:
        ValueError: commits 가 비어있을 때.
    """
    if not commits:
        raise ValueError("commits 목록이 비어있습니다. 최소 1개의 커밋이 필요합니다.")

    repo_path = Path(repo_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 파일명 기반 계산
    if filename is None:
        date_str = datetime.now().strftime("%y%m%d")
        base_name = f"shuttle_{date_str}"
    else:
        base_name = filename

    package_filename = f"{base_name}.bundle"
    manifest_filename = f"{base_name}_manifest.txt"

    # 1. bundle 생성
    package_path = create_bundle(
        repo_path=repo_path,
        commits=commits,
        output_dir=output_dir,
        filename=package_filename,
        scope=bundle_scope,
        base_refs=base_refs,
    )

    # 2. SHA-256 체크섬 생성
    sha256_path = generate_checksum(package_path)

    # 3. manifest 생성
    manifest_path = create_manifest(
        commits=commits,
        output_path=output_dir / manifest_filename,
        branch=branch,
    )

    return ExportResult(
        bundle=package_path,
        sha256=sha256_path,
        manifest=manifest_path,
    )
