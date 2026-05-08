"""csv_ui.py — commits.csv 생성 및 파싱.

인코딩:
  - 생성: utf-8-sig (Excel BOM 호환)
  - 파싱: utf-8-sig
"""
from __future__ import annotations

import csv
from pathlib import Path

from gitshuttle.git_ops import Commit


# CSV 컬럼 순서
_FIELDNAMES = ["include", "hash", "short_hash", "date", "author", "message", "files_changed"]


def generate_csv(
    commits: list[Commit],
    output_path: Path | str,
    already_imported: set[str] | None = None,
) -> Path:
    """commits.csv 를 생성한다.

    Args:
        commits:          커밋 목록 (최신순).
        output_path:      출력 파일 경로.
        already_imported: 이미 import 된 커밋 short_hash set.
                          해당 커밋의 include 기본값은 'N'.

    Returns:
        생성된 파일 경로.

    인코딩: utf-8-sig (BOM 포함, Excel 호환).
    """
    if already_imported is None:
        already_imported = set()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        writer.writeheader()
        for commit in commits:
            include = "N" if commit.short_hash in already_imported else "Y"
            writer.writerow(
                {
                    "include": include,
                    "hash": commit.hash,
                    "short_hash": commit.short_hash,
                    "date": commit.date,
                    "author": commit.author,
                    "message": commit.message,
                    "files_changed": commit.files_changed,
                }
            )

    return output_path


def parse_csv(
    csv_path: Path | str,
    original_commits: list[Commit],
) -> list[Commit]:
    """include=Y (대소문자 무관) 인 커밋만 반환한다.

    Args:
        csv_path:         편집된 CSV 파일 경로.
        original_commits: 원본 커밋 목록 (short_hash 기준으로 매칭).

    Returns:
        include=Y 인 Commit 목록 (원본 순서 유지).
    """
    csv_path = Path(csv_path)

    # short_hash → Commit 매핑
    commit_map: dict[str, Commit] = {c.short_hash: c for c in original_commits}

    selected: list[Commit] = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            include_val = row.get("include", "").strip().upper()
            if include_val == "Y":
                short_hash = row.get("short_hash", "").strip()
                if short_hash in commit_map:
                    selected.append(commit_map[short_hash])

    return selected
