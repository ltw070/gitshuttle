"""checksum.py — SHA-256 생성/검증.

파일 읽기는 'rb' 모드로 수행 (바이너리 SHA-256 계산).
체크섬 파일은 encoding='utf-8' 로 저장.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


def generate(file_path: Path | str) -> Path:
    """대상 파일의 SHA-256 체크섬 파일을 생성한다.

    출력 파일명: <file_path>.sha256
    내용 형식:  "<hex>  <filename>"  (두 공백 구분자 — sha256sum 표준)

    Returns:
        생성된 .sha256 파일의 Path.
    """
    file_path = Path(file_path)
    sha256_path = file_path.with_suffix(file_path.suffix + ".sha256")

    hex_digest = _compute_sha256(file_path)

    content = f"{hex_digest}  {file_path.name}"
    sha256_path.write_text(content, encoding='utf-8')

    return sha256_path


def verify(
    file_path: Path | str,
    sha256_path: Path | str | None = None,
) -> bool:
    """체크섬을 검증한다.

    sha256_path 미지정 시 <file_path>.sha256 을 자동 탐색.

    Returns:
        True  — 파일과 체크섬이 일치.
        False — 불일치, 파일 없음, 체크섬 파일 없음 등 모든 오류 케이스.
    """
    file_path = Path(file_path)

    if sha256_path is None:
        sha256_path = file_path.with_suffix(file_path.suffix + ".sha256")
    else:
        sha256_path = Path(sha256_path)

    # 대상 파일 존재 확인
    if not file_path.exists():
        return False

    # 체크섬 파일 존재 확인
    if not sha256_path.exists():
        return False

    try:
        content = sha256_path.read_text(encoding='utf-8').strip()
        # 형식: "<hex>  <filename>"
        parts = content.split("  ", 1)
        if len(parts) != 2:
            return False
        expected_hex = parts[0].strip()

        actual_hex = _compute_sha256(file_path)
        return actual_hex == expected_hex

    except Exception:
        return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_sha256(file_path: Path) -> str:
    """파일의 SHA-256 hex digest 를 반환한다. 'rb' 모드 사용."""
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
