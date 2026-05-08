"""test_e2e.py — E2E 통합 테스트 + split/merge bundle 테스트.

Sprint 5: 분할 압축 + E2E 통합 테스트 (TDD RED phase)

테스트 목록:
  1. test_e2e_export_import_flow       — source export → target import → 커밋 수 증가
  2. test_e2e_korean_message_preserved — 한글 커밋 메시지가 import 후 보존됨
  3. test_split_bundle_creates_parts   — split 후 파트 파일들이 생성됨
  4. test_split_bundle_chunk_count     — 파일 크기/청크 크기로 파트 수 계산 확인
  5. test_merge_bundles_restores_original — split → merge 후 원본과 바이트 동일
  6. test_merged_bundle_is_valid       — merge 결과물을 verify_bundle이 True 반환

제약:
  - 실제 100MB+ 파일 생성 금지. 소형 더미 데이터(수 KB)만 사용.
  - 외부 네트워크 호출 없음.
  - two_git_repos, tmp_git_repo 픽스처 사용.
"""
from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _git_env() -> dict:
    return {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'GIT_TERMINAL_PROMPT': '0'}


def _add_commit(repo_path: Path, filename: str, content: str, message: str) -> None:
    """repo에 파일 추가 후 커밋."""
    env = _git_env()
    (repo_path / filename).write_text(content, encoding='utf-8')
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, encoding='utf-8', env=env)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_path, check=True, encoding='utf-8', env=env,
    )


def _do_export(source: Path, output_dir: Path, filename: str = "test_shuttle") -> Path:
    """source repo를 bundle로 export하고 bundle 경로를 반환한다."""
    from gitshuttle.git_ops import get_commits
    from gitshuttle.export_ import run_export

    commits = get_commits(source)
    result = run_export(
        repo_path=source,
        commits=commits,
        output_dir=output_dir,
        branch="HEAD",
        filename=filename,
    )
    return result.bundle


# ---------------------------------------------------------------------------
# E2E Tests
# ---------------------------------------------------------------------------

def test_e2e_export_import_flow(two_git_repos, tmp_path):
    """source export → target import → target의 커밋 수가 증가해야 한다.

    two_git_repos: (source, target) 두 독립 임시 repo.
    source에 커밋을 추가한 뒤 export → import하면
    target의 커밋 수가 import 전보다 많아야 한다.
    """
    from gitshuttle.import_ import run_import, ImportResult
    from gitshuttle.git_ops import get_commits

    source, target = two_git_repos

    # source에 추가 커밋 생성
    _add_commit(source, "feature.txt", "new feature content", "feat: add feature")
    _add_commit(source, "bugfix.txt", "bugfix content", "fix: critical bug")

    # export
    bundle_path = _do_export(source, tmp_path)
    assert bundle_path.exists(), "bundle 파일이 생성되어야 한다"

    # import 전 target 커밋 수
    before_count = len(get_commits(target))

    # import 실행
    result = run_import(bundle_path, target)

    assert isinstance(result, ImportResult)
    assert result.total >= 1, "bundle 내 커밋이 1개 이상이어야 한다"
    assert result.imported >= 1, "최소 1개 이상 import되어야 한다"

    # import 후 target 커밋 수 — 반드시 증가해야 한다
    after_count = len(get_commits(target))
    assert after_count > before_count, (
        f"import 후 커밋 수가 증가해야 한다. before={before_count}, after={after_count}"
    )


def test_e2e_korean_message_preserved(two_git_repos, tmp_path):
    """한글 커밋 메시지가 export → import 후에도 그대로 보존되어야 한다.

    인코딩 규칙 준수: subprocess encoding='utf-8', git 환경변수 포함.
    """
    from gitshuttle.import_ import run_import
    from gitshuttle.git_ops import get_commits

    source, target = two_git_repos

    # 한글 커밋 메시지 추가
    korean_message = "feat: 한글 커밋 메시지 보존 테스트"
    _add_commit(source, "korean.txt", "한글 내용입니다", korean_message)

    # export
    bundle_path = _do_export(source, tmp_path)

    # import
    run_import(bundle_path, target)

    # target repo에서 커밋 메시지 확인
    target_commits = get_commits(target)
    messages = [c.message for c in target_commits]

    assert korean_message in messages, (
        f"한글 커밋 메시지 '{korean_message}'가 target에 보존되어야 한다.\n"
        f"실제 messages: {messages}"
    )


# ---------------------------------------------------------------------------
# Split / Merge Tests
# ---------------------------------------------------------------------------

def test_split_bundle_creates_parts(tmp_git_repo, tmp_path):
    """split_bundle 실행 후 파트 파일들이 생성되어야 한다.

    소형 bundle을 작은 chunk_bytes로 분할하면 여러 .partNNN 파일이 생겨야 한다.
    """
    from gitshuttle.git_ops import get_commits
    from gitshuttle.bundle import create_bundle, split_bundle

    commits = get_commits(tmp_git_repo)
    bundle_path = create_bundle(tmp_git_repo, commits, tmp_path, filename="split_test.bundle")

    # bundle 크기 확인 (수 KB 범위 예상)
    bundle_size = bundle_path.stat().st_size
    assert bundle_size > 0, "bundle 파일 크기가 0이면 안 된다"

    # 1 바이트 단위로 분할 — 많은 파트 생성 (단, 극단적 수는 피해야 함)
    # 실용적으로 bundle 크기를 3으로 나눠 3개 이상 파트 생성
    chunk_size = max(1, bundle_size // 3)
    parts = split_bundle(bundle_path, chunk_bytes=chunk_size)

    assert isinstance(parts, list), "split_bundle은 list를 반환해야 한다"
    assert len(parts) >= 2, f"2개 이상 파트가 생성되어야 한다. 실제: {len(parts)}"

    for part in parts:
        assert part.exists(), f"파트 파일이 존재해야 한다: {part}"
        assert part.stat().st_size > 0, f"파트 파일 크기가 0이면 안 된다: {part}"


def test_split_bundle_chunk_count(tmp_path):
    """파일 크기 / chunk_bytes 로 파트 수를 정확히 계산해야 한다.

    더미 바이너리 데이터로 검증. 실제 git bundle 필요 없음.
    """
    from gitshuttle.bundle import split_bundle

    # 100 바이트 더미 파일 생성
    dummy_path = tmp_path / "dummy.bundle"
    dummy_data = bytes(range(256)) * 10  # 2560 바이트 (0x00~0xFF 반복)
    dummy_path.write_bytes(dummy_data)

    chunk_size = 256
    expected_parts = math.ceil(len(dummy_data) / chunk_size)  # = 10

    parts = split_bundle(dummy_path, chunk_bytes=chunk_size)

    assert len(parts) == expected_parts, (
        f"파트 수가 {expected_parts}여야 한다. 실제: {len(parts)}"
    )

    # 파트 파일명 형식 확인: <basename>.part000, .part001, ...
    for i, part in enumerate(parts):
        expected_suffix = f".part{i:03d}"
        assert part.suffix == expected_suffix or part.name.endswith(expected_suffix), (
            f"파트 {i}의 파일명 형식이 잘못되었다: {part.name}"
        )


def test_split_bundle_invalid_chunk_size_raises(tmp_path):
    """chunk_bytes <= 0 이면 ValueError를 발생시켜야 한다."""
    from gitshuttle.bundle import split_bundle

    dummy_path = tmp_path / "dummy.bundle"
    dummy_path.write_bytes(b"some content")

    with pytest.raises(ValueError):
        split_bundle(dummy_path, chunk_bytes=0)

    with pytest.raises(ValueError):
        split_bundle(dummy_path, chunk_bytes=-1)


def test_merge_bundles_restores_original(tmp_path):
    """split → merge 후 원본 데이터와 바이트 단위로 동일해야 한다.

    바이너리 데이터 무결성 검증. 실제 git bundle 불필요.
    """
    from gitshuttle.bundle import split_bundle, merge_bundles

    # 더미 데이터 생성 (수 KB 범위)
    original_data = bytes(range(256)) * 20  # 5120 바이트
    dummy_path = tmp_path / "original.bundle"
    dummy_path.write_bytes(original_data)

    # 분할 (7개 파트 예상: ceil(5120/800) = 7)
    chunk_size = 800
    parts = split_bundle(dummy_path, chunk_bytes=chunk_size)
    assert len(parts) >= 2

    # 재조립
    merged_path = tmp_path / "merged.bundle"
    result_path = merge_bundles(parts, merged_path)

    assert result_path.exists(), "merge 결과 파일이 존재해야 한다"
    assert result_path == merged_path

    # 바이트 단위 동일성 검증
    merged_data = merged_path.read_bytes()
    assert merged_data == original_data, (
        f"merge 후 데이터가 원본과 달라야 한다. "
        f"original_size={len(original_data)}, merged_size={len(merged_data)}"
    )


def test_merge_bundles_missing_part_raises(tmp_path):
    """존재하지 않는 파트 파일이 있으면 FileNotFoundError를 발생시켜야 한다."""
    from gitshuttle.bundle import merge_bundles

    nonexistent_part = tmp_path / "nonexistent.part000"
    output_path = tmp_path / "merged.bundle"

    with pytest.raises(FileNotFoundError):
        merge_bundles([nonexistent_part], output_path)


def test_merged_bundle_is_valid(tmp_git_repo, tmp_path):
    """split → merge 후 재조립된 bundle을 verify_bundle이 True 반환해야 한다.

    실제 git bundle로 round-trip 무결성 검증.
    """
    from gitshuttle.git_ops import get_commits
    from gitshuttle.bundle import create_bundle, split_bundle, merge_bundles, verify_bundle

    commits = get_commits(tmp_git_repo)
    bundle_path = create_bundle(tmp_git_repo, commits, tmp_path, filename="roundtrip.bundle")

    bundle_size = bundle_path.stat().st_size
    assert bundle_size > 0

    # 2~3개 파트로 분할
    chunk_size = max(1, bundle_size // 2)
    parts = split_bundle(bundle_path, chunk_bytes=chunk_size)
    assert len(parts) >= 2

    # 재조립
    merged_path = tmp_path / "roundtrip_merged.bundle"
    merge_bundles(parts, merged_path)

    # git bundle verify 통과 여부
    assert verify_bundle(merged_path), (
        "split → merge 후 재조립된 bundle이 git bundle verify를 통과해야 한다"
    )
