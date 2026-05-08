"""Tests for gitshuttle.checksum — Sprint 1.

RED phase: these tests will fail until implementation is in place.
"""
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_generate_creates_sha256_file(tmp_path):
    """generate(file_path) → .sha256 파일 생성.

    내용 형식: "<hex>  <filename>" (두 공백 구분자, sha256sum 표준).
    """
    from gitshuttle.checksum import generate

    target = tmp_path / "data.bin"
    target.write_bytes(b"hello gitshuttle")

    sha256_path = generate(target)

    assert isinstance(sha256_path, Path)
    assert sha256_path.exists()
    assert sha256_path.suffix == ".sha256"
    assert sha256_path.name == "data.bin.sha256"

    content = sha256_path.read_text(encoding='utf-8')
    parts = content.strip().split("  ")
    assert len(parts) == 2, f"형식 불일치: {content!r}"

    hex_part, filename_part = parts
    assert len(hex_part) == 64, "SHA-256 hex는 64자여야 한다"
    assert all(c in "0123456789abcdef" for c in hex_part), "hex 문자만 포함해야 한다"
    assert filename_part == "data.bin"


def test_generate_returns_sha256_path(tmp_path):
    """generate() 반환값이 생성된 .sha256 파일 Path여야 한다."""
    from gitshuttle.checksum import generate

    target = tmp_path / "sample.bundle"
    target.write_bytes(b"\x00\x01\x02\x03" * 1000)

    sha256_path = generate(target)

    assert sha256_path == target.with_suffix(target.suffix + ".sha256")


def test_verify_checksum_valid(tmp_path):
    """올바른 파일 → verify(file_path, sha256_path) → True."""
    from gitshuttle.checksum import generate, verify

    target = tmp_path / "shuttle.bundle"
    target.write_bytes(b"real bundle content here")

    sha256_path = generate(target)

    assert verify(target, sha256_path) is True


def test_verify_checksum_auto_discover(tmp_path):
    """sha256_path 미지정 시 <file>.sha256 자동 탐색 → True."""
    from gitshuttle.checksum import generate, verify

    target = tmp_path / "shuttle.bundle"
    target.write_bytes(b"auto discover test")

    generate(target)  # <file>.sha256 생성

    # sha256_path 인자 없이 호출
    assert verify(target) is True


def test_verify_checksum_invalid(tmp_path):
    """내용 변조 후 verify → False."""
    from gitshuttle.checksum import generate, verify

    target = tmp_path / "tampered.bundle"
    target.write_bytes(b"original content")

    sha256_path = generate(target)

    # 파일 내용 변조
    target.write_bytes(b"tampered content!!")

    assert verify(target, sha256_path) is False


def test_verify_missing_sha256_file(tmp_path):
    """sha256 파일이 없을 때 verify → False."""
    from gitshuttle.checksum import verify

    target = tmp_path / "nocheck.bundle"
    target.write_bytes(b"some content")
    # .sha256 파일 생성 안 함

    assert verify(target) is False


def test_verify_missing_target_file(tmp_path):
    """대상 파일이 없을 때 verify → False."""
    from gitshuttle.checksum import verify

    target = tmp_path / "missing.bundle"
    sha256_path = tmp_path / "missing.bundle.sha256"
    sha256_path.write_text("a" * 64 + "  missing.bundle", encoding='utf-8')

    assert verify(target, sha256_path) is False


def test_generate_sha256_correct_value(tmp_path):
    """generate()가 계산한 SHA-256이 hashlib 직접 계산값과 일치해야 한다."""
    import hashlib
    from gitshuttle.checksum import generate

    data = b"deterministic content for sha256 check"
    target = tmp_path / "check.bin"
    target.write_bytes(data)

    sha256_path = generate(target)
    content = sha256_path.read_text(encoding='utf-8').strip()
    hex_in_file = content.split("  ")[0]

    expected_hex = hashlib.sha256(data).hexdigest()
    assert hex_in_file == expected_hex, (
        f"SHA-256 불일치. 파일: {hex_in_file}, 기대: {expected_hex}"
    )
