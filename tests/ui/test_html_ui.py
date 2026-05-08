"""tests/ui/test_html_ui.py — html_ui 모듈 테스트."""
from __future__ import annotations

import json
import re
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

def test_generate_html_creates_file(tmp_path):
    """generate_html 호출 후 파일이 생성되어야 한다."""
    from gitshuttle.ui.html_ui import generate_html

    commits = _make_commits()
    out = tmp_path / "commits.html"
    result = generate_html(commits, out)

    assert result == out
    assert out.exists()


def test_html_is_self_contained(tmp_path):
    """생성된 HTML에 외부 URL(http://, https://, cdn)이 없어야 한다."""
    from gitshuttle.ui.html_ui import generate_html

    commits = _make_commits()
    out = tmp_path / "commits.html"
    generate_html(commits, out)

    content = out.read_text(encoding="utf-8")

    # src= 또는 href= 속성에 외부 URL이 있는지 검사
    external_patterns = [
        r'src=["\']https?://',
        r'href=["\']https?://',
        r'cdn\.',
    ]
    for pattern in external_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        assert not matches, f"외부 URL 발견: {pattern} → {matches}"


def test_html_contains_commits(tmp_path):
    """생성된 HTML에 커밋 해시와 메시지가 포함되어야 한다."""
    from gitshuttle.ui.html_ui import generate_html

    commits = _make_commits()
    out = tmp_path / "commits.html"
    generate_html(commits, out)

    content = out.read_text(encoding="utf-8")

    for commit in commits:
        assert commit.short_hash in content, f"short_hash {commit.short_hash} 없음"


def test_html_encoding_utf8_no_bom(tmp_path):
    """HTML 파일은 UTF-8 (BOM 없음) 으로 저장되어야 한다."""
    from gitshuttle.ui.html_ui import generate_html

    commits = _make_commits()
    out = tmp_path / "commits.html"
    generate_html(commits, out)

    raw = out.read_bytes()
    # BOM(EF BB BF)이 없어야 함
    assert not raw.startswith(b"\xef\xbb\xbf"), "HTML에 BOM이 있음 — utf-8-sig 사용 금지"


def test_parse_selection_json(tmp_path):
    """parse_selection_json 은 선택된 해시에 해당하는 커밋만 반환해야 한다."""
    from gitshuttle.ui.html_ui import parse_selection_json

    commits = _make_commits()
    json_path = tmp_path / "selection.json"
    json_path.write_text(
        json.dumps({"selected": ["abc1234"]}),
        encoding="utf-8",
    )

    selected = parse_selection_json(json_path, commits)
    assert len(selected) == 1
    assert selected[0].short_hash == "abc1234"


def test_parse_selection_json_multiple(tmp_path):
    """여러 해시가 선택된 경우 모두 반환해야 한다."""
    from gitshuttle.ui.html_ui import parse_selection_json

    commits = _make_commits()
    json_path = tmp_path / "selection.json"
    json_path.write_text(
        json.dumps({"selected": ["abc1234", "bcd2345"]}),
        encoding="utf-8",
    )

    selected = parse_selection_json(json_path, commits)
    assert len(selected) == 2


def test_parse_selection_json_empty(tmp_path):
    """선택이 없는 경우 빈 리스트를 반환해야 한다."""
    from gitshuttle.ui.html_ui import parse_selection_json

    commits = _make_commits()
    json_path = tmp_path / "selection.json"
    json_path.write_text(json.dumps({"selected": []}), encoding="utf-8")

    selected = parse_selection_json(json_path, commits)
    assert selected == []


def test_parse_selection_json_unknown_hash(tmp_path):
    """존재하지 않는 해시는 무시되어야 한다."""
    from gitshuttle.ui.html_ui import parse_selection_json

    commits = _make_commits()
    json_path = tmp_path / "selection.json"
    json_path.write_text(
        json.dumps({"selected": ["xxxxxxx"]}),
        encoding="utf-8",
    )

    selected = parse_selection_json(json_path, commits)
    assert selected == []
