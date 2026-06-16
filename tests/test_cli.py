"""Tests for gitshuttle CLI scaffold (Sprint 0).

RED phase: these tests will fail until implementation is in place.
"""
import pytest
from typer.testing import CliRunner


def test_help_shows_commands():
    """--help 실행 시 export, import, config 커맨드가 표시되어야 한다."""
    from gitshuttle.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert "export" in result.output
    assert "import" in result.output
    assert "config" in result.output


def test_direct_command_removed():
    """직접 동기화 명령은 더 이상 제공하지 않는다."""
    from gitshuttle.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["sync"])

    assert result.exit_code != 0
    assert "No such command" in result.output


def test_version():
    """--version 실행 시 버전 문자열이 출력되어야 한다."""
    from gitshuttle.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert "0.1.0" in result.output


def test_default_config_tui():
    """gitshuttle.toml 없을 때 config 기본값이 'tui'여야 한다."""
    from gitshuttle.config import DEFAULT_UI

    assert DEFAULT_UI == "tui"


def test_export_stub(tmp_git_repo):
    """export 커맨드가 에러 없이 실행되어야 한다.

    GITSHUTTLE_HEADLESS=1 로 TUI 를 우회하고 tmp_git_repo 에서 실행한다.
    """
    import os
    from gitshuttle.cli import app

    runner = CliRunner()
    # Typer CliRunner 는 env 파라미터를 지원하지 않으므로 환경변수를 직접 패치한다.
    old_val = os.environ.get("GITSHUTTLE_HEADLESS")
    old_cwd = os.getcwd()
    try:
        os.environ["GITSHUTTLE_HEADLESS"] = "1"
        os.chdir(str(tmp_git_repo))
        result = runner.invoke(app, ["export", "--branch", "HEAD"])
    finally:
        if old_val is None:
            os.environ.pop("GITSHUTTLE_HEADLESS", None)
        else:
            os.environ["GITSHUTTLE_HEADLESS"] = old_val
        os.chdir(old_cwd)

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert "export 완료" in result.output


def test_export_accepts_repo_option(tmp_path, monkeypatch):
    """export --repo 는 현재 디렉터리 대신 지정한 repo 경로를 사용한다."""
    from gitshuttle.cli import app
    from gitshuttle.export_ import ExportResult
    from gitshuttle.git_ops import Commit
    import gitshuttle.export_ as export_module
    import gitshuttle.git_ops as git_ops_module
    import gitshuttle.ui.tui as tui_module

    repo_dir = tmp_path / "source_repo"
    repo_dir.mkdir()
    output_dir = tmp_path / "out"
    captured = {}

    fake_commit = Commit(
        hash="a" * 40,
        short_hash="aaaaaaa",
        date="2026-06-10 09:00:00 +0900",
        author="New Author",
        message="test commit",
        files_changed=1,
    )

    def fake_get_commits(repo_path, branch="HEAD", limit=None):
        captured["get_commits_repo"] = repo_path
        captured["branch"] = branch
        captured["limit"] = limit
        return [fake_commit]

    def fake_select_commits(commits):
        return commits

    def fake_run_export(
        repo_path,
        commits,
        output_dir,
        branch,
        bundle_scope="range",
        base_refs=None,
    ):
        captured["run_export_repo"] = repo_path
        captured["output_dir"] = output_dir
        captured["export_branch"] = branch
        captured["bundle_scope"] = bundle_scope
        return ExportResult(
            bundle=output_dir / "test.bundle",
            sha256=output_dir / "test.bundle.sha256",
            manifest=output_dir / "test_manifest.txt",
        )

    monkeypatch.setattr(git_ops_module, "get_commits", fake_get_commits)
    monkeypatch.setattr(tui_module, "select_commits_tui", fake_select_commits)
    monkeypatch.setattr(export_module, "run_export", fake_run_export)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "--repo",
            str(repo_dir),
            "--branch",
            "main",
            "--output",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert captured["get_commits_repo"] == repo_dir.resolve()
    assert captured["run_export_repo"] == repo_dir.resolve()
    assert captured["branch"] == "main"
    assert captured["limit"] is None
    assert captured["output_dir"] == output_dir
    assert captured["bundle_scope"] == "range"


def test_export_rejects_removed_format_option(tmp_path):
    """별도 재생 모드 제거 후 export --format 옵션은 제공하지 않는다."""
    from gitshuttle.cli import app

    repo_dir = tmp_path / "source_repo"
    repo_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "--repo",
            str(repo_dir),
            "--format",
            "bundle",
        ],
    )

    assert result.exit_code == 2
    assert "No such option: --format" in result.output


def test_export_recent_selects_latest_without_ui(tmp_path, monkeypatch):
    """export --recent N 은 UI 없이 최신 N개만 읽어 선택한다."""
    from gitshuttle.cli import app
    from gitshuttle.export_ import ExportResult
    from gitshuttle.git_ops import Commit
    import gitshuttle.export_ as export_module
    import gitshuttle.git_ops as git_ops_module
    import gitshuttle.ui.tui as tui_module

    repo_dir = tmp_path / "source_repo"
    repo_dir.mkdir()
    output_dir = tmp_path / "out"
    captured = {}
    commits = [
        Commit(
            hash=str(index) * 40,
            short_hash=str(index) * 7,
            date="2026-06-10 09:00:00 +0900",
            author="New Author",
            message=f"commit {index}",
            files_changed=1,
        )
        for index in (1, 2)
    ]

    def fake_get_commits(repo_path, branch="HEAD", limit=None):
        captured["limit"] = limit
        return commits

    def fail_select_commits(commits):
        raise AssertionError("recent mode should not open TUI")

    def fake_run_export(
        repo_path,
        commits,
        output_dir,
        branch,
        bundle_scope="range",
        base_refs=None,
    ):
        captured["selected"] = commits
        captured["bundle_scope"] = bundle_scope
        return ExportResult(
            bundle=output_dir / "test.bundle",
            sha256=output_dir / "test.bundle.sha256",
            manifest=output_dir / "test_manifest.txt",
        )

    monkeypatch.setattr(git_ops_module, "get_commits", fake_get_commits)
    monkeypatch.setattr(tui_module, "select_commits_tui", fail_select_commits)
    monkeypatch.setattr(export_module, "run_export", fake_run_export)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "--repo",
            str(repo_dir),
            "--output",
            str(output_dir),
            "--recent",
            "2",
        ],
    )

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert captured["limit"] == 2
    assert captured["selected"] == commits
    assert captured["bundle_scope"] == "range"
    assert "UI 없이 선택" in result.output


def test_export_accepts_bundle_scope_full(tmp_path, monkeypatch):
    """export --bundle-scope full 은 run_export에 self-contained bundle 범위를 전달한다."""
    from gitshuttle.cli import app
    from gitshuttle.export_ import ExportResult
    from gitshuttle.git_ops import Commit
    import gitshuttle.export_ as export_module
    import gitshuttle.git_ops as git_ops_module
    import gitshuttle.ui.tui as tui_module

    repo_dir = tmp_path / "source_repo"
    repo_dir.mkdir()
    output_dir = tmp_path / "out"
    captured = {}
    fake_commit = Commit(
        hash="a" * 40,
        short_hash="aaaaaaa",
        date="2026-06-10 09:00:00 +0900",
        author="New Author",
        message="test commit",
        files_changed=1,
    )

    monkeypatch.setattr(
        git_ops_module,
        "get_commits",
        lambda repo_path, branch="HEAD", limit=None: [fake_commit],
    )
    monkeypatch.setattr(tui_module, "select_commits_tui", lambda commits: commits)

    def fake_run_export(
        repo_path,
        commits,
        output_dir,
        branch,
        bundle_scope="range",
        base_refs=None,
    ):
        captured["bundle_scope"] = bundle_scope
        return ExportResult(
            bundle=output_dir / "test.bundle",
            sha256=output_dir / "test.bundle.sha256",
            manifest=output_dir / "test_manifest.txt",
        )

    monkeypatch.setattr(export_module, "run_export", fake_run_export)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "--repo",
            str(repo_dir),
            "--output",
            str(output_dir),
            "--bundle-scope",
            "full",
        ],
    )

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert captured["bundle_scope"] == "full"


def test_export_full_branch_selects_tip_as_full_bundle_without_ui(tmp_path, monkeypatch):
    """export --full-branch 는 브랜치 tip 기준 전체 이력을 bundle로 추출한다."""
    from gitshuttle.cli import app
    from gitshuttle.export_ import ExportResult
    from gitshuttle.git_ops import Commit
    import gitshuttle.export_ as export_module
    import gitshuttle.git_ops as git_ops_module
    import gitshuttle.ui.tui as tui_module

    repo_dir = tmp_path / "source_repo"
    repo_dir.mkdir()
    output_dir = tmp_path / "out"
    captured = {}
    tip_commit = Commit(
        hash="b" * 40,
        short_hash="bbbbbbb",
        date="2026-06-10 09:00:00 +0900",
        author="New Author",
        message="branch tip",
        files_changed=1,
    )

    def fake_get_commits(repo_path, branch="HEAD", limit=None):
        captured["branch"] = branch
        captured["limit"] = limit
        return [tip_commit]

    def fail_select_commits(commits):
        raise AssertionError("full-branch mode should not open TUI")

    def fake_run_export(
        repo_path,
        commits,
        output_dir,
        branch,
        bundle_scope="range",
        base_refs=None,
    ):
        captured["selected"] = commits
        captured["bundle_scope"] = bundle_scope
        return ExportResult(
            bundle=output_dir / "test.bundle",
            sha256=output_dir / "test.bundle.sha256",
            manifest=output_dir / "test_manifest.txt",
        )

    monkeypatch.setattr(git_ops_module, "get_commits", fake_get_commits)
    monkeypatch.setattr(tui_module, "select_commits_tui", fail_select_commits)
    monkeypatch.setattr(export_module, "run_export", fake_run_export)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "--repo",
            str(repo_dir),
            "--branch",
            "main",
            "--output",
            str(output_dir),
            "--full-branch",
        ],
    )

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert captured["branch"] == "main"
    assert captured["limit"] == 1
    assert captured["selected"] == [tip_commit]
    assert captured["bundle_scope"] == "full"
    assert "전체 이력" in result.output


def test_export_base_branch_full_branch_selects_branch_delta_without_ui(tmp_path, monkeypatch):
    """--base-branch 와 --full-branch 조합은 base..branch 전체를 UI 없이 선택한다."""
    from gitshuttle.cli import app
    from gitshuttle.export_ import ExportResult
    from gitshuttle.git_ops import Commit
    import gitshuttle.export_ as export_module
    import gitshuttle.git_ops as git_ops_module
    import gitshuttle.ui.tui as tui_module

    repo_dir = tmp_path / "source_repo"
    repo_dir.mkdir()
    output_dir = tmp_path / "out"
    captured = {}
    selected_commits = [
        Commit(
            hash="c" * 40,
            short_hash="ccccccc",
            date="2026-06-10 09:30:00 +0900",
            author="New Author",
            message="feature 2",
            files_changed=1,
        ),
        Commit(
            hash="b" * 40,
            short_hash="bbbbbbb",
            date="2026-06-10 09:00:00 +0900",
            author="New Author",
            message="feature 1",
            files_changed=1,
        ),
    ]

    def fake_get_commits(repo_path, branch="HEAD", limit=None):
        captured["branch"] = branch
        captured["limit"] = limit
        return selected_commits

    def fail_select_commits(commits):
        raise AssertionError("base branch full export should not open TUI")

    def fake_run_export(
        repo_path,
        commits,
        output_dir,
        branch,
        bundle_scope="range",
        base_refs=None,
    ):
        captured["selected"] = commits
        captured["export_branch"] = branch
        captured["bundle_scope"] = bundle_scope
        captured["base_refs"] = base_refs
        return ExportResult(
            bundle=output_dir / "test.bundle",
            sha256=output_dir / "test.bundle.sha256",
            manifest=output_dir / "test_manifest.txt",
        )

    monkeypatch.setattr(git_ops_module, "get_commits", fake_get_commits)
    monkeypatch.setattr(tui_module, "select_commits_tui", fail_select_commits)
    monkeypatch.setattr(export_module, "run_export", fake_run_export)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "--repo",
            str(repo_dir),
            "--branch",
            "feature/work",
            "--base-branch",
            "main",
            "--output",
            str(output_dir),
            "--full-branch",
        ],
    )

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert captured["branch"] == "main..feature/work"
    assert captured["limit"] is None
    assert captured["selected"] == selected_commits
    assert captured["export_branch"] == "main..feature/work"
    assert captured["bundle_scope"] == "range"
    assert captured["base_refs"] == ["main"]
    assert "기준 브랜치 이후" in result.output


def test_export_full_branch_rejects_recent(tmp_path):
    """export --full-branch 는 --recent 와 함께 사용할 수 없다."""
    from gitshuttle.cli import app

    repo_dir = tmp_path / "source_repo"
    repo_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "--repo",
            str(repo_dir),
            "--full-branch",
            "--recent",
            "2",
        ],
    )

    assert result.exit_code == 1
    assert "--full-branch" in result.output
    assert "--recent" in result.output


def test_import_stub():
    """import 커맨드는 --file 없이 실행하면 오류 안내 후 exit code 1."""
    from gitshuttle.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["import"])

    assert result.exit_code == 1
    assert "--file" in result.output or "--file" in (result.output + str(result.exception))


def test_import_accepts_repo_option(tmp_path, monkeypatch):
    """import --repo 는 현재 디렉터리 대신 지정한 target repo 경로를 사용한다."""
    from gitshuttle.cli import app
    import gitshuttle.import_ as import_module

    bundle_path = tmp_path / "test.bundle"
    bundle_path.write_bytes(b"fake bundle")
    repo_dir = tmp_path / "target_repo"
    repo_dir.mkdir()
    captured = {}

    def fake_run_import(
        bundle_path,
        repo_path,
        on_conflict="skip",
        sha256_path=None,
        author_map_path=None,
        target_branch=None,
        timestamp_mode="now",
    ):
        captured["bundle_path"] = bundle_path
        captured["repo_path"] = repo_path
        captured["on_conflict"] = on_conflict
        captured["timestamp_mode"] = timestamp_mode
        return import_module.ImportResult(imported=1, skipped=0, total=1)

    monkeypatch.setattr(import_module, "run_import", fake_run_import)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--file",
            str(bundle_path),
            "--repo",
            str(repo_dir),
            "--timestamp",
            "original",
        ],
    )

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert captured["bundle_path"] == bundle_path
    assert captured["repo_path"] == repo_dir.resolve()
    assert captured["timestamp_mode"] == "original"


def test_import_rejects_removed_mode_option(tmp_path):
    """별도 재생 모드 제거 후 import --mode 옵션은 제공하지 않는다."""
    from gitshuttle.cli import app

    bundle_path = tmp_path / "test.bundle"
    bundle_path.write_bytes(b"fake bundle")
    repo_dir = tmp_path / "target_repo"
    repo_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--file",
            str(bundle_path),
            "--repo",
            str(repo_dir),
            "--mode",
            "bundle",
        ],
    )

    assert result.exit_code == 2
    assert "No such option: --mode" in result.output


def test_config_stub():
    """config 커맨드가 에러 없이 실행되어야 한다 (1 입력 → tui 선택)."""
    from gitshuttle.cli import app

    runner = CliRunner()
    # "1\n" 을 stdin 으로 제공 → TUI 선택
    result = runner.invoke(app, ["config"], input="1\n")

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
