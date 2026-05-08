"""tests/ui/test_csv_ui.py — csv_ui 모듈 테스트."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from gitshuttle.git_ops import Commit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_commits():
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

def test_generate_csv_creates_file(tmp_path):
    """generate_csv 호출 후 파일이 생성되어야 한다."""
    from gitshuttle.ui.csv_ui import generate_csv

    commits = _make_commits()
    out = tmp_path / "commits.csv"
    result = generate_csv(commits, out)

    assert result == out
    assert out.exists()


def test_generate_csv_has_include_column(tmp_path):
    """생성된 CSV에 include 컬럼이 있어야 한다."""
    from gitshuttle.ui.csv_ui import generate_csv

    commits = _make_commits()
    out = tmp_path / "commits.csv"
    generate_csv(commits, out)

    with open(out, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

    assert "include" in fieldnames


def test_generate_csv_utf8_sig_encoding(tmp_path):
    """CSV 파일이 utf-8-sig (BOM) 인코딩으로 저장되어야 한다."""
    from gitshuttle.ui.csv_ui import generate_csv

    commits = _make_commits()
    out = tmp_path / "commits.csv"
    generate_csv(commits, out)

    # BOM(EF BB BF) 첫 3바이트로 확인
    raw = out.read_bytes()
    assert raw[:3] == b"\xef\xbb\xbf", "utf-8-sig BOM이 없음"


def test_parse_csv_returns_selected(tmp_path):
    """include=Y 인 커밋만 반환해야 한다."""
    from gitshuttle.ui.csv_ui import generate_csv, parse_csv

    commits = _make_commits()
    out = tmp_path / "commits.csv"
    generate_csv(commits, out)

    # include 컬럼: 첫 번째는 Y, 두 번째는 N 으로 수정
    rows = []
    with open(out, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    rows[0]["include"] = "Y"
    rows[1]["include"] = "N"

    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    selected = parse_csv(out, commits)
    assert len(selected) == 1
    assert selected[0].short_hash == "abc1234"


def test_parse_csv_excludes_n(tmp_path):
    """include=N 인 커밋은 결과에 포함되지 않아야 한다."""
    from gitshuttle.ui.csv_ui import generate_csv, parse_csv

    commits = _make_commits()
    out = tmp_path / "commits.csv"
    generate_csv(commits, out)

    rows = []
    with open(out, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    for row in rows:
        row["include"] = "N"

    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    selected = parse_csv(out, commits)
    assert selected == []


def test_parse_csv_case_insensitive(tmp_path):
    """include 컬럼 값은 대소문자 무관하게 파싱되어야 한다 (y, Y 모두 포함)."""
    from gitshuttle.ui.csv_ui import generate_csv, parse_csv

    commits = _make_commits()
    out = tmp_path / "commits.csv"
    generate_csv(commits, out)

    rows = []
    with open(out, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    rows[0]["include"] = "y"
    rows[1]["include"] = "Y"

    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    selected = parse_csv(out, commits)
    assert len(selected) == 2


def test_parse_csv_korean(tmp_path):
    """한글 커밋 메시지가 포함된 CSV를 정상 파싱해야 한다."""
    from gitshuttle.ui.csv_ui import generate_csv, parse_csv

    commits = [
        Commit(
            hash="aaa0000000000000000000000000000000000000",
            short_hash="aaa0000",
            date="2026-05-01 10:00:00 +0900",
            author="김철수",
            message="feat: 한글 기능 추가",
            files_changed=2,
        ),
    ]
    out = tmp_path / "korean.csv"
    generate_csv(commits, out)

    rows = []
    with open(out, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    rows[0]["include"] = "Y"

    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    selected = parse_csv(out, commits)
    assert len(selected) == 1
    assert selected[0].author == "김철수"
    assert "한글" in selected[0].message
