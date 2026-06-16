"""test_rewrite.py — rewrite.py TDD 테스트.

TDD RED phase: rewrite.py 구현 전에 작성.
테스트 대상:
  - load_author_map: JSON 파일 로드, 파일 없으면 빈 dict 반환
  - rewrite_authors: 작성자 치환, 미매핑 원본 유지
  - rewrite_branch_ref: refs/heads/<old> → refs/heads/<new> 치환
  - rewrite_timestamps: mode="now", "original", "from"
  - apply_rewrites: 전체 파이프라인 편의 함수
  - import_.py: --author-map, --target-branch, --timestamp CLI 옵션 존재 확인
"""
from __future__ import annotations

import json
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# 테스트용 fast-export 스트림 샘플
# ---------------------------------------------------------------------------

# 타임스탬프: 2024-05-02 09:00:00 +0900 = 1714611600 Unix
SAMPLE_TS_1 = 1714611600
# 타임스탬프: 2024-05-03 09:00:00 +0900 = 1714698000 Unix (하루 뒤)
SAMPLE_TS_2 = 1714698000

SAMPLE_STREAM = textwrap.dedent(f"""\
blob
mark :1
data 13
Hello, World!

reset refs/heads/main
commit refs/heads/main
mark :2
author Alice <alice@example.com> {SAMPLE_TS_1} +0900
committer Alice <alice@example.com> {SAMPLE_TS_1} +0900
data 14
Initial commit

M 100644 :1 README.md

commit refs/heads/main
mark :3
author Bob <bob@example.com> {SAMPLE_TS_2} +0900
committer Bob <bob@example.com> {SAMPLE_TS_2} +0900
data 12
Second commit
from :2

M 100644 :1 hello.txt

""")


# ---------------------------------------------------------------------------
# load_author_map 테스트
# ---------------------------------------------------------------------------

class TestLoadAuthorMap:
    def test_load_existing_json(self, tmp_path):
        """JSON 파일이 있으면 dict를 반환한다."""
        from gitshuttle.rewrite import load_author_map

        mapping = {
            "alice@example.com": {"name": "Alice Internal", "email": "alice@corp.com"},
            "bob@example.com": {"name": "Bob Internal", "email": "bob@corp.com"},
        }
        map_file = tmp_path / "author_map.json"
        map_file.write_text(json.dumps(mapping), encoding='utf-8')

        result = load_author_map(str(map_file))
        assert result == mapping

    def test_load_nonexistent_file_returns_empty(self, tmp_path):
        """파일이 없으면 빈 dict를 반환한다."""
        from gitshuttle.rewrite import load_author_map

        result = load_author_map(str(tmp_path / "nonexistent.json"))
        assert result == {}

    def test_load_with_path_object(self, tmp_path):
        """Path 객체도 허용한다."""
        from gitshuttle.rewrite import load_author_map

        mapping = {"x@a.com": {"name": "X", "email": "x@b.com"}}
        map_file = tmp_path / "map.json"
        map_file.write_text(json.dumps(mapping), encoding='utf-8')

        result = load_author_map(map_file)
        assert result["x@a.com"]["name"] == "X"

    def test_invalid_json_has_file_and_line_hint(self, tmp_path):
        """JSON 문법 오류는 파일/라인/검증 명령을 포함해 안내한다."""
        import pytest
        from gitshuttle.rewrite import load_author_map

        map_file = tmp_path / "author_map.json"
        map_file.write_text(
            '{\n'
            '  "old@example.com": {"name": "New", "email": "new@example.com"}\n'
            '  "other@example.com": {"name": "New", "email": "new@example.com"}\n'
            '}\n',
            encoding="utf-8",
        )

        with pytest.raises(ValueError) as exc_info:
            load_author_map(map_file)

        message = str(exc_info.value)
        assert "author-map JSON 문법 오류" in message
        assert str(map_file) in message
        assert "line 3" in message
        assert "python -m json.tool" in message


# ---------------------------------------------------------------------------
# rewrite_authors 테스트
# ---------------------------------------------------------------------------

class TestRewriteAuthors:
    def test_mapped_author_replaced(self):
        """매핑된 작성자는 이름과 이메일이 모두 치환된다."""
        from gitshuttle.rewrite import rewrite_authors

        author_map = {
            "alice@example.com": {"name": "Alice Corp", "email": "alice@corp.com"},
        }
        stream, warnings = rewrite_authors(SAMPLE_STREAM, author_map)

        assert "Alice Corp <alice@corp.com>" in stream
        # 원본 이메일은 더 이상 존재하지 않아야 함
        assert "alice@example.com" not in stream

    def test_unmapped_author_preserved(self):
        """미매핑 작성자는 원본 그대로 유지된다."""
        from gitshuttle.rewrite import rewrite_authors

        author_map = {
            "alice@example.com": {"name": "Alice Corp", "email": "alice@corp.com"},
        }
        stream, warnings = rewrite_authors(SAMPLE_STREAM, author_map)

        # Bob은 매핑 없음 → 원본 유지
        assert "Bob <bob@example.com>" in stream

    def test_unmapped_author_in_warnings(self):
        """미매핑 작성자는 warnings 리스트에 포함된다."""
        from gitshuttle.rewrite import rewrite_authors

        author_map = {
            "alice@example.com": {"name": "Alice Corp", "email": "alice@corp.com"},
        }
        stream, warnings = rewrite_authors(SAMPLE_STREAM, author_map)

        # Bob은 매핑 없음 → warnings에 포함
        assert any("bob@example.com" in w or "Bob" in w for w in warnings)

    def test_empty_map_preserves_all_authors(self):
        """빈 매핑이면 모든 작성자가 원본 그대로 유지된다."""
        from gitshuttle.rewrite import rewrite_authors

        stream, warnings = rewrite_authors(SAMPLE_STREAM, {})
        assert "Alice <alice@example.com>" in stream
        assert "Bob <bob@example.com>" in stream

    def test_both_author_and_committer_replaced(self):
        """author 라인과 committer 라인 모두 치환된다."""
        from gitshuttle.rewrite import rewrite_authors

        author_map = {
            "alice@example.com": {"name": "Alice Corp", "email": "alice@corp.com"},
        }
        stream, warnings = rewrite_authors(SAMPLE_STREAM, author_map)

        # author와 committer 라인 수 확인 (각각 Alice에 대해 1개씩)
        author_corp_count = stream.count("Alice Corp <alice@corp.com>")
        assert author_corp_count >= 2  # author 1 + committer 1

    def test_returns_tuple_stream_and_warnings(self):
        """반환값은 (str, list) 형태여야 한다."""
        from gitshuttle.rewrite import rewrite_authors

        result = rewrite_authors(SAMPLE_STREAM, {})
        assert isinstance(result, tuple)
        assert len(result) == 2
        stream, warnings = result
        assert isinstance(stream, str)
        assert isinstance(warnings, list)


# ---------------------------------------------------------------------------
# rewrite_branch_ref 테스트
# ---------------------------------------------------------------------------

class TestRewriteBranchRef:
    def test_commit_line_ref_replaced(self):
        """'commit refs/heads/main' 라인이 타겟 브랜치로 치환된다."""
        from gitshuttle.rewrite import rewrite_branch_ref

        stream = rewrite_branch_ref(SAMPLE_STREAM, "imported/main")

        assert "commit refs/heads/imported/main" in stream
        # 원본 브랜치 이름이 commit 라인에 없어야 함
        assert "commit refs/heads/main" not in stream

    def test_reset_line_ref_replaced(self):
        """'reset refs/heads/main' 라인도 치환된다."""
        from gitshuttle.rewrite import rewrite_branch_ref

        stream = rewrite_branch_ref(SAMPLE_STREAM, "ext-main")

        assert "reset refs/heads/ext-main" in stream

    def test_non_ref_lines_unchanged(self):
        """ref 라인이 아닌 다른 라인은 변경되지 않는다."""
        from gitshuttle.rewrite import rewrite_branch_ref

        stream = rewrite_branch_ref(SAMPLE_STREAM, "new-branch")

        # blob, mark, author, committer 라인은 그대로
        assert "blob" in stream
        assert f"author Alice <alice@example.com> {SAMPLE_TS_1} +0900" in stream

    def test_different_source_branch(self):
        """다른 브랜치 이름(feature/foo)도 정상 치환된다."""
        from gitshuttle.rewrite import rewrite_branch_ref

        stream = "commit refs/heads/feature/foo\nblob\n"
        result = rewrite_branch_ref(stream, "imported/feature")

        assert "commit refs/heads/imported/feature" in result
        assert "commit refs/heads/feature/foo" not in result

    def test_gitshuttle_tmp_ref_replaced(self):
        """GitShuttle bundle의 refs/gitshuttle/tmp_* ref도 타겟 브랜치로 치환된다."""
        from gitshuttle.rewrite import rewrite_branch_ref

        stream = (
            "reset refs/gitshuttle/tmp_abc1234\n"
            "commit refs/gitshuttle/tmp_abc1234\n"
            "mark :1\n"
        )
        result = rewrite_branch_ref(stream, "migration/gitshuttle-20260610")

        assert "reset refs/heads/migration/gitshuttle-20260610" in result
        assert "commit refs/heads/migration/gitshuttle-20260610" in result
        assert "refs/gitshuttle/tmp_abc1234" not in result


# ---------------------------------------------------------------------------
# rewrite_timestamps 테스트
# ---------------------------------------------------------------------------

class TestRewriteTimestamps:
    def test_mode_now_all_timestamps_same(self):
        """mode='now': 모든 author/committer 타임스탬프가 동일한 값으로 변경된다."""
        from gitshuttle.rewrite import rewrite_timestamps

        before = int(time.time())
        stream = rewrite_timestamps(SAMPLE_STREAM, mode="now")
        after = int(time.time()) + 1  # 1초 여유

        # 타임스탬프 라인 추출
        ts_values = _extract_timestamps(stream)

        assert len(ts_values) >= 2
        # 모두 같은 값이어야 함
        assert len(set(ts_values)) == 1
        # now 시각 범위 내여야 함
        ts = int(list(set(ts_values))[0])
        assert before <= ts <= after

    def test_mode_original_timestamps_unchanged(self):
        """mode='original': 원본 타임스탬프가 그대로 유지된다."""
        from gitshuttle.rewrite import rewrite_timestamps

        stream = rewrite_timestamps(SAMPLE_STREAM, mode="original")
        ts_values = _extract_timestamps(stream)

        ts_ints = [int(v) for v in ts_values]
        assert SAMPLE_TS_1 in ts_ints
        assert SAMPLE_TS_2 in ts_ints

    def test_mode_from_first_commit_matches_from_dt(self):
        """mode='from': 가장 오래된 커밋이 from_dt와 일치한다."""
        from gitshuttle.rewrite import rewrite_timestamps

        from_dt = datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        stream = rewrite_timestamps(SAMPLE_STREAM, mode="from", from_dt=from_dt)

        ts_values = sorted([int(v) for v in _extract_timestamps(stream)])
        # 가장 작은 타임스탬프 = from_dt
        from_ts = int(from_dt.timestamp())
        assert ts_values[0] == from_ts

    def test_mode_from_relative_interval_preserved(self):
        """mode='from': 커밋 간 상대 간격이 원본과 동일하게 유지된다."""
        from gitshuttle.rewrite import rewrite_timestamps

        original_interval = SAMPLE_TS_2 - SAMPLE_TS_1  # 86400초 (1일)

        from_dt = datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        stream = rewrite_timestamps(SAMPLE_STREAM, mode="from", from_dt=from_dt)

        ts_values = sorted([int(v) for v in set(_extract_timestamps(stream))])
        # 적어도 2개의 다른 타임스탬프가 있어야 함
        assert len(ts_values) >= 2
        actual_interval = ts_values[1] - ts_values[0]
        assert actual_interval == original_interval

    def test_mode_from_requires_from_dt(self):
        """mode='from'에서 from_dt가 None이면 ValueError 발생."""
        from gitshuttle.rewrite import rewrite_timestamps

        import pytest
        with pytest.raises(ValueError, match="from_dt"):
            rewrite_timestamps(SAMPLE_STREAM, mode="from", from_dt=None)

    def test_invalid_mode_raises(self):
        """알 수 없는 mode는 ValueError를 발생시킨다."""
        from gitshuttle.rewrite import rewrite_timestamps

        import pytest
        with pytest.raises(ValueError, match="mode"):
            rewrite_timestamps(SAMPLE_STREAM, mode="invalid")


# ---------------------------------------------------------------------------
# apply_rewrites 테스트
# ---------------------------------------------------------------------------

class TestApplyRewrites:
    def test_apply_all_rewrites(self):
        """apply_rewrites는 author, branch, timestamp를 순서대로 적용한다."""
        from gitshuttle.rewrite import apply_rewrites

        author_map = {
            "alice@example.com": {"name": "Alice Corp", "email": "alice@corp.com"},
        }
        from_dt = datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc)

        stream, warnings = apply_rewrites(
            stream=SAMPLE_STREAM,
            author_map=author_map,
            target_branch="imported/main",
            timestamp_mode="from",
            from_dt=from_dt,
        )

        # author 치환 확인
        assert "Alice Corp <alice@corp.com>" in stream
        # branch 치환 확인
        assert "commit refs/heads/imported/main" in stream
        # timestamp 치환 확인 — 원본 타임스탬프가 없어야 함
        assert str(SAMPLE_TS_1) not in stream

    def test_apply_rewrites_returns_tuple(self):
        """반환값은 (str, list) 형태여야 한다."""
        from gitshuttle.rewrite import apply_rewrites

        result = apply_rewrites(
            stream=SAMPLE_STREAM,
            author_map={},
            target_branch="main",
            timestamp_mode="original",
        )
        assert isinstance(result, tuple)
        stream, warnings = result
        assert isinstance(stream, str)
        assert isinstance(warnings, list)

    def test_apply_rewrites_warnings_collected(self):
        """미매핑 작성자 경고가 warnings에 수집된다."""
        from gitshuttle.rewrite import apply_rewrites

        stream, warnings = apply_rewrites(
            stream=SAMPLE_STREAM,
            author_map={},  # 빈 매핑 → 모든 작성자 미매핑
            target_branch="main",
            timestamp_mode="original",
        )

        # Alice와 Bob 모두 경고에 포함되어야 함
        all_warnings = " ".join(warnings)
        assert "alice@example.com" in all_warnings or "Alice" in all_warnings


class TestRewritePreservesDataBlocks:
    """fast-export data payload는 파일 내용이므로 rewrite 대상에서 제외되어야 한다."""

    def test_apply_rewrites_does_not_modify_blob_payload(self):
        from gitshuttle.rewrite import apply_rewrites

        payload = (
            "commit refs/gitshuttle/tmp_abc1234\n"
            f"author Alice <alice@example.com> {SAMPLE_TS_1} +0900\n"
            "re.findall(pattern, stream, re.MULTILINE)\n"
        )
        payload_size = len(payload.encode("utf-8"))
        stream = (
            f"blob\n"
            f"mark :1\n"
            f"data {payload_size}\n"
            f"{payload}"
            f"reset refs/gitshuttle/tmp_abc1234\n"
            f"commit refs/gitshuttle/tmp_abc1234\n"
            f"mark :2\n"
            f"author Alice <alice@example.com> {SAMPLE_TS_1} +0900\n"
            f"committer Alice <alice@example.com> {SAMPLE_TS_1} +0900\n"
            f"data 14\n"
            f"Initial commit\n"
            f"\n"
            f"M 100644 :1 tricky.py\n"
            f"\n"
        )

        rewritten, warnings = apply_rewrites(
            stream=stream,
            author_map={
                "alice@example.com": {
                    "name": "Alice Corp",
                    "email": "alice@corp.com",
                }
            },
            target_branch="migration/gitshuttle-20260610",
            timestamp_mode="original",
        )

        assert warnings == []
        assert f"data {payload_size}\n{payload}" in rewritten
        assert "commit refs/heads/migration/gitshuttle-20260610" in rewritten
        assert "Alice Corp <alice@corp.com>" in rewritten
        # 원본 ref와 author 문자열은 blob payload 안에만 남아야 한다.
        assert rewritten.count("commit refs/gitshuttle/tmp_abc1234") == 1
        assert rewritten.count("Alice <alice@example.com>") == 1
        assert "re.findall(pattern, stream, re.MULTILINE)" in rewritten

    def test_rewrite_parent_refs_does_not_modify_blob_payload(self):
        from gitshuttle.rewrite import rewrite_parent_refs

        original_parent = "a" * 40
        target_parent = "b" * 40
        payload = f"from {original_parent}\n"
        payload_size = len(payload.encode("utf-8"))
        stream = (
            "blob\n"
            "mark :1\n"
            f"data {payload_size}\n"
            f"{payload}"
            "commit refs/heads/main\n"
            "mark :2\n"
            "author A <a@example.com> 1 +0000\n"
            "committer A <a@example.com> 1 +0000\n"
            "data 4\n"
            "msg\n"
            f"from {original_parent}\n"
            "M 100644 :1 note.txt\n"
            "\n"
        )

        rewritten = rewrite_parent_refs(stream, {original_parent: target_parent})

        assert f"data {payload_size}\n{payload}" in rewritten
        assert f"from {target_parent}\n" in rewritten
        assert rewritten.count(f"from {original_parent}") == 1


# ---------------------------------------------------------------------------
# CLI 옵션 존재 확인 (소스 코드 파싱 방식 — typer 미설치 환경 호환)
# ---------------------------------------------------------------------------

class TestImportCLIOptions:
    """cli.py 소스에 옵션 파라미터 선언이 존재하는지 확인한다.

    typer가 설치되어 있지 않은 환경에서도 동작하도록
    cli.py 소스 텍스트를 직접 파싱한다.
    """

    def _read_cli_source(self) -> str:
        from pathlib import Path
        cli_path = Path(__file__).parent.parent / "gitshuttle" / "cli.py"
        return cli_path.read_text(encoding='utf-8')

    def test_import_has_author_map_option(self):
        """import 커맨드에 --author-map 옵션 선언이 존재해야 한다."""
        source = self._read_cli_source()
        assert "author_map" in source
        assert "--author-map" in source

    def test_import_has_target_branch_option(self):
        """import 커맨드에 --target-branch 옵션 선언이 존재해야 한다."""
        source = self._read_cli_source()
        assert "target_branch" in source
        assert "--target-branch" in source

    def test_import_has_timestamp_option(self):
        """import 커맨드에 --timestamp 옵션 선언이 존재해야 한다."""
        source = self._read_cli_source()
        assert "timestamp" in source
        assert "--timestamp" in source


# ---------------------------------------------------------------------------
# config.py 읽기 확인
# ---------------------------------------------------------------------------

class TestConfigImportSection:
    def test_get_import_config_returns_defaults(self, tmp_path):
        """[import] 섹션 없으면 기본값을 반환한다."""
        from gitshuttle.config import get_import_config

        result = get_import_config(config_path=tmp_path / "nonexistent.toml")
        assert result["timestamp"] == "now"
        assert result["author_map"] is None

    def test_get_import_config_reads_timestamp(self, tmp_path):
        """[import] 섹션의 timestamp 값을 읽는다."""
        from gitshuttle.config import get_import_config

        toml_content = '[import]\ntimestamp = "original"\n'
        cfg_file = tmp_path / "gitshuttle.toml"
        cfg_file.write_text(toml_content, encoding='utf-8')

        result = get_import_config(config_path=cfg_file)
        assert result["timestamp"] == "original"

    def test_get_import_config_reads_author_map(self, tmp_path):
        """[import] 섹션의 author_map 경로를 읽는다."""
        from gitshuttle.config import get_import_config

        toml_content = '[import]\nauthor_map = "map.json"\n'
        cfg_file = tmp_path / "gitshuttle.toml"
        cfg_file.write_text(toml_content, encoding='utf-8')

        result = get_import_config(config_path=cfg_file)
        assert result["author_map"] == "map.json"


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _extract_timestamps(stream: str) -> list[str]:
    """fast-export 스트림에서 author/committer 타임스탬프(Unix 정수 문자열)를 추출한다.

    형식: "author Name <email> TIMESTAMP TIMEZONE"
    """
    import re
    pattern = r'^(?:author|committer)\s+.+?\s+(\d+)\s+[+-]\d{4}$'
    return re.findall(pattern, stream, re.MULTILINE)
