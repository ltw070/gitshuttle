"""test_manifest.py — manifest.py 단위 테스트.

TDD: 이 파일은 manifest.py 구현 전에 먼저 작성된다 (RED 상태).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from gitshuttle.git_ops import Commit


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_commits():
    return [
        Commit(
            hash="abc1234def5678901234567890123456789012345",
            short_hash="abc1234",
            date="2026-05-01 10:00:00 +0900",
            author="Alice",
            message="feat: 로그인 구현",
            files_changed=3,
        ),
        Commit(
            hash="bcd2345efg678901234567890123456789012345",
            short_hash="bcd2345",
            date="2026-04-28 09:00:00 +0900",
            author="Bob",
            message="fix: 인코딩 수정",
            files_changed=1,
        ),
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_manifest_creates_file(tmp_path, sample_commits):
    """create_manifest 호출 시 파일이 실제로 생성되어야 한다."""
    from gitshuttle.manifest import create_manifest

    out = tmp_path / "test_manifest.txt"
    result = create_manifest(sample_commits, out)

    assert result == out
    assert out.exists()


def test_create_manifest_contains_hashes(tmp_path, sample_commits):
    """생성된 manifest 파일에 커밋 short_hash 가 포함되어야 한다."""
    from gitshuttle.manifest import create_manifest

    out = tmp_path / "hashes_manifest.txt"
    create_manifest(sample_commits, out)

    content = out.read_text(encoding='utf-8')
    for commit in sample_commits:
        assert commit.short_hash in content


def test_create_manifest_korean_message(tmp_path):
    """한글 커밋 메시지가 UTF-8 로 정상 저장되어야 한다 (BOM 없음)."""
    from gitshuttle.manifest import create_manifest

    commits = [
        Commit(
            hash="aaa1111bbb2222ccc3333ddd4444eee5555fff66",
            short_hash="aaa1111",
            date="2026-05-08 12:00:00 +0900",
            author="홍길동",
            message="feat: 한글 커밋 메시지 테스트",
            files_changed=2,
        ),
    ]
    out = tmp_path / "korean_manifest.txt"
    create_manifest(commits, out)

    # UTF-8 로 읽을 수 있어야 함
    content = out.read_text(encoding='utf-8')
    assert "한글 커밋 메시지 테스트" in content
    assert "홍길동" in content

    # BOM 없음 확인
    raw_bytes = out.read_bytes()
    assert not raw_bytes.startswith(b'\xef\xbb\xbf'), "BOM(utf-8-sig)이 없어야 합니다."


def test_create_manifest_format(tmp_path, sample_commits):
    """manifest 파일에 필수 헤더 섹션이 모두 포함되어야 한다."""
    from gitshuttle.manifest import create_manifest

    out = tmp_path / "format_manifest.txt"
    create_manifest(sample_commits, out, branch="main")

    content = out.read_text(encoding='utf-8')

    assert "GitShuttle Manifest" in content
    assert "브랜치:" in content
    assert "main" in content
    assert "커밋 수:" in content
    # 커밋 수 값 확인
    assert str(len(sample_commits)) in content
    # 생성일시 라인 (YYYY-MM-DD 패턴 포함)
    assert "생성일시:" in content


def test_create_manifest_returns_path(tmp_path, sample_commits):
    """create_manifest 는 생성된 파일의 Path 를 반환해야 한다."""
    from gitshuttle.manifest import create_manifest

    out = tmp_path / "return_check.txt"
    result = create_manifest(sample_commits, out)

    assert isinstance(result, Path)
    assert result == out


def test_create_manifest_each_commit_line(tmp_path, sample_commits):
    """각 커밋 정보(short_hash, author, message)가 파일에 기록되어야 한다."""
    from gitshuttle.manifest import create_manifest

    out = tmp_path / "line_check.txt"
    create_manifest(sample_commits, out)

    content = out.read_text(encoding='utf-8')

    for commit in sample_commits:
        assert commit.short_hash in content
        assert commit.author in content
        assert commit.message in content
